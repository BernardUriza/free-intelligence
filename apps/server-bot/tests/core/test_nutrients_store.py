"""The food table answers with a state and a basis, and never invents a number."""

from __future__ import annotations

import re

import pytest

from persona_core.nutrients import store


def names(query: str, **kw) -> list[str]:
    return [f.name for f in store.search(query, **kw)]


@pytest.mark.parametrize(
    ("query", "first"),
    [
        ("guayaba", "Guavas, common, raw"),
        ("lentejas", "Lentils, dry"),
        ("aceite de oliva", "Oil, olive, salad or cooking"),
        ("nopales", "Nopales, raw"),
        ("nuez de la india", "Nuts, cashew nuts, raw"),
        ("jitomates", "Tomato, roma"),
    ],
)
def test_a_mexican_name_finds_its_food(query, first):
    assert names(query)[0] == first


@pytest.mark.parametrize(
    ("query", "nutrient"),
    [
        ("lentejas", "hierro"),
        ("frijol negro", "proteina"),
        ("kale", "calcio"),
        ("aguacate", "grasa"),
        ("plátano", "potasio"),
        ("avena", "fibra"),
        ("pimiento morrón", "vitamina_c"),
        ("pepitas de calabaza", "zinc"),
        ("chía", "calcio"),
        ("almendras", "vitamina_e"),
        ("garbanzo seco", "proteina"),
        ("fresas", "vitamina_c"),
        ("nuez de brasil", "selenio"),
        ("brócoli crudo", "folato"),
    ],
)
def test_what_the_usda_cards_answered_the_table_answers(query, nutrient):
    assert any(nutrient in f.values for f in store.search(query))


@pytest.mark.parametrize(
    ("query", "state"),
    [("frijol negro cocido", "cocido"), ("frijoles negros secos", "seco"), ("garbanzos de lata", "lata")],
)
def test_the_state_in_the_query_filters(query, state):
    found = store.search(query)
    assert found
    assert {f.state for f in found} == {state}


def test_a_dry_legume_usda_calls_raw_is_dry():
    lentils = next(f for f in store.foods().values() if f.name == "Lentils, raw")
    assert lentils.state == "seco"
    guava = next(f for f in store.foods().values() if f.name == "Guavas, common, raw")
    assert guava.state == "crudo"


def test_an_unknown_food_is_empty_not_a_neighbour():
    assert store.search("unicornio") == []
    assert store.search("") == []


def test_no_animal_food_in_the_table():
    animal = re.compile(r"\b(chicken|beef|pork|ham|bacon|turkey|cheese|honey|eggs?|fish|lard|gelatin)\b", re.I)
    assert [f.name for f in store.foods().values() if animal.search(f.name)] == []
    assert store.search("huevo") == store.search("pollo") == []


def test_a_nutrient_usda_did_not_measure_is_none_never_zero():
    lentils = next(f for f in store.foods().values() if f.name == "Lentils, raw")
    assert "yodo" not in lentils.values
    assert store.amount(lentils, "yodo", "100g") is None


def test_the_basis_divides_by_the_declared_denominator():
    guava = next(f for f in store.foods().values() if f.name == "Guavas, common, raw")
    kcal = guava.values["energia"]
    assert store.amount(guava, "energia", "100kcal") == pytest.approx(100)
    assert store.amount(guava, "proteina", "100kcal") == pytest.approx(guava.values["proteina"] * 100 / kcal)
    with pytest.raises(store.NutrientError, match="basis"):
        store.amount(guava, "proteina", "porcion")


def test_nutrient_names_take_the_label_with_accents_and_reject_the_rest():
    assert store.nutrient_keys(["Proteína", "vitamina C"]) == ["proteina", "vitamina_c"]
    with pytest.raises(store.NutrientError, match="unknown nutrient"):
        store.nutrient_keys(["magia"])


def test_rank_compares_one_state_and_orders_descending():
    ranked = store.rank("hierro", category="leguminosas", state="cocido", basis="100g", limit=5)
    values = [v for _, v in ranked]
    assert values == sorted(values, reverse=True)
    assert {f.state for f, _ in ranked} == {"cocido"}
    with pytest.raises(store.NutrientError, match="category"):
        store.rank("hierro", category="carnes", state=None, basis="100g", limit=5)


def test_every_category_and_nutrient_in_the_rules_has_rows():
    rules = store.rules()
    assert {f.category for f in store.foods().values()} == set(rules["categories"].values())
    for key in rules["nutrients"]:
        assert any(key in f.values for f in store.foods().values()), key


def test_every_alias_finds_something():
    assert [a for a in store.aliases() if not store.search(a)] == []


@pytest.mark.parametrize(
    ("asked", "first"),
    [
        ("tortilla", "Tortilla, corn, shelf stable"),
        ("pimiento rojo", "Peppers, bell, red, raw"),
        ("chile morrón", "Peppers, sweet, green, raw"),
        ("manzana", "Apples, raw, without skin"),
    ],
)
def test_the_mexican_name_finds_the_plain_food_first(asked, first):
    assert store.search(asked)[0].name == first


@pytest.mark.parametrize("asked", ["camote", "uva", "naranja"])
def test_leaves_and_peel_never_answer_for_the_food(asked):
    assert not {w for w in ("leaves", "peel,") if w in store.search(asked)[0].name.lower()}


def test_a_wheat_mix_is_never_what_tortilla_means():
    assert all("wheat" not in f.name.lower() for f in store.search("tortilla"))
