"""
LLM Router Policy - Free Intelligence

Enforcement de política: TODA llamada a LLM debe usar router centralizado.

Propósito:
- Prohibir llamadas directas a APIs de LLM (anthropic, openai, etc.)
- Forzar uso de router centralizado para control y audit
- Detección estática de imports y calls directos

Uso:
    # ❌ PROHIBIDO: Llamada directa
    from anthropic import Anthropic
    client = Anthropic()
    response = client.messages.create(...)

    # ✅ PERMITIDO: Via router
    from llm_router import route_llm_call
    response = route_llm_call(prompt=..., model=...)

Validación estática:
    python3 backend/llm_router_policy.py scan backend/

Policy:
- ❌ Imports directos: anthropic, openai, cohere, etc.
- ❌ Llamadas directas: client.messages.create(), openai.ChatCompletion.create()
- ✅ Uso de router: route_llm_call(), LLMRouter.query()

Autor: Bernard Uriza Orozco
Fecha: 2025-10-25
Sprint: SPR-2025W44 (Sprint 2)
Task: FI-CORE-FIX-001
"""

import ast
from dataclasses import dataclass
from pathlib import Path

# Optional logger import (for runtime logging)
try:
    from logger import get_logger

    logger = get_logger(__name__)
except ImportError:
    # Fallback to print for CLI usage
    class SimpleLogger:
        def info(self, event, **kwargs):
            print(f"INFO: {event} - {kwargs}")

        def warning(self, event, **kwargs):
            print(f"WARNING: {event} - {kwargs}")

        def error(self, event, **kwargs):
            print(f"ERROR: {event} - {kwargs}")

    logger = SimpleLogger()


# ============================================================================
# EXCEPTIONS
# ============================================================================


class LLMRouterViolation(Exception):
    """Raised when direct LLM API call is detected."""

    pass


# ============================================================================
# CONFIGURATION
# ============================================================================

# Forbidden direct imports (LLM provider libraries)
FORBIDDEN_IMPORTS = {
    "anthropic",
    "openai",
    "cohere",
    "google.generativeai",
    "huggingface_hub",
    "transformers",
}

# Allowed router modules (whitelist)
ALLOWED_ROUTER_MODULES = {
    "llm_router",
    "backend.llm_router",
}

# Forbidden call patterns (API methods)
FORBIDDEN_CALL_PATTERNS = {
    "messages.create",  # anthropic
    "chat.completions.create",  # openai
    "ChatCompletion.create",  # openai legacy
    "Completion.create",  # openai legacy
    "generate",  # cohere, huggingface
    "generate_content",  # google
}


# ============================================================================
# DATACLASSES
# ============================================================================


@dataclass
class RouterViolation:
    """Información de violación de router policy."""

    filepath: str
    lineno: int
    violation_type: str  # 'import' | 'call'
    details: str

    def __str__(self) -> str:
        return f"{self.filepath}:{self.lineno} - {self.violation_type}: {self.details}"


# ============================================================================
# VALIDATORS
# ============================================================================


def extract_imports(tree: ast.AST) -> set[str]:
    """
    Extrae todos los imports de un AST.

    Returns:
        Set de módulos importados (e.g., {'anthropic', 'openai'})
    """
    imports = set()

    for node in ast.walk(tree):
        # import anthropic
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)

        # from anthropic import Anthropic
        if isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports


def has_forbidden_import(imports: set[str]) -> list[str]:
    """
    Verifica si hay imports prohibidos.

    Returns:
        Lista de imports prohibidos encontrados
    """
    forbidden = []

    for imp in imports:
        # Check exact match
        if imp in FORBIDDEN_IMPORTS:
            forbidden.append(imp)
            continue

        # Check prefix match (e.g., google.generativeai)
        for forbidden_imp in FORBIDDEN_IMPORTS:
            if imp.startswith(forbidden_imp + "."):
                forbidden.append(imp)
                break

    return forbidden


def extract_attribute_calls(tree: ast.AST) -> list[tuple]:
    """
    Extrae llamadas a métodos con atributos (e.g., client.messages.create()).

    Returns:
        Lista de (lineno, call_chain) donde call_chain es "messages.create"
    """
    calls = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Reconstruir call chain
            call_chain = []
            current = node.func

            while isinstance(current, ast.Attribute):
                call_chain.insert(0, current.attr)
                current = current.value

            if call_chain:
                chain_str = ".".join(call_chain)
                calls.append((node.lineno, chain_str))

    return calls


def has_forbidden_call(calls: list[tuple]) -> list[tuple]:
    """
    Verifica si hay llamadas prohibidas a APIs de LLM.

    Returns:
        Lista de (lineno, call_pattern) con llamadas prohibidas
    """
    forbidden = []

    for lineno, call_chain in calls:
        for pattern in FORBIDDEN_CALL_PATTERNS:
            if pattern in call_chain:
                forbidden.append((lineno, call_chain))
                break

    return forbidden


