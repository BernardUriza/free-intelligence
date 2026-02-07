#!/usr/bin/env python3
"""Generate Dependency Graph - Visualización de dependencias entre módulos.

Genera un grafo de dependencias entre módulos del backend para:
1. Detectar dependencias circulares
2. Visualizar arquitectura de capas
3. Identificar módulos altamente acoplados

Output formats:
- text: Listado textual de dependencias
- dot: Graphviz DOT format (requiere graphviz instalado)
- json: JSON para análisis programático

Uso:
    python backend/scripts/generate-dependency-graph.py
    python backend/scripts/generate-dependency-graph.py --format dot > deps.dot
    python backend/scripts/generate-dependency-graph.py --layer services

Visualizar con graphviz:
    python backend/scripts/generate-dependency-graph.py --format dot | dot -Tpng > deps.png

Author: Claude Code (P4-1 Developer Tooling)
Created: 2026-02-02
"""

from __future__ import annotations

import ast
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Module:
    """Representa un módulo Python."""

    name: str
    layer: str  # api, services, domain, infrastructure, etc.
    dependencies: set[str]  # Módulos que importa


class DependencyAnalyzer:
    """Analiza y visualiza dependencias entre módulos."""

    LAYERS = ["api", "services", "domain", "repositories", "mappers", "infrastructure"]

    def __init__(self, root_dir: Path):
        """Inicializa analizador.

        Args:
            root_dir: Directorio raíz del backend
        """
        self.root_dir = root_dir
        self.modules: dict[str, Module] = {}

    def detect_layer(self, module_path: str) -> str:
        """Detecta capa a la que pertenece un módulo.

        Args:
            module_path: Path del módulo (e.g., "backend.api.routers.session")

        Returns:
            Nombre de la capa
        """
        parts = module_path.split(".")
        for layer in self.LAYERS:
            if layer in parts:
                return layer
        return "other"

    def extract_imports(self, file_path: Path) -> set[str]:
        """Extrae módulos importados de un archivo.

        Args:
            file_path: Path al archivo Python

        Returns:
            Set de módulos importados (nombres completos)
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=str(file_path))
        except (SyntaxError, UnicodeDecodeError):
            return set()

        imports = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Solo backend imports
                    if alias.name.startswith("backend."):
                        imports.add(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith("backend."):
                    imports.add(node.module)

        return imports

    def scan_directory(self, directory: Path, layer_filter: str | None = None) -> None:
        """Escanea directorio y construye grafo de dependencias.

        Args:
            directory: Directorio a escanear
            layer_filter: Si se especifica, solo analiza esa capa
        """
        for py_file in directory.rglob("*.py"):
            # Skip __pycache__, tests
            if "__pycache__" in str(py_file) or "/tests/" in str(py_file):
                continue

            # Convertir path a module name
            rel_path = py_file.relative_to(self.root_dir.parent)
            module_name = str(rel_path).replace("/", ".").replace(".py", "")

            # Aplicar filtro de capa
            layer = self.detect_layer(module_name)
            if layer_filter and layer != layer_filter:
                continue

            # Extraer dependencias
            dependencies = self.extract_imports(py_file)

            # Filtrar dependencias a mismo backend
            backend_deps = {d for d in dependencies if d.startswith("backend.")}

            self.modules[module_name] = Module(
                name=module_name, layer=layer, dependencies=backend_deps
            )

    def detect_circular_dependencies(self) -> list[list[str]]:
        """Detecta dependencias circulares en el grafo.

        Returns:
            Lista de ciclos encontrados
        """
        cycles = []

        def dfs(node: str, visited: set[str], path: list[str]) -> None:
            if node in path:
                # Ciclo detectado
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                if cycle not in cycles:
                    cycles.append(cycle)
                return

            if node in visited or node not in self.modules:
                return

            visited.add(node)
            path.append(node)

            for dep in self.modules[node].dependencies:
                dfs(dep, visited.copy(), path.copy())

        for module in self.modules:
            dfs(module, set(), [])

        return cycles

    def generate_text_report(self) -> str:
        """Genera reporte textual de dependencias.

        Returns:
            String con reporte formateado
        """
        lines = [f"📊 Dependency Graph ({len(self.modules)} modules)\n"]

        # Agrupar por capa
        by_layer: dict[str, list[Module]] = defaultdict(list)
        for module in self.modules.values():
            by_layer[module.layer].append(module)

        for layer in sorted(by_layer.keys()):
            modules = by_layer[layer]
            lines.append(f"\n## {layer.upper()} ({len(modules)} modules)")

            for module in sorted(modules, key=lambda m: m.name):
                lines.append(f"\n### {module.name}")
                if module.dependencies:
                    for dep in sorted(module.dependencies):
                        dep_layer = self.detect_layer(dep)
                        lines.append(f"  → {dep} [{dep_layer}]")
                else:
                    lines.append("  (no dependencies)")

        # Detectar ciclos
        cycles = self.detect_circular_dependencies()
        if cycles:
            lines.append(f"\n\n⚠️  Circular Dependencies Detected ({len(cycles)}):")
            for i, cycle in enumerate(cycles, 1):
                lines.append(f"\n{i}. {' → '.join(cycle)}")

        return "\n".join(lines)

    def generate_dot_graph(self) -> str:
        """Genera grafo en formato Graphviz DOT.

        Returns:
            String en formato DOT
        """
        lines = ["digraph dependencies {"]
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box];')
        lines.append('')

        # Colores por capa
        colors = {
            "api": "lightblue",
            "services": "lightgreen",
            "domain": "lightyellow",
            "repositories": "lightpink",
            "mappers": "lightgray",
            "infrastructure": "lightcoral",
        }

        # Nodos
        for module in self.modules.values():
            color = colors.get(module.layer, "white")
            # Simplificar nombre para legibilidad
            short_name = module.name.split(".")[-1]
            lines.append(f'  "{module.name}" [label="{short_name}", fillcolor={color}, style=filled];')

        lines.append('')

        # Edges
        for module in self.modules.values():
            for dep in module.dependencies:
                if dep in self.modules:  # Solo deps dentro del backend
                    lines.append(f'  "{module.name}" -> "{dep}";')

        lines.append('}')
        return "\n".join(lines)

    def generate_json_report(self) -> str:
        """Genera reporte en formato JSON.

        Returns:
            String JSON
        """
        data: dict[str, Any] = {
            "modules": {},
            "statistics": {
                "total_modules": len(self.modules),
                "by_layer": {},
            },
        }

        # Módulos
        for name, module in self.modules.items():
            data["modules"][name] = {
                "layer": module.layer,
                "dependencies": list(module.dependencies),
                "dependency_count": len(module.dependencies),
            }

        # Estadísticas por capa
        by_layer: dict[str, int] = defaultdict(int)
        for module in self.modules.values():
            by_layer[module.layer] += 1

        data["statistics"]["by_layer"] = dict(by_layer)

        # Detectar ciclos
        cycles = self.detect_circular_dependencies()
        data["circular_dependencies"] = cycles

        return json.dumps(data, indent=2)


def main() -> int:
    """Ejecuta generador de grafo de dependencias.

    Returns:
        0 siempre (informacional)
    """
    import argparse

    parser = argparse.ArgumentParser(description="Generate dependency graph")
    parser.add_argument(
        "--format",
        choices=["text", "dot", "json"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--layer",
        choices=["api", "services", "domain", "repositories", "mappers", "infrastructure"],
        help="Filter by layer",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Root directory to scan (default: backend/)",
    )

    args = parser.parse_args()

    analyzer = DependencyAnalyzer(root_dir=args.root)
    analyzer.scan_directory(args.root, layer_filter=args.layer)

    if args.format == "text":
        print(analyzer.generate_text_report())
    elif args.format == "dot":
        print(analyzer.generate_dot_graph())
    elif args.format == "json":
        print(analyzer.generate_json_report())

    return 0


if __name__ == "__main__":
    sys.exit(main())
