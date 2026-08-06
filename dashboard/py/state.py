"""Shared dashboard state — one store instead of scattered module globals."""

from py import freshness


class Store:
    def __init__(self):
        self.metrics = {}
        self.alice_metrics = {}
        self.alice_missing = False
        self.logs = []
        self.traces = []
        self.facts = []
        self.log_filter = "all"
        self.current_tab = "monitor"
        self.data_produced_at = None
        self.data_age = None
        self.data_state = freshness.UNDATED


store = Store()