def scan_file_for_router_violations(filepath: Path) -> list[RouterViolation]:
    """
    Escanea un archivo Python en busca de violaciones de router policy.

    Returns:
        Lista de RouterViolation con información de violaciones
    """
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError as e:
        logger.warning("FILE_PARSE_FAILED", filepath=str(filepath), error=str(e))
        return []

    violations = []

    # Check imports
    imports = extract_imports(tree)
    forbidden_imports = has_forbidden_import(imports)

    for imp in forbidden_imports:
        violations.append(
            RouterViolation(
                filepath=str(filepath),
                lineno=1,  # Import line not tracked in this simple version
                violation_type="import",
                details=f"Direct import of LLM library: '{imp}'",
            )
        )

    # Check calls
    calls = extract_attribute_calls(tree)
    forbidden_calls = has_forbidden_call(calls)

    for lineno, call_pattern in forbidden_calls:
        violations.append(
            RouterViolation(
                filepath=str(filepath),
                lineno=lineno,
                violation_type="call",
                details=f"Direct LLM API call: '{call_pattern}'",
            )
        )

    return violations


def scan_directory(directory: Path) -> dict[str, list[RouterViolation]]:
    """
    Escanea un directorio recursivamente en busca de violaciones.

    Returns:
        Dict[filepath: str, violations: List[RouterViolation]]
    """
    results = {}

    for pyfile in directory.rglob("*.py"):
        # Skip test files y __pycache__
        if "test_" in pyfile.name or "__pycache__" in str(pyfile):
            continue

        violations = scan_file_for_router_violations(pyfile)

        if violations:
            results[str(pyfile)] = violations

    return results


def validate_codebase(root_dir: Path) -> bool:
    """
    Valida todo el codebase contra la política de router.

    Returns:
        True si NO hay violaciones, False si hay violaciones
    """
    results = scan_directory(root_dir)

    if not results:
        logger.info(
            "ROUTER_POLICY_SCAN_COMPLETED",
            directory=str(root_dir),
            message="No direct LLM API calls detected",
        )
        return True

    # Log violations
    total_violations = sum(len(v) for v in results.values())
    logger.error(
        "ROUTER_POLICY_VIOLATIONS_DETECTED",
        directory=str(root_dir),
        total_violations=total_violations,
        files_with_violations=len(results),
    )

    return False


def print_violations_report(results: dict[str, list[RouterViolation]]):
    """
    Imprime reporte formateado de violaciones.
    """
    if not results:
        print("\n✅ ROUTER POLICY VALIDATION PASSED")
        print("   No direct LLM API calls detected")
        print("   All LLM interactions must use centralized router")
        return

    print("\n❌ ROUTER POLICY VIOLATIONS DETECTED\n")

    total_violations = 0
    for filepath, violations in results.items():
        print(f"📁 {filepath}")

        # Group by type
        import_violations = [v for v in violations if v.violation_type == "import"]
        call_violations = [v for v in violations if v.violation_type == "call"]

        if import_violations:
            print("   🚫 Forbidden Imports:")
            for v in import_violations:
                total_violations += 1
                print(f"      • {v.details}")

        if call_violations:
            print("   🚫 Direct API Calls:")
            for v in call_violations:
                total_violations += 1
                print(f"      • Line {v.lineno}: {v.details}")

        print()

    print(f"Total violations: {total_violations}")
    print("\nPolicy: ALL LLM calls must:")
    print("  1. Use centralized router (llm_router module)")
    print("  2. NO direct imports of anthropic, openai, etc.")
    print("  3. NO direct API calls (messages.create, etc.)")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 backend/llm_router_policy.py scan <directory>")
        print("  python3 backend/llm_router_policy.py validate <directory>")
        print("\nExamples:")
        print("  python3 backend/llm_router_policy.py scan backend/")
        print("  python3 backend/llm_router_policy.py validate backend/")
        sys.exit(1)

    command = sys.argv[1]

    if command == "scan":
        if len(sys.argv) < 3:
            print("Error: Missing directory argument")
            sys.exit(1)

        directory = Path(sys.argv[2])

        if not directory.exists():
            print(f"Error: Directory not found: {directory}")
            sys.exit(1)

        print(f"🔍 Scanning {directory} for router policy violations...\n")

        results = scan_directory(directory)
        print_violations_report(results)

    elif command == "validate":
        if len(sys.argv) < 3:
            print("Error: Missing directory argument")
            sys.exit(1)

        directory = Path(sys.argv[2])

        if not directory.exists():
            print(f"Error: Directory not found: {directory}")
            sys.exit(1)

        print(f"🔍 Validating {directory} against router policy...\n")

        is_valid = validate_codebase(directory)

        # Print report
        results = scan_directory(directory)
        print_violations_report(results)

        sys.exit(0 if is_valid else 1)

    else:
        print(f"Error: Unknown command '{command}'")
        print("Available commands: scan, validate")
        sys.exit(1)
