"""
Tests para LLM Audit Policy

Cobertura:
- Decorator @require_audit_log
- AST detection de funciones LLM
- Validación de compliance (decorator + audit call)
- Escaneo de archivos y directorios
- Reporte de violaciones

Autor: Bernard Uriza Orozco
Fecha: 2025-10-25
Task: FI-CORE-FEAT-004
"""

import ast
import tempfile
import unittest
from pathlib import Path

from backend.llm_audit_policy import (
    LLMFunctionInfo,
    calls_append_audit_log,
    has_require_audit_decorator,
    is_llm_function_name,
    require_audit_log,
    scan_directory,
    scan_file_for_llm_functions,
    validate_codebase,
)


class TestRequireAuditLogDecorator(unittest.TestCase):
    """Tests para decorator @require_audit_log."""

    def test_decorator_marks_function(self):
        """Decorator debe marcar función con __llm_audit_required__."""

        @require_audit_log
        def test_function():
            return "result"

        self.assertTrue(hasattr(test_function, "__llm_audit_required__"))
        self.assertTrue(test_function.__llm_audit_required__)

    def test_decorator_preserves_function_name(self):
        """Decorator debe preservar nombre de función."""

        @require_audit_log
        def call_claude_api():
            return "response"

        self.assertEqual(call_claude_api.__name__, "call_claude_api")

    def test_decorator_preserves_wrapped_function(self):
        """Decorator debe guardar referencia a función original."""

        @require_audit_log
        def invoke_llm():
            return "result"

        self.assertTrue(hasattr(invoke_llm, "__wrapped_function__"))
        self.assertEqual(invoke_llm.__wrapped_function__, "invoke_llm")

    def test_decorated_function_executes(self):
        """Función decorada debe ejecutarse normalmente."""

        @require_audit_log
        def get_response():
            return "test_response"

        result = get_response()
        self.assertEqual(result, "test_response")


class TestLLMFunctionNameDetection(unittest.TestCase):
    """Tests para detección de nombres de función LLM."""

    def test_detects_high_confidence_patterns(self):
        """Debe detectar patrones de alta confianza."""
        self.assertTrue(is_llm_function_name("call_claude_api"))
        self.assertTrue(is_llm_function_name("call_openai"))
        self.assertTrue(is_llm_function_name("invoke_llm"))
        self.assertTrue(is_llm_function_name("invoke_model"))
        self.assertTrue(is_llm_function_name("query_llm"))

    def test_detects_llm_keywords(self):
        """Debe detectar keywords de LLM."""
        self.assertTrue(is_llm_function_name("process_claude_response"))
        self.assertTrue(is_llm_function_name("anthropic_handler"))
        self.assertTrue(is_llm_function_name("openai_completion"))

    def test_excludes_validator_functions(self):
        """Debe excluir funciones del validador."""
        self.assertFalse(is_llm_function_name("scan_file_for_llm_functions"))
        self.assertFalse(is_llm_function_name("is_llm_function_name"))
        self.assertFalse(is_llm_function_name("validate_codebase"))

    def test_excludes_internal_generators(self):
        """Debe excluir funciones generate_* internas."""
        self.assertFalse(is_llm_function_name("generate_corpus_id"))
        self.assertFalse(is_llm_function_name("generate_owner_hash"))
        self.assertFalse(is_llm_function_name("generate_test_data"))

    def test_ignores_normal_functions(self):
        """No debe marcar funciones normales."""
        self.assertFalse(is_llm_function_name("get_data"))
        self.assertFalse(is_llm_function_name("append_interaction"))
        self.assertFalse(is_llm_function_name("validate_corpus"))


class TestDecoratorDetection(unittest.TestCase):
    """Tests para detección de decorator en AST."""

    def test_detects_simple_decorator(self):
        """Debe detectar @require_audit_log simple."""
        code = """
@require_audit_log
def call_llm():
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        self.assertTrue(has_require_audit_decorator(func_node))

    def test_detects_module_decorator(self):
        """Debe detectar @module.require_audit_log."""
        code = """
@llm_audit_policy.require_audit_log
def invoke_model():
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        self.assertTrue(has_require_audit_decorator(func_node))

    def test_ignores_other_decorators(self):
        """No debe detectar otros decorators."""
        code = """
@some_other_decorator
def my_function():
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        self.assertFalse(has_require_audit_decorator(func_node))

    def test_no_decorator(self):
        """Debe retornar False si no hay decorators."""
        code = """
def plain_function():
    pass
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        self.assertFalse(has_require_audit_decorator(func_node))


class TestAuditLogCallDetection(unittest.TestCase):
    """Tests para detección de append_audit_log() call."""

    def test_detects_direct_call(self):
        """Debe detectar append_audit_log() directo."""
        code = """
def call_llm():
    result = llm.query()
    append_audit_log(...)
    return result
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        self.assertTrue(calls_append_audit_log(func_node))

    def test_detects_module_call(self):
        """Debe detectar audit_logs.append_audit_log()."""
        code = """
