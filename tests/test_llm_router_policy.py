"""
Tests para LLM Router Policy

Cobertura:
- Detección de imports prohibidos (anthropic, openai, etc.)
- Detección de llamadas directas a APIs
- Escaneo de archivos y directorios
- Validación de codebase
- Reporte de violaciones

Autor: Bernard Uriza Orozco
Fecha: 2025-10-25
Task: FI-CORE-FIX-001
"""

import ast
import tempfile
import unittest
from pathlib import Path

from backend.llm_router_policy import (
    RouterViolation,
    extract_attribute_calls,
    extract_imports,
    has_forbidden_call,
    has_forbidden_import,
    scan_directory,
    scan_file_for_router_violations,
    validate_codebase,
)


class TestExtractImports(unittest.TestCase):
    """Tests para extracción de imports."""

    def test_extract_simple_import(self):
        """Debe extraer import simple."""
        code = "import anthropic"
        tree = ast.parse(code)
        imports = extract_imports(tree)
        self.assertIn("anthropic", imports)

    def test_extract_from_import(self):
        """Debe extraer from import."""
        code = "from anthropic import Anthropic"
        tree = ast.parse(code)
        imports = extract_imports(tree)
        self.assertIn("anthropic", imports)

    def test_extract_multiple_imports(self):
        """Debe extraer múltiples imports."""
        code = """
import anthropic
import openai
from cohere import Client
"""
        tree = ast.parse(code)
        imports = extract_imports(tree)
        self.assertIn("anthropic", imports)
        self.assertIn("openai", imports)
        self.assertIn("cohere", imports)

    def test_extract_nested_import(self):
        """Debe extraer import con dots."""
        code = "from google.generativeai import GenerativeModel"
        tree = ast.parse(code)
        imports = extract_imports(tree)
        self.assertIn("google.generativeai", imports)


class TestHasForbiddenImport(unittest.TestCase):
    """Tests para detección de imports prohibidos."""

    def test_detects_anthropic(self):
        """Debe detectar import de anthropic."""
        imports = {"anthropic", "os", "sys"}
        forbidden = has_forbidden_import(imports)
        self.assertIn("anthropic", forbidden)

    def test_detects_openai(self):
        """Debe detectar import de openai."""
        imports = {"openai", "pathlib"}
        forbidden = has_forbidden_import(imports)
        self.assertIn("openai", forbidden)

    def test_detects_nested_google(self):
        """Debe detectar import de google.generativeai."""
        imports = {"google.generativeai", "json"}
        forbidden = has_forbidden_import(imports)
        self.assertEqual(len(forbidden), 1)
        self.assertTrue(any("google.generativeai" in f for f in forbidden))

    def test_ignores_safe_imports(self):
        """No debe marcar imports seguros."""
        imports = {"os", "sys", "pathlib", "json"}
        forbidden = has_forbidden_import(imports)
        self.assertEqual(len(forbidden), 0)

    def test_detects_multiple_forbidden(self):
        """Debe detectar múltiples imports prohibidos."""
        imports = {"anthropic", "openai", "cohere", "os"}
        forbidden = has_forbidden_import(imports)
        self.assertGreaterEqual(len(forbidden), 3)


class TestExtractAttributeCalls(unittest.TestCase):
    """Tests para extracción de attribute calls."""

    def test_extract_simple_call(self):
        """Debe extraer llamada simple."""
        code = "client.messages.create()"
        tree = ast.parse(code)
        calls = extract_attribute_calls(tree)
        self.assertEqual(len(calls), 1)
        _, chain = calls[0]
        self.assertEqual(chain, "messages.create")

    def test_extract_nested_call(self):
        """Debe extraer llamada anidada."""
        code = "openai.chat.completions.create()"
        tree = ast.parse(code)
        calls = extract_attribute_calls(tree)
        self.assertEqual(len(calls), 1)
        _, chain = calls[0]
        self.assertEqual(chain, "chat.completions.create")

    def test_extract_multiple_calls(self):
        """Debe extraer múltiples llamadas."""
        code = """
client.messages.create()
api.generate()
"""
        tree = ast.parse(code)
        calls = extract_attribute_calls(tree)
        self.assertEqual(len(calls), 2)


class TestHasForbiddenCall(unittest.TestCase):
    """Tests para detección de llamadas prohibidas."""

    def test_detects_anthropic_messages_create(self):
        """Debe detectar messages.create."""
        calls = [(1, "messages.create"), (2, "other.method")]
        forbidden = has_forbidden_call(calls)
        self.assertEqual(len(forbidden), 1)
        self.assertEqual(forbidden[0][1], "messages.create")

    def test_detects_openai_completions_create(self):
        """Debe detectar chat.completions.create."""
        calls = [(1, "chat.completions.create")]
        forbidden = has_forbidden_call(calls)
        self.assertEqual(len(forbidden), 1)

    def test_detects_generate(self):
        """Debe detectar generate()."""
        calls = [(1, "model.generate")]
        forbidden = has_forbidden_call(calls)
        self.assertEqual(len(forbidden), 1)

    def test_ignores_safe_calls(self):
        """No debe marcar llamadas seguras."""
        calls = [(1, "logger.info"), (2, "data.append")]
        forbidden = has_forbidden_call(calls)
        self.assertEqual(len(forbidden), 0)


