"""Build `persona_core/nutrients/foods.csv` from the USDA JSON releases (CC0).

    python scripts/nutrients/build_foods.py <foundation.json> <sr_legacy.json>

Downloads: https://fdc.nal.usda.gov/fdc-datasets/ . What enters is declared in
`persona_core/nutrients/rules.yml`.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "corpus_frugivoro"))

from es_map import USDA as SPANISH  # noqa: E402

NUTRIENTS_DIR = ROOT / "persona_core" / "nutrients"
COLUMNS = ("fdc_id", "source", "name", "spanish", "category")


def spanish_name(description: str) -> str:
    """The Spanish name of the longest comma prefix the map knows, else empty."""
    parts = re.sub(r" \(0% moisture\)$", "", description).split(",")
    return next((SPANISH[k] for n in range(len(parts), 1, -1) if (k := ",".join(parts[:n])) in SPANISH), "")


def extra_label(description: str, extra: dict) -> str | None:
    return next((label for pattern, label in extra.items() if re.search(pattern, description)), None)


def is_plant(description: str, category: str, build: dict) -> bool:
    if category == "Fats and Oils" and not re.search(build["oils_only"], description):
        return False
    if re.search(build["branded"], description) or re.search(build["composite"], description, re.I):
        return False
    return not re.search(build["animal"], re.sub(build["plant_words"], " ", description, flags=re.I), re.I)


def rows(path: Path, source: str, rules: dict):
    data = json.loads(path.read_text(encoding="utf-8"))
    for food in data[next(iter(data))]:
        category = (food.get("foodCategory") or {}).get("description")
        description = " ".join(food["description"].split())
        label = rules["categories"].get(category) or extra_label(description, rules["extra"])
        if not label or not is_plant(description, category, rules["build"]):
            continue
        amounts: dict[int, float] = {}
        for item in food["foodNutrients"]:
            if item.get("amount") is not None:
                amounts.setdefault(item["nutrient"]["id"], item["amount"])
        values = {
            key: next((amounts[i] for i in spec["ids"] if i in amounts), None)
            for key, spec in rules["nutrients"].items()
        }
        if sum(v is not None for v in values.values()) < rules["build"]["min_nutrients"]:
            continue
        row = (food["fdcId"], source, description, spanish_name(description), label)
        yield dict(zip(COLUMNS, row, strict=True)) | {
            k: "" if v is None else f"{v:.4g}" for k, v in values.items()
        }


def main() -> int:
    rules = yaml.safe_load((NUTRIENTS_DIR / "rules.yml").read_text(encoding="utf-8"))
    out = [*rows(Path(sys.argv[1]), "F", rules), *rows(Path(sys.argv[2]), "S", rules)]
    out.sort(key=lambda r: (r["source"], r["category"], r["name"], int(r["fdc_id"])))
    with (NUTRIENTS_DIR / "foods.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[*COLUMNS, *rules["nutrients"]], lineterminator="\n")
        writer.writeheader()
        writer.writerows(out)
    print(len(out), "foods")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
