"""
LLM Audit Policy - Free Intelligence

Enforcement de política: TODA llamada a LLM debe estar auditada.

Propósito:
- Prevenir llamadas a LLM sin trazabilidad
- Garantizar que cada inferencia quede registrada
- Enforcement en runtime + validación estática

Uso:
    from llm_audit_policy import require_audit_log

    @require_audit_log
    def call_claude_api(prompt: str) -> str:
        # Esta función DEBE loggear a audit_logs antes de retornar
        ...

Validación estática:
    python3 backend/llm_audit_policy.py scan backend/

Policy:
- ❌ LLM calls sin decorator @require_audit_log
- ❌ Funciones con "llm", "claude", "anthropic", "openai" en nombre sin audit
- ✅ Toda función decorada debe llamar append_audit_log() internamente

Autor: Bernard Uriza Orozco
Fecha: 2025-10-25
Sprint: SPR-2025W44 (Sprint 2)
Task: FI-CORE-FEAT-004
"""

import ast
import functools
from pathlib import Path
from typing import Callable, List, Dict
from dataclasses import dataclass

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

class LLMAuditViolation(Exception):
    """Raised when LLM function is called without audit logging."""
    pass


# ============================================================================
# DECORATOR: @require_audit_log
# ============================================================================

def require_audit_log(func: Callable) -> Callable:
    """
    Decorator que marca una función como requiriendo audit logging.

    Usage:
        @require_audit_log
        def call_claude_api(prompt: str) -> str:
            # DEBE llamar append_audit_log() antes de retornar
            ...

    Raises:
        LLMAuditViolation: Si la función no tiene audit logging

    Note:
        - Esta versión es un marker decorator (fase 1)
        - Fase 2: Runtime validation (verificar que se llamó append_audit_log)
        - Por ahora solo sirve para detección estática
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Marker para detección estática
        # TODO(FI-CORE-FEAT-004-P2): Runtime validation de append_audit_log
        logger.info(
            "LLM_FUNCTION_CALLED",
            function=func.__name__,
            module=func.__module__
        )
        return func(*args, **kwargs)

    # Marcar wrapper para detección
    wrapper.__llm_audit_required__ = True
    wrapper.__wrapped_function__ = func.__name__

    return wrapper


# ============================================================================
# STATIC VALIDATOR (AST-based)
# ============================================================================

@dataclass
class LLMFunctionInfo:
    """Información de función LLM detectada."""
    name: str
    lineno: int
    has_decorator: bool
    calls_audit_log: bool
    filepath: str

    def is_compliant(self) -> bool:
        """Retorna True si cumple con la política."""
        return self.has_decorator and self.calls_audit_log


def is_llm_function_name(name: str) -> bool:
    """
    Detecta si un nombre de función sugiere llamada a LLM.

    Patterns detectados:
    - call_*_api, invoke_*, query_* (con keywords LLM)
    - *_claude*, *_anthropic*, *_openai*, *_llm*

    Excludes:
    - Funciones del propio validador (scan_*, is_llm_*, validate_*)
    - generate_* solo si tiene keyword LLM (evita falsos positivos)
    """
    name_lower = name.lower()

    # Excluir funciones del validador mismo
    validator_prefixes = [
        'scan_', 'is_llm_', 'validate_', 'has_',
        'calls_', 'print_', 'get_canonical'
    ]
    for prefix in validator_prefixes:
        if name_lower.startswith(prefix):
            return False

    # Excluir funciones internas comunes (no-LLM)
    internal_patterns = [
        'generate_corpus_id', 'generate_owner_hash',
        'generate_event_name', 'generate_test_'
    ]
    for pattern in internal_patterns:
        if pattern in name_lower:
            return False

    # Substrings que DEFINITIVAMENTE indican LLM provider/type
    llm_keywords = [
        'claude', 'anthropic', 'openai', 'gpt',
        'llm', '_ai_', '_ml_'
    ]

    # Check keywords primero (alta confianza)
    for keyword in llm_keywords:
        if keyword in name_lower:
            return True

    # Prefixes de alta confianza (solo si NO tienen exclusiones)
    high_confidence_prefixes = [
        'call_claude', 'call_openai', 'call_anthropic',
        'invoke_llm', 'invoke_model', 'invoke_ai',
        'query_llm', 'query_model', 'query_ai',
        'request_llm', 'request_model', 'request_ai'
    ]

    for prefix in high_confidence_prefixes:
        if name_lower.startswith(prefix):
            return True

    # Prefixes de mediana confianza (solo con keywords)
    medium_confidence_prefixes = [
        'call_', 'invoke_', 'query_', 'request_',
        'infer_', 'predict_', 'complete_', 'generate_'
    ]

    for prefix in medium_confidence_prefixes:
        if name_lower.startswith(prefix):
            # Solo marcar si también tiene keyword LLM
            for keyword in llm_keywords:
                if keyword in name_lower:
                    return True

    return False


def has_require_audit_decorator(node: ast.FunctionDef) -> bool:
    """
    Verifica si la función tiene decorator @require_audit_log.
    """
    if not node.decorator_list:
        return False

    for decorator in node.decorator_list:
        # Decorator simple: @require_audit_log
        if isinstance(decorator, ast.Name):
            if decorator.id == 'require_audit_log':
                return True

        # Decorator con módulo: @llm_audit_policy.require_audit_log
        if isinstance(decorator, ast.Attribute):
            if decorator.attr == 'require_audit_log':
                return True

    return False


def calls_append_audit_log(node: ast.FunctionDef) -> bool:
    """
    Verifica si la función llama a append_audit_log().
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            # append_audit_log(...)
            if isinstance(child.func, ast.Name):
                if child.func.id == 'append_audit_log':
                    return True

            # audit_logs.append_audit_log(...)
            if isinstance(child.func, ast.Attribute):
                if child.func.attr == 'append_audit_log':
                    return True

    return False


