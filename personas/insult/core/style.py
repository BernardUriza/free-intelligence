"""Legacy re-export shim — user-style modeling moved to khimeras_shared.style (PR-1c).

UserStyleProfile and its language/formality/emoji classifiers model the USER's
writing style (persona-agnostic) and are persisted by the memory store, so they
belong in the shared layer alongside it. Single source of truth:
``khimeras_shared.style``.
"""

from khimeras_shared.style import UserStyleProfile

__all__ = ["UserStyleProfile"]
