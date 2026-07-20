"""Memory package — distributed repository architecture for Insult's longitudinal store.

What used to be a 1017-line monolith (`insult/core/memory.py`) is now a
package of 10+ focused modules:

- `connection.py`   ConnectionManager (schema init, migrations, WAL, vectors)
- `base.py`         BaseRepository (shared auto-reconnect)
- `context.py`      Pure functions: format_relative_time, build_context
- `store/`          MemoryStore facade package — preserves the legacy flat API
- `repositories/`   One module per domain (messages, facts, reminders, ...)

External callers should keep importing MemoryStore from this package —
the facade makes the refactor transparent. Internal modules that want a
specific domain can import the relevant repository directly:

    from khimeras_shared.memory.repositories import FactsRepository

See `store/__init__.py` for the rationale on keeping the facade rather than
switching every callsite to direct-repository injection.
"""

from khimeras_shared.memory.context import build_context, format_relative_time, format_relevant_block
from khimeras_shared.memory.store import MemoryStore

__all__ = ["MemoryStore", "build_context", "format_relative_time", "format_relevant_block"]
