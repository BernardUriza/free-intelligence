import re, sys, unicodedata
from pathlib import Path
sys.path.insert(0, sys.argv[3]); from es_map import FDB, ANIMAL_EXTRA
src, out = Path(sys.argv[1]), Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
def slug(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:60]
n = miss = skip = 0; seen = set()
for f in sorted(src.glob("*.md")):
    parts = f.read_text().split("\n\n")
    title, source = parts[0].lstrip("# ").strip(), parts[1]
    for p in parts[2:]:
        m = re.match(r"\*\*([^*]+)\*\*", p.strip())
        if not m: continue
        en = m.group(1)
        if en in ANIMAL_EXTRA: skip += 1; continue
        es = FDB.get(en)
        if not es: miss += 1; print("MISS", en); continue
        kind = "perfil aromático (FlavorDB2)"
        name = f"flavordb2_{slug(es)}_{slug(en)}"
        while name in seen: name += "-b"
        seen.add(name)
        body = f"# {es.capitalize()} ({en}): {kind}\n\n{es.capitalize()} ({en}). {p.strip()}\n\n{source}\n"
        (out / f"{name}.md").write_text(body, encoding="utf-8"); n += 1
print("written", n, "missing", miss, "skipped animal", skip)
