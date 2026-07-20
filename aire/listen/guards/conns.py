"""Connection caps, total and per IP: the bucket stops a LINE flood; this stops
a CONNECTION flood from exhausting fds/RAM on the small box."""

from ..config import MAX_CONNECTIONS, MAX_CONNECTIONS_PER_IP


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


CONNS = ConnLimiter(MAX_CONNECTIONS, MAX_CONNECTIONS_PER_IP)
