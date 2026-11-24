"""The food table and the three questions asked of it. Policy lives in `rules.yml`."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from fi_core.text import fold_accents

HERE = Path(__file__).parent

# Divides every amount; "proteina" answers "per 10 g of protein".
BASES = {"100g": (None, 1.0), "100kcal": ("energia", 100.0), "10g_proteina": ("proteina", 10.0)}
STATES = ("crudo", "seco", "cocido", "lata", "germinado", "congelado", "jugo", "harina", "inflado", "otro")

_STATE_WORDS = (
    ("lata", ("canned",)),
    ("harina", ("flour", "meal", "starch")),
    ("jugo", ("juice", "nectar")),
    ("cocido", ("cooked", "boiled", "baked", "steamed", "roasted", "fried", "microwaved", "toasted")),
    ("inflado", ("puffed",)),
    ("germinado", ("sprouted",)),
    ("congelado", ("frozen",)),
    ("seco", ("dry", "dried", "dehydrated", "freeze-dried")),
    ("crudo", ("raw", "uncooked", "fresh")),
)
_PLAIN_STATES = ("crudo", "seco", "otro")
_DRY_CATEGORIES = ("leguminosas", "cereales", "nueces-y-semillas")


class NutrientError(ValueError):
    """A question the table cannot answer; the message says why."""


@dataclass(frozen=True)
class Food:
    fdc_id: int
    source: str
    name: str
    spanish: str
    category: str
    state: str
    values: dict[str, float]

    @property
    def label(self) -> str:
        return f"{self.spanish} ({self.name})" if self.spanish else self.name


@lru_cache(maxsize=1)
def rules() -> dict[str, Any]:
    return yaml.safe_load((HERE / "rules.yml").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def aliases() -> dict[str, str]:
    return yaml.safe_load((HERE / "aliases.yml").read_text(encoding="utf-8"))


def _stem(word: str) -> str:
    """Spanish and English plurals fold to one form: frijoles/frijol, berries/berry."""
    if len(word) < 4:
        return word
    word = word[:-1] if word.endswith("s") and not word.endswith("ss") else word
    word = word[:-1] if word.endswith("e") else word
    return word[:-1] + "i" if word.endswith("y") else word


def _words(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", fold_accents(text).lower())]


def state_of(name: str, category: str, water: float | None) -> str:
    """Dry, cooked, canned...: a comparison across states is not a comparison of foods."""
    words = set(re.findall(r"[a-z-]+", name.lower()))
    state = next((s for s, marks in _STATE_WORDS if words & set(marks)), "otro")
    dry = water is not None and water < rules()["search"]["dry_water_g"]
    return "seco" if state in ("crudo", "otro") and dry and category in _DRY_CATEGORIES else state


@lru_cache(maxsize=1)
def foods() -> dict[int, Food]:
    table: dict[int, Food] = {}
    with (HERE / "foods.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            values = {k: float(row[k]) for k in rules()["nutrients"] if row[k] != ""}
            state = state_of(row["name"], row["category"], values.get("agua"))
            table[int(row["fdc_id"])] = Food(
                int(row["fdc_id"]), row["source"], row["name"], row["spanish"], row["category"], state, values
            )
    return table


_STATE_QUERY = {
    _stem(word): state
    for state, words in {
        "crudo": "crudo cruda raw fresco fresca",
        "seco": "seco seca dry dried",
        "cocido": "cocido cocida cooked boiled hervido hervida",
        "lata": "lata enlatado enlatada canned",
        "germinado": "germinado germinada sprouted",
        "congelado": "congelado congelada frozen",
        "harina": "harina flour",
        "jugo": "jugo juice",
    }.items()
    for word in words.split()
}
_STOP = {"de", "del", "la", "el", "los", "las", "en", "con", "y", "a", "un", "una"}


@lru_cache(maxsize=1)
def _alias_index() -> list[tuple[list[str], list[str]]]:
    pairs = [([w for w in _words(spanish) if w not in _STOP], _words(usda)) for spanish, usda in aliases().items()]
    return sorted(pairs, key=lambda p: -len(p[0]))


def _english(words: list[str]) -> list[str]:
    english: list[str] = []
    for spanish, usda in _alias_index():
        if all(w in words for w in spanish):
            english += usda
            words = [w for w in words if w not in spanish]
    return english + words


def search(query: str, *, state: str | None = None) -> list[Food]:
    """Foods whose name holds every word of `query` (Spanish or English), best first."""
    asked = state
    raw = [w for w in _words(query) if w not in _STOP]
    whole_alias = raw in [spanish for spanish, _ in _alias_index()]
    if not state and not whole_alias:
        state = next((_STATE_QUERY[w] for w in raw if w in _STATE_QUERY), None)
    words = raw if whole_alias else [w for w in raw if _STATE_QUERY.get(w) != state or state is None]
    if not words:
        return []
    found = _matches(words, state)
    return found or (_matches(words, None) if not asked else [])


def _matches(words: list[str], state: str | None) -> list[Food]:
    wanted = (words, _english(words))
    found = []
    for food in foods().values():
        if state and food.state != state:
            continue
        spanish, english = _words(food.spanish), _words(food.name)
        in_spanish = bool(spanish) and all(w in spanish for w in wanted[0])
        in_english = all(w in english for w in wanted[1])
        if not (in_spanish or in_english):
            continue
        leads = spanish[: len(words)] == words or (in_english and english[:1] == wanted[1][:1])
        exact = spanish == words
        altered = any(mark in food.name for mark in rules()["search"]["altered"])
        processed = state is None and food.state not in _PLAIN_STATES
        spread = max((english.index(w) for w in wanted[1] if w in english), default=len(english))
        found.append(((not exact, not leads, altered, processed, spread, len(english), food.source, food.name), food))
    return [food for _, food in sorted(found, key=lambda item: item[0])]


def amount(food: Food, nutrient: str, basis: str) -> float | None:
    """`nutrient` of `food` per `basis`; None when USDA did not measure one of the two."""
    if basis not in BASES:
        raise NutrientError(f"unknown basis {basis!r}; use one of {', '.join(BASES)}")
    value = food.values.get(nutrient)
    per, size = BASES[basis]
    if value is None or per is None:
        return value
    denominator = food.values.get(per)
    return value * size / denominator if denominator else None


def nutrient_keys(names: list[str] | None) -> list[str]:
    known = rules()["nutrients"]
    by_label = {fold_accents(s["label"]).lower(): k for k, s in known.items()}
    keys = []
    for name in names or []:
        plain = fold_accents(str(name)).lower().strip()
        key = plain.replace(" ", "_") if plain.replace(" ", "_") in known else by_label.get(plain)
        if key is None:
            raise NutrientError(f"unknown nutrient {name!r}; the table has: {', '.join(known)}")
        keys.append(key)
    return keys or list(known)


def rank(nutrient: str, *, category: str | None, state: str | None, basis: str, limit: int) -> list[tuple[Food, float]]:
    """The foods with most `nutrient`, measured values only, one row per name."""
    labels = set(rules()["categories"].values())
    if category and category not in labels:
        raise NutrientError(f"unknown category {category!r}; use one of {', '.join(sorted(labels))}")
    if state and state not in STATES:
        raise NutrientError(f"unknown state {state!r}; use one of {', '.join(STATES)}")
    scored = [
        (food, value)
        for food in foods().values()
        if (not category or food.category == category)
        and (not state or food.state == state)
        and "salt added" not in food.name
        and (value := amount(food, nutrient, basis)) is not None
    ]
    scored.sort(key=lambda item: -item[1])
    return scored[:limit]
