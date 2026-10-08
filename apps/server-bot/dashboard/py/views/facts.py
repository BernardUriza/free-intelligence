"""Facts tab — per-user fact cards with user/category filters."""

from browser import document, html

from py.state import store
from py.views.shared import fmt_time


def render_facts():
    grid = document["facts-grid"]
    grid.clear()

    if not store.facts:
        grid <= html.P("No facts yet.", Class="empty-msg")
        return

    user_filter = document["facts-user-filter"].value
    cat_filter = document["facts-category-filter"].value

    users = {}
    categories = set()
    for f in store.facts:
        uid = f.get("user_id", "?")
        if user_filter != "all" and uid != user_filter:
            continue
        cat = f.get("category", "general")
        categories.add(cat)
        if cat_filter != "all" and cat != cat_filter:
            continue
        users.setdefault(uid, []).append(f)

    total_users = len({f.get("user_id", "") for f in store.facts})
    document["facts-stats"].text = f"{len(store.facts)} facts · {total_users} users"

    all_users = sorted({f.get("user_id", "?") for f in store.facts})
    _update_dropdown("facts-user-filter", all_users, user_filter)
    _update_dropdown("facts-category-filter", sorted(categories), cat_filter)

    for uid in sorted(users.keys()):
        facts = users[uid]
        card = html.DIV(Class="fact-user-card")

        header = html.DIV(Class="fact-user-header")
        header <= html.SPAN(uid, Class="fact-user-name")
        header <= html.SPAN(f"{len(facts)} facts", Class="fact-user-count")
        card <= header

        for f in facts:
            item = html.DIV(Class="fact-item")
            cat = f.get("category", "general")
            item <= html.SPAN(cat, Class=f"fact-category {cat}")
            item <= html.SPAN(f.get("fact", ""), Class="fact-text")
            ts = f.get("updated_at", 0)
            if ts:
                item <= html.SPAN(fmt_time(float(ts), "%m/%d"), Class="fact-time")
            card <= item

        grid <= card


def _update_dropdown(element_id, values, current):
    sel = document[element_id]
    sel.clear()
    sel <= html.OPTION("All", value="all")
    for v in values:
        opt = html.OPTION(v, value=v)
        if v == current:
            opt.attrs["selected"] = "selected"
        sel <= opt
