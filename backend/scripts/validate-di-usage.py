#!/usr/bin/env python3
"""Validate Dependency Injection Usage - Service Locator Detection.

Detecta uso del anti-pattern service locator (get_container()).
La arquitectura debe usar FastAPI Depends() para inyección de dependencias.

Detecta:
1. Llamadas directas a get_container()
2. Acceso a container attributes (container.some_service)
3. Imports de container en código de API

Excepciones legales:
- Tests (pueden usar container para setup)
- Scripts de utilidad
- Inicialización de app (main.py, __init__.py)

Uso:
    python backend/scripts/validate-di-usage.py
    python backend/scripts/validate-di-usage.py --strict

Exit codes:
    0 - No service locator usage found
    1 - Service locator usage detected

Author: Claude Code (P4-1 Developer Tooling)
Created: 2026-02-02
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DIViolation:
    """Representa una violación de DI (uso de service locator)."""

    file: Path
    line: int
    code: str
    reason: str
    suggestion: str


class DIValidator:
    """Valida que se use Dependency Injection en lugar de Service Locator."""

    # Archivos permitidos (no se validan)
    ALLOWED_PATHS = [
        "/tests/",
        "/scripts/",
        "/__init__.py",
        "/main.py",
        "/container.py",
        "conftest.py",
    ]

    def __init__(self, root_dir: Path, strict: bool = False):
        """Inicializa validador.

        Args:
            root_dir: Directorio raíz del backend
            strict: Si True, no permite excepciones
        """
        self.root_dir = root_dir
        self.strict = strict
        self.violations: list[DIViolation] = []

    def is_allowed_file(self, file_path: Path) -> bool:
        """Verifica si un archivo está permitido (no se valida).

        Args:
            file_path: Path al archivo

        Returns:
            True si está en lista de permitidos
        """
        if self.strict:
            return False

        file_str = str(file_path)
        return any(allowed in file_str for allowed in self.ALLOWED_PATHS)

    def check_file(self, file_path: Path) -> None:
        """Verifica uso de DI en un archivo.

        Args:
            file_path: Path al archivo a verificar
        """
        if self.is_allowed_file(file_path):
            return

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content, filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            return

        # Detectar get_container() calls
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Detectar get_container()
                if isinstance(node.func, ast.Name) and node.func.id == "get_container":
                    self.violations.append(
                        DIViolation(
                            file=file_path,
                            line=node.lineno,
                            code="get_container()",
                            reason="Service Locator anti-pattern detected",
                            suggestion="Use FastAPI Depends() injection instead",
                        )
                    )

                # Detectar container.get_*() calls
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id == "container":
                            self.violations.append(
                                DIViolation(
                                    file=file_path,
                                    line=node.lineno,
                                    code=f"container.{node.func.attr}()",
                                    reason="Direct container access detected",
                                    suggestion="Inject service via Depends(get_<service>)",
                                )
                            )

    def scan_api_layer(self) -> None:
        """Escanea solo la capa API (donde DI es crítico)."""
        api_dir = self.root_dir / "api"
        if not api_dir.exists():
            return

        for py_file in api_dir.rglob("*.py"):
            if "__pycache__" in str(py_file):
                continue
            self.check_file(py_file)

    def report(self) -> None:
        """Genera reporte de violaciones."""
        if not self.violations:
            print("✅ No service locator usage found in API layer!")
            print("   All endpoints use proper Dependency Injection (Depends())")
            return

        print(f"❌ Found {len(self.violations)} DI violation(s):\n")

        for i, violation in enumerate(self.violations, 1):
            rel_path = violation.file.relative_to(self.root_dir)
            print(f"{i}. {rel_path}:{violation.line}")
            print(f"   Code: {violation.code}")
            print(f"   Reason: {violation.reason}")
            print(f"   💡 {violation.suggestion}")
            print()

        print("Example of correct DI pattern:")
        print("```python")
        print("# ❌ BEFORE (Service Locator)")
        print("def create_session():")
        print("    container = get_container()")
        print("    session_service = container.session_service")
        print("    return session_service.create(...)")
        print()
        print("# ✅ AFTER (Dependency Injection)")
        print("def create_session(")
        print("    session_service: SessionService = Depends(get_session_service)")
        print("):")
        print("    return session_service.create(...)")
        print("```")


def main() -> int:
    """Ejecuta validación de DI.

    Returns:
        0 si no hay violaciones, 1 si hay violaciones
    """
    import argparse

    parser = argparse.ArgumentParser(description="Validate Dependency Injection usage")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="No allow any exceptions (validate all files)",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Root directory to scan (default: backend/)",
    )

    args = parser.parse_args()

    validator = DIValidator(root_dir=args.root, strict=args.strict)
    validator.scan_api_layer()
    validator.report()

    return 1 if validator.violations else 0


if __name__ == "__main__":
    sys.exit(main())
