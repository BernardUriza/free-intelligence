"""Reusable card carousel for the Insult dashboard (no external deps)."""

from browser import document, html


class CardCarousel:
    """Simple horizontal scroll carousel with card selection."""

    def __init__(self, container_id, render_card, get_id, empty_msg="No data."):
        self.container_id = container_id
        self.render_card = render_card
        self.get_id = get_id
        self.empty_msg = empty_msg
        self.selected = ""

    def render(self, items):
        container = document[self.container_id]
        container.clear()

        if not items:
            container <= html.P(self.empty_msg, Class="empty-msg")
            return

        self.selected = ""
        track = html.DIV(Class="carousel-track")

        for item in items:
            card = self.render_card(item)
            item_id = self.get_id(item)
            card.attrs["data-card-id"] = item_id
            card.classList.add("carousel-card")
            card.bind("click", lambda ev, eid=item_id: self._select(eid))
            track <= card

        container <= track

    def _select(self, identifier):
        self.selected = identifier
        cards = document.select(f"#{self.container_id} .carousel-card")
        for card in cards:
            if card.attrs.get("data-card-id") == identifier:
                card.classList.add("selected")
            else:
                card.classList.remove("selected")

    def loading(self):
        container = document[self.container_id]
        container.clear()
        container <= html.DIV("Loading...", Class="empty-msg")
