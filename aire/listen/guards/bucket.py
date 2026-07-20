"""Token bucket per peer IP (per connection would reset on reconnect); idle IPs evicted."""

import time

from ..config import RATE_LIMIT_LINES_PER_MIN


class Bucket:
    def __init__(self, rate_per_min: int) -> None:
        self.rate, self.burst = rate_per_min / 60.0, float(rate_per_min)
        self._tokens: dict[str, float] = {}
        self._seen: dict[str, float] = {}

    def allow(self, ip: str) -> bool:
        now = time.monotonic()
        if len(self._seen) > 10_000:
            cutoff = now - 3600
            self._seen = {k: t for k, t in self._seen.items() if t >= cutoff}
            self._tokens = {k: v for k, v in self._tokens.items() if k in self._seen}
        last = self._seen.get(ip, now)
        tokens = min(self.burst, self._tokens.get(ip, self.burst) + (now - last) * self.rate)
        self._seen[ip] = now
        if tokens < 1.0:
            self._tokens[ip] = tokens
            return False
        self._tokens[ip] = tokens - 1.0
        return True


BUCKET = Bucket(RATE_LIMIT_LINES_PER_MIN)
