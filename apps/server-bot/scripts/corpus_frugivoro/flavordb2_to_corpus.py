import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SRC = Path(sys.argv[1])
OUT = Path(sys.argv[2])
ANIMAL_CATEGORY = re.compile(r"meat|fish|seafood|dairy|animal|egg|poultry|insect|^dish$", re.I)
ANIMAL_NAME = re.compile(
    r"\b(beef|pork|chicken|lamb|mutton|turkey|duck|goose|egg|milk|cheese|butter|cream|yogurt|honey|"
    r"fish|salmon|tuna|cod|shrimp|crab|lobster|oyster|clam|mussel|squid|caviar|gelatin|lard|bacon|ham|"
    r"sausage|casein|anchovy|herring|sardine|mackerel|trout|venison|veal|liver)\b",
    re.I,
)

by_cat = defaultdict(list)
skipped = Counter()
for p in sorted(SRC.glob("*.json"), key=lambda x: int(x.stem)):
    d = json.loads(p.read_text())
    name = d.get("entity_alias_readable") or ""
    cat = d.get("category_readable") or "Otros"
    if ANIMAL_CATEGORY.search(cat) or ANIMAL_NAME.search(name):
        skipped[cat] += 1
        continue
    mols = d.get("molecules") or []
    if not mols:
        continue
    descriptors = Counter()
    for m in mols:
        for tag in (m.get("flavor_profile") or "").split("@"):
            tag = tag.strip().lower()
            if tag:
                descriptors[tag] += 1
    bitter = sum(1 for m in mols if m.get("bitter"))
    named = [m for m in mols if m.get("fema_flavor_profile")]
    named.sort(key=lambda m: len(m.get("fema_flavor_profile") or ""), reverse=True)
    keys = "; ".join(f"{m['common_name']} ({m['fema_flavor_profile'].lower()})" for m in named[:6])
    top = ", ".join(f"{t} ({n})" for t, n in descriptors.most_common(14))
    source = d.get("natural_source_name") or ""
    para = (
        f"**{name}** — categoría {cat}"
        + (f", fuente natural {source}" if source else "")
        + f". FlavorDB2 le asocia {len(mols)} moléculas de sabor"
        + (f", {bitter} marcadas como amargas" if bitter else "")
        + f". Descriptores de aroma más frecuentes entre sus moléculas (cuántas moléculas los traen): {top}."
        + (f" Moléculas con perfil FEMA: {keys}." if keys else "")
    )
    by_cat[cat].append(para)

OUT.mkdir(parents=True, exist_ok=True)
header_tpl = (
    "# Perfil aromático por ingrediente — {cat} (FlavorDB2)\n\n"
    "Fuente: FlavorDB2, Complex Systems Lab, IIIT-Delhi, https://cosylab.iiitd.edu.in/flavordb2/ — licencia "
    "CC BY-NC-SA 3.0 (uso no comercial). Extraído el 2026-11-24 de los JSON públicos por entidad. Cada ingrediente "
    "trae las moléculas de sabor que la base le asocia y los descriptores de aroma de esas moléculas. Es la lista de "
    "lo que PUEDE oler, no de cuánto: FlavorDB no da concentraciones. Compartir moléculas no predice que dos "
    "ingredientes combinen (Jain 2015, Spence 2020); úsalo para entender el aroma de un ingrediente, no para "
    "decidir maridajes.\n\n"
)
total = 0
for cat, paras in sorted(by_cat.items()):
    slug = re.sub(r"[^a-z0-9]+", "-", cat.lower()).strip("-")
    (OUT / f"flavordb2_{slug}.md").write_text(header_tpl.format(cat=cat) + "\n\n".join(paras) + "\n", encoding="utf-8")
    total += len(paras)
    print(f"{cat}: {len(paras)}")
print("total", total, "skipped", dict(skipped))
