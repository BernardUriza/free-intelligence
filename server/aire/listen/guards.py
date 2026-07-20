"""Floods and gates. The bucket stops a LINE flood (per IP, not per connection:
reconnecting cannot reset it; idle IPs evicted). The connection caps stop a
CONNECTION flood from exhausting fds/RAM on the small box. `admit` adds the
whitelist gate (backlog #18) — FAIL CLOSED when enforcing: an unloaded roster
denies; a security control that self-disables on a DB blip is worse than none.
The DENIED-DEVICE line cures Carlos's failure #1: you SEE the forgotten device."""

import time

from . import roster
from .applog import _now, append
from .config import (MAX_CONNECTIONS, MAX_CONNECTIONS_PER_IP,
                     RATE_LIMIT_LINES_PER_MIN, WHITELIST_ENFORCE)


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


class ConnLimiter:
    def __init__(self, total: int, per_ip: int) -> None:
        self.total = total
        self.per_ip = per_ip
        self.n = 0
        self.by_ip: dict[str, int] = {}

    def acquire(self, ip: str) -> bool:
        if self.n >= self.total or self.by_ip.get(ip, 0) >= self.per_ip:
            return False
        self.n += 1
        self.by_ip[ip] = self.by_ip.get(ip, 0) + 1
        return True

    def release(self, ip: str) -> None:
        self.n = max(0, self.n - 1)
        left = self.by_ip.get(ip, 0) - 1
        if left <= 0:
            self.by_ip.pop(ip, None)
        else:
            self.by_ip[ip] = left


BUCKET = Bucket(RATE_LIMIT_LINES_PER_MIN)
CONNS = ConnLimiter(MAX_CONNECTIONS, MAX_CONNECTIONS_PER_IP)


def admit(ip: str, addr: str, exempt: bool) -> bool:
    if exempt:
        return True
    if not BUCKET.allow(ip):
        return False
    if WHITELIST_ENFORCE and not (roster.enabled() and roster.ready() and roster.allows(ip)):
        append(f"{_now()} {addr} DENIED-DEVICE")
        return False
    return True