def invoke_model():
    response = model.generate()
    audit_logs.append_audit_log(...)
    return response
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        self.assertTrue(calls_append_audit_log(func_node))

    def test_no_audit_call(self):
        """Debe retornar False si no hay llamada a audit."""
        code = """
def query_llm():
    return llm.complete()
"""
        tree = ast.parse(code)
        func_node = tree.body[0]
        self.assertFalse(calls_append_audit_log(func_node))


class TestFileScan(unittest.TestCase):
    """Tests para escaneo de archivos."""

    def test_scan_compliant_file(self):
        """Debe detectar función LLM compliant."""
        code = """
from llm_audit_policy import require_audit_log
from audit_logs import append_audit_log

@require_audit_log
def call_claude_api(prompt):
    response = "test"
    append_audit_log(operation="CLAUDE_API_CALLED", user_id="test")
    return response
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            filepath = Path(f.name)
            functions = scan_file_for_llm_functions(filepath)

            self.assertEqual(len(functions), 1)
            self.assertEqual(functions[0].name, "call_claude_api")
            self.assertTrue(functions[0].has_decorator)
            self.assertTrue(functions[0].calls_audit_log)
            self.assertTrue(functions[0].is_compliant())

            filepath.unlink()

    def test_scan_non_compliant_file(self):
        """Debe detectar función LLM non-compliant."""
        code = """
def call_openai_api(prompt):
    # Sin decorator, sin audit log
    return "response"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()

            filepath = Path(f.name)
            functions = scan_file_for_llm_functions(filepath)

            self.assertEqual(len(functions), 1)
            self.assertEqual(functions[0].name, "call_openai_api")
            self.assertFalse(functions[0].has_decorator)
            self.assertFalse(functions[0].calls_audit_log)
            self.assertFalse(functions[0].is_compliant())

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
            functions = scan_file_for_llm_functions(filepath)

            # No debe crashear, debe retornar lista vacía
            self.assertEqual(len(functions), 0)

            filepath.unlink()


class TestDirectoryScan(unittest.TestCase):
    """Tests para escaneo de directorios."""

    def test_scan_directory_with_violations(self):
        """Debe escanear directorio y detectar violaciones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Archivo 1: Non-compliant
            file1 = tmppath / "module1.py"
            file1.write_text(
                """
def call_llm():
    return "response"
"""
            )

            # Archivo 2: Compliant
            file2 = tmppath / "module2.py"
            file2.write_text(
                """
@require_audit_log
def invoke_model():
    append_audit_log(...)
    return "response"
"""
            )

            results = scan_directory(tmppath)

            # Debe encontrar 2 archivos con funciones LLM
            self.assertEqual(len(results), 2)

            # Verificar que detectó funciones
            all_functions = []
            for funcs in results.values():
                all_functions.extend(funcs)

            self.assertEqual(len(all_functions), 2)

    def test_scan_directory_skips_tests(self):
        """Debe ignorar archivos test_*.py."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Test file (debe ser ignorado)
            test_file = tmppath / "test_something.py"
            test_file.write_text(
                """
def call_llm():
    return "test"
"""
            )

            results = scan_directory(tmppath)

            # No debe encontrar nada
            self.assertEqual(len(results), 0)


class TestValidateCodebase(unittest.TestCase):
    """Tests para validación de codebase."""

    def test_validate_compliant_codebase(self):
        """Debe pasar validación si todo es compliant."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            file1 = tmppath / "compliant.py"
            file1.write_text(
                """
@require_audit_log
def call_claude():
    append_audit_log(...)
    return "ok"
"""
            )

            is_valid = validate_codebase(tmppath)
            self.assertTrue(is_valid)

    def test_validate_non_compliant_codebase(self):
        """Debe fallar validación si hay violaciones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            file1 = tmppath / "violation.py"
            file1.write_text(
                """
def invoke_llm():
    return "no audit"
"""
            )

            is_valid = validate_codebase(tmppath)
            self.assertFalse(is_valid)

    def test_validate_empty_directory(self):
        """Debe pasar validación si no hay funciones LLM."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            file1 = tmppath / "normal.py"
            file1.write_text(
                """
def get_data():
    return []
"""
            )

            is_valid = validate_codebase(tmppath)
            self.assertTrue(is_valid)


class TestLLMFunctionInfo(unittest.TestCase):
    """Tests para dataclass LLMFunctionInfo."""

    def test_is_compliant_when_both_true(self):
        """Debe ser compliant si tiene decorator y audit call."""
        info = LLMFunctionInfo(
            name="call_llm", lineno=10, has_decorator=True, calls_audit_log=True, filepath="test.py"
        )
        self.assertTrue(info.is_compliant())

    def test_not_compliant_without_decorator(self):
        """No debe ser compliant sin decorator."""
        info = LLMFunctionInfo(
            name="call_llm",
            lineno=10,
            has_decorator=False,
            calls_audit_log=True,
            filepath="test.py",
        )
        self.assertFalse(info.is_compliant())

    def test_not_compliant_without_audit_call(self):
        """No debe ser compliant sin audit call."""
        info = LLMFunctionInfo(
            name="call_llm",
            lineno=10,
            has_decorator=True,
            calls_audit_log=False,
            filepath="test.py",
        )
        self.assertFalse(info.is_compliant())


if __name__ == "__main__":
    unittest.main()
