#!/usr/bin/env python3
"""Analyze File Sizes - Code Complexity Detection Tool.

Detecta archivos que exceden límites de tamaño recomendados.

Límites recomendados (Plan Geológico P3-1):
- Infrastructure: 300 líneas (max)
- Services: 400 líneas (max)
- Repositories: 350 líneas (max)
- API routers: 250 líneas (max)
- General: 500 líneas (warning threshold)

Uso:
    python backend/scripts/analyze-file-sizes.py
    python backend/scripts/analyze-file-sizes.py --threshold 300
    python backend/scripts/analyze-file-sizes.py --top 10

Exit codes:
    0 - All files within limits
    1 - Files exceed limits (warning only)

Author: Claude Code (P4-1 Developer Tooling)
Created: 2026-02-02
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FileSize:
    """Representa información de tamaño de un archivo."""

    path: Path
    lines: int
    layer: str  # infrastructure, services, api, etc.
    limit: int  # Límite recomendado para esa capa


class FileSizeAnalyzer:
    """Analiza tamaños de archivos y detecta candidatos para refactoring."""

    # Límites por capa (líneas)
    LAYER_LIMITS = {
        "infrastructure": 300,
        "services": 400,
        "repositories": 350,
        "api": 250,
        "mappers": 200,
        "domain": 300,
    }

    DEFAULT_LIMIT = 500

    def __init__(self, root_dir: Path):
        """Inicializa analizador.

        Args:
            root_dir: Directorio raíz del backend
        """
        self.root_dir = root_dir
        self.files: list[FileSize] = []

    def count_lines(self, file_path: Path) -> int:
        """Cuenta líneas en un archivo (excluyendo líneas vacías y comentarios solo).

        Args:
            file_path: Path al archivo

        Returns:
            Número de líneas significativas
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Contar solo líneas significativas (no vacías, no solo comentarios)
            significant = 0
            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    significant += 1

            return significant
        except (UnicodeDecodeError, PermissionError):
            return 0

    def detect_layer(self, file_path: Path) -> str:
        """Detecta a qué capa pertenece un archivo.

        Args:
            file_path: Path al archivo

        Returns:
            Nombre de la capa (infrastructure, services, etc.)
        """
        parts = file_path.parts
        for layer in self.LAYER_LIMITS.keys():
            if layer in parts:
                return layer
        return "other"

    def scan_directory(self, directory: Path) -> None:
        """Escanea recursivamente archivos Python.

        Args:
            directory: Directorio a escanear
        """
        for py_file in directory.rglob("*.py"):
            # Skip __pycache__, tests, scripts
            if any(
                skip in str(py_file)
                for skip in ["__pycache__", ".pyc", "/tests/", "/scripts/"]
            ):
                continue

            lines = self.count_lines(py_file)
            if lines == 0:
                continue

            layer = self.detect_layer(py_file)
            limit = self.LAYER_LIMITS.get(layer, self.DEFAULT_LIMIT)

            self.files.append(
                FileSize(path=py_file, lines=lines, layer=layer, limit=limit)
            )

    def get_violations(self) -> list[FileSize]:
        """Retorna archivos que exceden sus límites.

        Returns:
            Lista de FileSize que exceden límites
        """
        return [f for f in self.files if f.lines > f.limit]

    def get_top_files(self, n: int = 10) -> list[FileSize]:
        """Retorna los N archivos más grandes.

        Args:
            n: Número de archivos a retornar

        Returns:
            Lista de FileSize ordenada por tamaño descendente
        """
        return sorted(self.files, key=lambda f: f.lines, reverse=True)[:n]

    def report(self, show_top: int = 0) -> None:
        """Genera reporte de análisis de tamaño.

        Args:
            show_top: Si >0, muestra top N archivos más grandes
        """
        violations = self.get_violations()

        if not violations:
            print("✅ All files within recommended size limits!")
        else:
            print(f"⚠️  Found {len(violations)} file(s) exceeding size limits:\n")

            for file_size in sorted(violations, key=lambda f: f.lines, reverse=True):
                rel_path = file_size.path.relative_to(self.root_dir)
                excess = file_size.lines - file_size.limit
                percentage = (excess / file_size.limit) * 100

                print(f"📄 {rel_path}")
                print(
                    f"   Lines: {file_size.lines} (limit: {file_size.limit}, +{excess} lines, +{percentage:.0f}%)"
                )
                print(f"   Layer: {file_size.layer}")
                print(
                    f"   💡 Consider splitting into smaller modules (target: <{file_size.limit} lines)"
                )
                print()

        if show_top > 0:
            print(f"\n📊 Top {show_top} largest files:")
            top_files = self.get_top_files(show_top)

            for i, file_size in enumerate(top_files, 1):
                rel_path = file_size.path.relative_to(self.root_dir)
                status = "❌" if file_size.lines > file_size.limit else "✅"
                print(f"{i}. {status} {rel_path}: {file_size.lines} lines ({file_size.layer})")

        # Estadísticas generales
        if self.files:
            total_files = len(self.files)
            total_lines = sum(f.lines for f in self.files)
            avg_lines = total_lines / total_files

            print(f"\n📈 Statistics:")
            print(f"   Total files analyzed: {total_files}")
            print(f"   Total lines: {total_lines:,}")
            print(f"   Average file size: {avg_lines:.0f} lines")
            print(f"   Files exceeding limits: {len(violations)} ({len(violations)/total_files*100:.1f}%)")


def main() -> int:
    """Ejecuta el analizador de tamaños.

    Returns:
        0 si todo OK, 1 si hay violaciones (warning)
    """
    import argparse

    parser = argparse.ArgumentParser(description="Analyze Python file sizes")
    parser.add_argument(
        "--threshold",
        type=int,
        help="Override default threshold (lines)",
    )
    parser.add_argument(
        "--top", type=int, default=10, help="Show top N largest files (default: 10)"
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Root directory to scan (default: backend/)",
    )

    args = parser.parse_args()

    analyzer = FileSizeAnalyzer(root_dir=args.root)

    # Override límite general si se especifica
    if args.threshold:
        analyzer.DEFAULT_LIMIT = args.threshold

    # Escanear directorio completo
    analyzer.scan_directory(args.root)

    # Generar reporte
    analyzer.report(show_top=args.top)

    # Return 1 si hay violaciones (pero no falla CI, solo warning)
    violations = analyzer.get_violations()
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