def scan_file_for_llm_functions(filepath: Path) -> List[LLMFunctionInfo]:
    """
    Escanea un archivo Python en busca de funciones LLM sin audit.

    Returns:
        Lista de LLMFunctionInfo con información de compliance
    """
    try:
        content = filepath.read_text(encoding='utf-8')
        tree = ast.parse(content, filename=str(filepath))
    except SyntaxError as e:
        logger.warning(
            "FILE_PARSE_FAILED",
            filepath=str(filepath),
            error=str(e)
        )
        return []

    llm_functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            # Detectar si es función LLM
            if is_llm_function_name(node.name):
                has_decorator = has_require_audit_decorator(node)
                calls_audit = calls_append_audit_log(node)

                llm_functions.append(LLMFunctionInfo(
                    name=node.name,
                    lineno=node.lineno,
                    has_decorator=has_decorator,
                    calls_audit_log=calls_audit,
                    filepath=str(filepath)
                ))

    return llm_functions


def scan_directory(directory: Path) -> Dict[str, List[LLMFunctionInfo]]:
    """
    Escanea un directorio recursivamente en busca de LLM functions.

    Returns:
        Dict[filepath: str, violations: List[LLMFunctionInfo]]
    """
    results = {}

    for pyfile in directory.rglob('*.py'):
        # Skip test files y __pycache__
        if 'test_' in pyfile.name or '__pycache__' in str(pyfile):
            continue

        llm_functions = scan_file_for_llm_functions(pyfile)

        if llm_functions:
            results[str(pyfile)] = llm_functions

    return results


def validate_codebase(root_dir: Path) -> bool:
    """
    Valida todo el codebase contra la política LLM audit.

    Returns:
        True si NO hay violaciones, False si hay violaciones
    """
    results = scan_directory(root_dir)

    if not results:
        logger.info(
            "LLM_AUDIT_VALIDATION_PASSED",
            directory=str(root_dir),
            message="No LLM functions detected"
        )
        return True

    # Filtrar solo violaciones (non-compliant)
    violations = {}
    for filepath, functions in results.items():
        non_compliant = [f for f in functions if not f.is_compliant()]
        if non_compliant:
            violations[filepath] = non_compliant

    if not violations:
        logger.info(
            "LLM_AUDIT_VALIDATION_PASSED",
            directory=str(root_dir),
            total_llm_functions=sum(len(funcs) for funcs in results.values()),
            message="All LLM functions are compliant"
        )
        return True

    # Log violations
    logger.error(
        "LLM_AUDIT_VIOLATIONS_DETECTED",
        directory=str(root_dir),
        total_violations=sum(len(funcs) for funcs in violations.values()),
        files_with_violations=len(violations)
    )

    return False


def print_violations_report(results: Dict[str, List[LLMFunctionInfo]]):
    """
    Imprime reporte formateado de violaciones.
    """
    # Filtrar violaciones
    violations = {}
    for filepath, functions in results.items():
        non_compliant = [f for f in functions if not f.is_compliant()]
        if non_compliant:
            violations[filepath] = non_compliant

    if not violations:
        print("\n✅ LLM AUDIT VALIDATION PASSED")
        print(f"   All LLM functions comply with audit policy")

        # Mostrar stats de funciones compliant
        total_functions = sum(len(funcs) for funcs in results.values())
        if total_functions > 0:
            print(f"   Total LLM functions: {total_functions}")
            print(f"   All have @require_audit_log and call append_audit_log()")

        return

    print("\n❌ LLM AUDIT VIOLATIONS DETECTED\n")

    total_violations = 0
    for filepath, functions in violations.items():
        print(f"📁 {filepath}")

        for func in functions:
            total_violations += 1
            issues = []

            if not func.has_decorator:
                issues.append("Missing @require_audit_log decorator")

            if not func.calls_audit_log:
                issues.append("Missing append_audit_log() call")

            print(f"   ❌ {func.name} (line {func.lineno})")
            for issue in issues:
                print(f"      • {issue}")

        print()

    print(f"Total violations: {total_violations}")
    print("\nPolicy: ALL LLM functions must:")
    print("  1. Have @require_audit_log decorator")
    print("  2. Call append_audit_log() before returning")


# ============================================================================
# CLI
# ============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 backend/llm_audit_policy.py scan <directory>")
        print("  python3 backend/llm_audit_policy.py validate <directory>")
        print("\nExamples:")
        print("  python3 backend/llm_audit_policy.py scan backend/")
        print("  python3 backend/llm_audit_policy.py validate backend/")
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

        print(f"🔍 Scanning {directory} for LLM functions...\n")

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

        print(f"🔍 Validating {directory} against LLM audit policy...\n")

        is_valid = validate_codebase(directory)

        # Print report
        results = scan_directory(directory)
        print_violations_report(results)

        sys.exit(0 if is_valid else 1)

    else:
        print(f"Error: Unknown command '{command}'")
        print("Available commands: scan, validate")
        sys.exit(1)
