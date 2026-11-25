"""MCP tools over the USDA food table: numbers are looked up, never recalled.

They carry no identity: the table is public and the same for everyone.
"""

from __future__ import annotations

from persona_core.nutrients import store
from persona_runner.mcp_tools import shared
from persona_runner.mcp_tools.tooldef import tool

_STATE = {"type": "string", "enum": list(store.STATES), "description": "state of the food; omit for any"}
_BASIS = {
    "type": "string",
    "enum": list(store.BASES),
    "description": "100g (default), 100kcal, or 10g_proteina",
}


def _line(food: store.Food) -> str:
    return f"- fdc_id {food.fdc_id} | {food.label} | estado: {food.state} | {food.category} | fuente {food.source}"


def _number(value: float | None) -> str:
    return "sin dato" if value is None else f"{value:.3g}"


def _ratio(values: list[float | None], basis: str) -> str:
    measured = [v for v in values if v is not None]
    if len(measured) < 2 or min(measured) <= 0:
        return ""
    return f" -> el mayor es {max(measured) / min(measured):.3g} veces el menor ({basis.replace('_', ' de ')})"


def _sources(foods: list[store.Food]) -> str:
    used = sorted({f.source for f in foods})
    return "Fuente: " + "; ".join(f"{s} = {store.rules()['sources'][s]}" for s in used)


@tool(
    "food_lookup",
    (
        "Find a plant food in the USDA composition table by name, in Spanish or English "
        "('guayaba', 'frijol negro cocido', 'black beans raw'). Returns the candidates with their fdc_id and "
        "STATE (dry, cooked, canned...). Pick the one the person means: a dry grain holds about three "
        "times the nutrients of the cooked one. Then call nutrient_compare with the ids."
    ),
    {
        "type": "object",
        "properties": {"query": {"type": "string"}, "state": _STATE},
        "required": ["query"],
    },
)
async def food_lookup(args: dict) -> dict:
    query = str(args.get("query") or "").strip()
    if not query:
        return shared._error("query is required")
    state = args.get("state") or None
    found = store.search(query, state=state)
    if not found:
        return shared._text(
            f"No hay '{query}'" + (f" en estado '{state}'" if state else "") + " en la tabla. "
            "Eso no dice que no tenga nutrientes: prueba otro nombre (en inglés también) o di que no tienes el dato."
        )
    cap = store.rules()["search"]["max_candidates"]
    head = f"{len(found)} alimentos para '{query}'" + (f"; van los primeros {cap}" if len(found) > cap else "")
    return shared._text("\n".join([head, *(_line(f) for f in found[:cap])]))


@tool(
    "nutrient_compare",
    (
        "The measured nutrients of one or several foods side by side, by fdc_id (from food_lookup). Use it for any "
        "number you are going to state or compare. `nutrients` are keys such as proteina, hierro, calcio, zinc, "
        "fibra, folato, vitamina_c, omega3_ala, lisina, b12; omit for all. Each line already carries how many times the "
        "largest is the smallest: state that figure, never your own arithmetic. 'sin dato' means USDA did not measure it, "
        "never zero."
    ),
    {
        "type": "object",
        "properties": {
            "fdc_ids": {"type": "array", "items": {"type": "integer"}, "minItems": 1},
            "nutrients": {"type": "array", "items": {"type": "string"}},
            "basis": _BASIS,
        },
        "required": ["fdc_ids"],
    },
)
async def nutrient_compare(args: dict) -> dict:
    cap = store.rules()["search"]["max_compare"]
    basis = args.get("basis") or "100g"
    try:
        ids = [int(i) for i in args.get("fdc_ids") or []]
        keys = store.nutrient_keys(args.get("nutrients"))
        if not ids or len(ids) > cap:
            raise store.NutrientError(f"give 1 to {cap} fdc_ids")
        if missing := [i for i in ids if i not in store.foods()]:
            raise store.NutrientError(f"not in the table: {missing}; ids come from food_lookup")
        picked = [store.foods()[i] for i in ids]
        table = {k: [store.amount(f, k, basis) for f in picked] for k in keys}
    except (store.NutrientError, TypeError, ValueError) as err:
        return shared._error(str(err))
    lines = [f"Base: por {basis.replace('_', ' de ')}", *(_line(f) for f in picked)]
    if len({f.state for f in picked}) > 1:
        lines.append("OJO: los estados no coinciden; no los presentes como el mismo alimento en igualdad.")
    spec = store.rules()["nutrients"]
    for key, values in table.items():
        if any(v is not None for v in values):
            lines.append(
                f"{spec[key]['label']} ({spec[key]['unit']}): "
                + " | ".join(_number(v) for v in values)
                + _ratio(values, basis)
            )
    if unmeasured := [spec[k]["label"] for k, v in table.items() if all(x is None for x in v)]:
        lines.append("Sin dato en todos: " + ", ".join(unmeasured))
    return shared._text("\n".join([*lines, _sources(picked)]))


@tool(
    "nutrient_rank",
    (
        "Which plant foods have the most of one nutrient, measured values only. Give `category` (verduras, frutas, "
        "cereales, leguminosas, nueces-y-semillas, especias, aceites) and `state` so the list compares like with like; "
        "without them, dry spices win everything and nobody eats 100 g of oregano."
    ),
    {
        "type": "object",
        "properties": {
            "nutrient": {"type": "string"},
            "category": {"type": "string"},
            "state": _STATE,
            "basis": _BASIS,
            "limit": {"type": "integer"},
        },
        "required": ["nutrient"],
    },
)
async def nutrient_rank(args: dict) -> dict:
    basis = args.get("basis") or "100g"
    try:
        limit = max(1, min(int(args.get("limit") or 10), store.rules()["search"]["max_rank"]))
        (key,) = store.nutrient_keys([args.get("nutrient") or ""])
        ranked = store.rank(
            key, category=args.get("category") or None, state=args.get("state") or None, basis=basis, limit=limit
        )
    except (store.NutrientError, TypeError, ValueError) as err:
        return shared._error(str(err))
    if not ranked:
        return shared._text("Ningún alimento de la tabla tiene ese dato con esos filtros.")
    spec = store.rules()["nutrients"][key]
    lines = [f"{spec['label']} ({spec['unit']}) por {basis.replace('_', ' de ')}"]
    lines += [f"- {_number(v)} | {f.label} | estado: {f.state} | fdc_id {f.fdc_id}" for f, v in ranked]
    return shared._text("\n".join([*lines, _sources([f for f, _ in ranked])]))


FOOD_DATA_TOOLS = [food_lookup, nutrient_compare, nutrient_rank]
FOOD_DATA_SERVER_NAME = "food_data"