class TestScanFile(unittest.TestCase):
    """Tests para escaneo de archivos."""

    def test_scan_file_with_forbidden_import(self):
        """Debe detectar archivo con import prohibido."""
        code = """
import anthropic

def my_function():
    return "ok"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            filepath = Path(f.name)
            violations = scan_file_for_router_violations(filepath)

            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].violation_type, "import")
            self.assertIn("anthropic", violations[0].details)

            filepath.unlink()

    def test_scan_file_with_forbidden_call(self):
        """Debe detectar archivo con llamada prohibida."""
        code = """
def call_api():
    response = client.messages.create(model="claude")
    return response
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            filepath = Path(f.name)
            violations = scan_file_for_router_violations(filepath)

            self.assertEqual(len(violations), 1)
            self.assertEqual(violations[0].violation_type, "call")
            self.assertIn("messages.create", violations[0].details)

            filepath.unlink()

    def test_scan_file_with_both_violations(self):
        """Debe detectar import y call prohibidos."""
        code = """
import anthropic

def call_api():
    client = anthropic.Anthropic()
    response = client.messages.create()
    return response
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            filepath = Path(f.name)
            violations = scan_file_for_router_violations(filepath)

            # Debe tener import violation + call violation
            self.assertGreaterEqual(len(violations), 2)

            violation_types = [v.violation_type for v in violations]
            self.assertIn("import", violation_types)
            self.assertIn("call", violation_types)

            filepath.unlink()

    def test_scan_clean_file(self):
        """Debe pasar archivo limpio (usando router)."""
        code = """
from llm_router import route_llm_call

def call_api(prompt):
    response = route_llm_call(prompt=prompt, model="claude")
    return response
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            filepath = Path(f.name)
            violations = scan_file_for_router_violations(filepath)

            # No debe tener violaciones
            self.assertEqual(len(violations), 0)

            filepath.unlink()

    def test_scan_file_with_syntax_error(self):
        """Debe manejar archivos con syntax errors."""
        code = """
def invalid_syntax(
    # Missing closing parenthesis
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            filepath = Path(f.name)
            violations = scan_file_for_router_violations(filepath)

            # No debe crashear, debe retornar lista vacía
            self.assertEqual(len(violations), 0)

            filepath.unlink()


class TestDirectoryScan(unittest.TestCase):
    """Tests para escaneo de directorios."""

    def test_scan_directory_with_violations(self):
        """Debe escanear directorio y detectar violaciones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Archivo 1: Con violación
            file1 = tmppath / "module1.py"
            file1.write_text(
                """
import anthropic
"""
            )

            # Archivo 2: Sin violación
            file2 = tmppath / "module2.py"
            file2.write_text(
                """
from llm_router import route_llm_call
"""
            )

            results = scan_directory(tmppath)

            # Debe encontrar 1 archivo con violaciones
            self.assertEqual(len(results), 1)
            self.assertIn("module1.py", str(list(results.keys())[0]))

    def test_scan_directory_skips_tests(self):
        """Debe ignorar archivos test_*.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Test file (debe ser ignorado)
            test_file = tmppath / "test_something.py"
            test_file.write_text(
                """
import anthropic
"""
            )

            results = scan_directory(tmppath)

            # No debe encontrar nada
            self.assertEqual(len(results), 0)


class TestValidateCodebase(unittest.TestCase):
    """Tests para validación de codebase."""

    def test_validate_clean_codebase(self):
        """Debe pasar validación si no hay violaciones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            file1 = tmppath / "clean.py"
            file1.write_text(
                """
from llm_router import route_llm_call

def call_llm(prompt):
    return route_llm_call(prompt=prompt)
"""
            )

            is_valid = validate_codebase(tmppath)
            self.assertTrue(is_valid)

    def test_validate_codebase_with_violations(self):
        """Debe fallar validación si hay violaciones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            file1 = tmppath / "violation.py"
            file1.write_text(
                """
import anthropic

def call_api():
    client = anthropic.Anthropic()
    return client.messages.create()
"""
            )

            is_valid = validate_codebase(tmppath)
            self.assertFalse(is_valid)

    def test_validate_empty_directory(self):
        """Debe pasar validación si no hay archivos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            is_valid = validate_codebase(tmppath)
            self.assertTrue(is_valid)


class TestRouterViolation(unittest.TestCase):
    """Tests para dataclass RouterViolation."""

    def test_router_violation_str(self):
        """Debe formatear correctamente __str__."""
        violation = RouterViolation(
            filepath="test.py",
            lineno=10,
            violation_type="import",
            details="Direct import of 'anthropic'",
        )

        result = str(violation)
        self.assertIn("test.py:10", result)
        self.assertIn("import", result)
        self.assertIn("anthropic", result)


if __name__ == "__main__":
    unittest.main()
