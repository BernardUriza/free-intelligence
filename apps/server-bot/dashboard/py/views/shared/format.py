"""Time formatting shared by every dashboard view."""

import time


def fmt_uptime(seconds):
    s = int(seconds or 0)
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60}m"
    if s < 86400:
        return f"{s // 3600}h {(s % 3600) // 60}m"
    return f"{s // 86400}d {(s % 86400) // 3600}h"


def fmt_time(ts, fmt="%H:%M:%S", fallback="??:??:??"):
    return time.strftime(fmt, time.localtime(ts)) if ts else fallback
