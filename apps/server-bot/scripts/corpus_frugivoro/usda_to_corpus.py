import json
import re
import sys
from collections import defaultdict
from pathlib import Path

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
PLANT = {
    "Vegetables and Vegetable Products": "verduras",
    "Fruits and Fruit Juices": "frutas",
    "Cereal Grains and Pasta": "cereales",
    "Legumes and Legume Products": "leguminosas",
    "Nut and Seed Products": "nueces-y-semillas",
    "Spices and Herbs": "especias",
    "Fats and Oils": "aceites",
}
ANIMAL_WORDS = re.compile(r"\b(butter|lard|tallow|egg|milk|cheese|chicken|beef|pork|fish|honey|ghee|cream)\b", re.I)
WANT = [
    ("Energy", "KCAL", "energía", "kcal"),
    ("Protein", None, "proteína", "g"),
    ("Total lipid (fat)", None, "grasa", "g"),
    ("Carbohydrate, by difference", None, "carbohidratos", "g"),
    ("Fiber, total dietary", None, "fibra", "g"),
    ("Sugars, Total", None, "azúcares", "g"),
    ("Glutamic acid", None, "ácido glutámico (base del umami)", "g"),
    ("Calcium, Ca", None, "calcio", "mg"),
    ("Iron, Fe", None, "hierro", "mg"),
    ("Magnesium, Mg", None, "magnesio", "mg"),
    ("Potassium, K", None, "potasio", "mg"),
    ("Sodium, Na", None, "sodio", "mg"),
    ("Zinc, Zn", None, "zinc", "mg"),
    ("Vitamin C, total ascorbic acid", None, "vitamina C", "mg"),
    ("Folate, total", None, "folato", "µg"),
    ("Vitamin A, RAE", None, "vitamina A (RAE)", "µg"),
    ("Vitamin K (phylloquinone)", None, "vitamina K", "µg"),
]

data = json.load(open(SRC))
foods = data[next(iter(data))]
by_cat = defaultdict(list)
for f in foods:
    cat = (f.get("foodCategory") or {}).get("description")
    if cat not in PLANT or ANIMAL_WORDS.search(f["description"]):
        continue
    vals = {}
    for n in f.get("foodNutrients", []):
        name = n["nutrient"]["name"]
        unit = (n["nutrient"].get("unitName") or "").upper()
        if n.get("amount") is None:
            continue
        for key, unit_req, label, out_unit in WANT:
            if name == key and (unit_req is None or unit == unit_req) and label not in vals:
                vals[label] = (n["amount"], out_unit)
    if len(vals) < 4:
        continue
    parts = [f"{label} {round(v, 2)} {u}" for (_, _, label, _) in WANT if (x := vals.get(label)) for v, u in [x]]
    by_cat[PLANT[cat]].append(
        f"**{f['description']}** (USDA FDC {f['fdcId']}, por 100 g): " + "; ".join(parts) + "."
    )

OUT.mkdir(parents=True, exist_ok=True)
total = 0
for slug, lines in by_cat.items():
    header = (
        f"# Composición nutrimental de {slug} — USDA FoodData Central, Foundation Foods\n\n"
        "Fuente: USDA FoodData Central, conjunto Foundation Foods, publicación 2025-12-18, "
        "https://fdc.nal.usda.gov/ — dominio público (CC0 1.0). Valores analíticos por 100 g de porción comestible, "
        "nombres del alimento en inglés tal como los publica USDA. El ácido glutámico es el aminoácido total "
        "(libre más ligado a proteína); el que da umami es sólo la fracción libre, que USDA no separa.\n\n"
    )
    (OUT / f"usda_fdc_foundation_{slug}.md").write_text(header + "\n\n".join(sorted(lines)) + "\n", encoding="utf-8")
    total += len(lines)
    print(slug, len(lines))
print("total", total)
