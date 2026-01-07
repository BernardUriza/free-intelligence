#!/usr/bin/env python3
"""
Split Bryntum JS into manageable modules.

This script analyzes the beautified Bryntum JS file and splits it into
logical module files based on class definitions.

Usage:
    python3 scripts/split-bryntum.py
"""

import re
import os
from pathlib import Path

# Paths
BRYNTUM_JS = Path("public/js/bryntum/schedulerpro.wc.module.js")
MODULES_DIR = Path("public/js/bryntum/modules")

# Key modules to extract (class name -> filename)
KEY_MODULES = {
    # Core utilities
    "BrowserHelper": "01-browser-helper",
    "StringHelper": "02-string-helper",
    "Objects": "03-objects",
    "VersionHelper": "04-version-helper",
    "Config": "05-config",
    "Base": "06-base",

    # Events and DOM
    "EventHelper": "10-event-helper",
    "DomHelper": "11-dom-helper",
    "DomSync": "12-dom-sync",

    # Data
    "Model": "20-model",
    "Store": "21-store",
    "Collection": "22-collection",

    # Drag functionality (CRITICAL)
    "DragHelper": "30-drag-helper",
    "DragContext": "31-drag-context",
    "DragProxy": "32-drag-proxy",
    "DragCreateBase": "33-drag-create-base",
    "EventDragCreate": "34-event-drag-create",  # THIS IS THE KEY ONE

    # Events/Appointments
    "EventModel": "40-event-model",
    "EventStore": "41-event-store",
    "CoreEventMixin": "42-core-event-mixin",

    # Scheduler
    "SchedulerBase": "50-scheduler-base",
    "TimelineBase": "51-timeline-base",
    "TimeAxisViewModel": "52-time-axis-view-model",

    # Resources
    "ResourceModel": "60-resource-model",
    "ResourceStore": "61-resource-store",
    "ResourceTimeRangeModel": "62-resource-time-range-model",
}

def find_class_boundaries(content: str) -> list:
    """Find start/end lines for each class definition."""
    lines = content.split('\n')
    classes = []

    # Pattern for class definitions
    class_pattern = re.compile(r'^var\s+(\w+)\s*=\s*class')

    current_class = None
    current_start = None
    brace_count = 0
    in_class = False

    for i, line in enumerate(lines):
        match = class_pattern.match(line)

        if match and not in_class:
            # Found new class
            if current_class:
                # Save previous class
                classes.append({
                    'name': current_class,
                    'start': current_start,
                    'end': i - 1
                })

            current_class = match.group(1)
            current_start = i
            in_class = True
            brace_count = 0

        if in_class:
            brace_count += line.count('{') - line.count('}')

            # Check if class ended (semicolon after closing brace)
            if brace_count <= 0 and line.strip().endswith('};'):
                classes.append({
                    'name': current_class,
                    'start': current_start,
                    'end': i
                })
                current_class = None
                in_class = False

    return classes


def extract_module(content: str, class_info: dict) -> str:
    """Extract a class and its dependencies."""
    lines = content.split('\n')
    start = max(0, class_info['start'] - 5)  # Include some context
    end = min(len(lines), class_info['end'] + 2)

    return '\n'.join(lines[start:end])


def main():
    print(f"Reading {BRYNTUM_JS}...")
    content = BRYNTUM_JS.read_text()
    lines = content.split('\n')
    total_lines = len(lines)
    print(f"Total lines: {total_lines:,}")

    # Find all classes
    print("\nFinding class boundaries...")
    classes = find_class_boundaries(content)
    print(f"Found {len(classes)} classes")

    # Create modules directory
    MODULES_DIR.mkdir(parents=True, exist_ok=True)

    # Extract key modules
    print("\nExtracting key modules...")
    extracted = []

    for class_info in classes:
        class_name = class_info['name']

        if class_name in KEY_MODULES:
            filename = KEY_MODULES[class_name]
            module_content = extract_module(content, class_info)

            output_path = MODULES_DIR / f"{filename}.js"
            output_path.write_text(module_content)

            line_count = len(module_content.split('\n'))
            extracted.append({
                'name': class_name,
                'file': filename,
                'lines': line_count,
                'start': class_info['start'],
                'end': class_info['end']
            })

            print(f"  {filename}.js ({line_count:,} lines) - {class_name}")

    # Create index file with line references
    index_content = """/**
 * Bryntum Module Index
 *
 * This file maps class names to their locations in the original file
 * and the extracted module files.
 *
 * IMPORTANT: The main file is still used at runtime.
 * These modules are for editing/patching only.
 */

export const BRYNTUM_MODULES = {
"""

    for mod in extracted:
        index_content += f"""  {mod['name']}: {{
    file: '{mod['file']}.js',
    originalLines: [{mod['start']}, {mod['end']}],
    extractedLines: {mod['lines']},
  }},
"""

    index_content += "};\n"

    # Add all class locations
    index_content += """
/**
 * All classes and their line numbers in the original file
 */
export const ALL_CLASSES = {
"""

    for class_info in classes:
        index_content += f"  '{class_info['name']}': [{class_info['start']}, {class_info['end']}],\n"

    index_content += "};\n"

    (MODULES_DIR / "index.js").write_text(index_content)
    print(f"\nCreated index.js")

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total classes: {len(classes)}")
    print(f"Extracted modules: {len(extracted)}")
    print(f"Output directory: {MODULES_DIR}")
    print(f"\nKey file for drag-create validation:")
    print(f"  modules/34-event-drag-create.js")
    print(f"  Original lines: 168386-168685 (approx)")


if __name__ == "__main__":
    main()
