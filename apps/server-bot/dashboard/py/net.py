"""Blob fetching — the single ajax shape every data source uses."""

import time

from browser import ajax


def fetch_json(url, on_complete):
    req = ajax.Ajax()
    req.open("GET", f"{url}?t={time.time()}", True)
    req.bind("complete", on_complete)
    req.send()
