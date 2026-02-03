#!/usr/bin/env python3
"""Check Architecture Boundaries - Import Validation Tool.

Detecta violaciones de Clean Architecture detectando imports ilegales entre capas.

Reglas de arquitectura:
1. API no debe importar core/ (legacy, deprecado)
2. Domain no debe importar API (domain es capa interna)
3. Services no debe importar API (lógica de negocio independiente de HTTP)
4. Infrastructure puede importar de cualquier capa (capa externa)
5. Repositories no deben importar services (dependency inversion)

Uso:
    python backend/scripts/check-imports.py
    python backend/scripts/check-imports.py --fix-suggestions

Exit codes:
    0 - No violations found
    1 - Violations detected

Author: Claude Code (P4-1 Developer Tooling)
Created: 2026-02-02
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ImportViolation:
    """Representa una violación de import entre capas."""

    file: Path
    line: int
    imported_module: str
    reason: str
    suggestion: str


class ArchitectureLinter:
    """Valida que los imports respeten las reglas de Clean Architecture."""

    # Reglas: (origen_pattern, destino_pattern, razón, sugerencia)
    ILLEGAL_PATTERNS = [
        (
            "backend/api",
            "backend/core",
            "API no debe importar core/ (legacy deprecado)",
            "Usar services/ con Depends() injection",
        ),
        (
            "backend/domain",
            "backend/api",
            "Domain no debe importar API (inversión de dependencias)",
            "Domain solo debe importar interfaces, no implementaciones",
        ),
        (
            "backend/services",
            "backend/api",
            "Services no debe importar API (lógica de negocio independiente)",
            "Services solo debe depender de repositories y domain",
        ),
        (
            "backend/repositories",
            "backend/services",
            "Repositories no deben importar services (dependency inversion)",
            "Repositories solo deben implementar interfaces del domain",
        ),
        (
            "backend/mappers",
            "backend/api",
            "Mappers no deben importar API (mappers son puros)",
            "Mappers solo transforman domain ↔ persistence",
        ),
    ]

    def __init__(self, root_dir: Path):
        """Inicializa linter con directorio raíz del proyecto.

        Args:
            root_dir: Path al directorio raíz (e.g., /path/to/backend/)
        """
        self.root_dir = root_dir
        self.violations: list[ImportViolation] = []

    def check_file(self, file_path: Path) -> None:
        """Verifica imports en un archivo Python.

        Args:
            file_path: Path al archivo a verificar
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            return  # Skip archivos con errores de sintaxis

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._check_import(file_path, node.lineno, alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._check_import(file_path, node.lineno, node.module)

    def _check_import(self, file_path: Path, line: int, imported_module: str) -> None:
        """Verifica si un import específico viola las reglas.

        Args:
            file_path: Archivo que contiene el import
            line: Número de línea del import
            imported_module: Módulo importado (e.g., "backend.api.routers")
        """
        file_str = str(file_path)

        for source_pattern, target_pattern, reason, suggestion in self.ILLEGAL_PATTERNS:
            # Verificar si el archivo está en la capa origen
            if source_pattern in file_str:
                # Verificar si importa de la capa destino prohibida
                if target_pattern.replace("/", ".") in imported_module:
                    self.violations.append(
                        ImportViolation(
                            file=file_path,
                            line=line,
                            imported_module=imported_module,
                            reason=reason,
                            suggestion=suggestion,
                        )
                    )

    def scan_directory(self, directory: Path) -> None:
        """Escanea recursivamente un directorio buscando violaciones.

        Args:
            directory: Directorio a escanear
        """
        for py_file in directory.rglob("*.py"):
            # Skip __pycache__ y archivos de test
            if "__pycache__" in str(py_file) or ".pyc" in str(py_file):
                continue
            self.check_file(py_file)

    def report(self, show_suggestions: bool = False) -> None:
        """Imprime reporte de violaciones encontradas.

        Args:
            show_suggestions: Si True, muestra sugerencias de corrección
        """
        if not self.violations:
            print("✅ No architecture violations found!")
            return

        print(f"❌ Found {len(self.violations)} architecture violation(s):\n")

        for i, violation in enumerate(self.violations, 1):
            rel_path = violation.file.relative_to(self.root_dir)
            print(f"{i}. {rel_path}:{violation.line}")
            print(f"   Import: {violation.imported_module}")
            print(f"   Reason: {violation.reason}")

            if show_suggestions:
                print(f"   💡 Suggestion: {violation.suggestion}")

            print()


def main() -> int:
    """Ejecuta el linter de arquitectura.

    Returns:
        0 si no hay violaciones, 1 si hay violaciones
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Check Clean Architecture import boundaries"
    )
    parser.add_argument(
        "--fix-suggestions",
        action="store_true",
        help="Show suggestions for fixing violations",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Root directory to scan (default: backend/)",
    )

    args = parser.parse_args()

    linter = ArchitectureLinter(root_dir=args.root)

    # Escanear capas principales
    for layer in ["api", "domain", "services", "repositories", "mappers"]:
        layer_path = args.root / layer
        if layer_path.exists():
            linter.scan_directory(layer_path)

    linter.report(show_suggestions=args.fix_suggestions)

    return 1 if linter.violations else 0


if __name__ == "__main__":
    sys.exit(main())
