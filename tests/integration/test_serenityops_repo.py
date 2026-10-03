"""Unit tests for the SerenityOps repository — token hashing + pure logic.

The DB-touching paths (insert_snapshot, get_latest_snapshot, etc.) live
behind asyncpg and ship the same fate as the rest of the post-PG repos:
they get reactivated once the asyncpg-pool fixture lands. These tests
cover the pieces that DON'T need a connection:

- `_hash_token` is deterministic and one-way (input != output, same input
  always lands on same hash).
- `_decode_jsonb` tolerates the three shapes asyncpg may hand us
  (None / dict / JSON-encoded str).
- `_hash_token` collisions across users are vanishingly unlikely — two
  fresh `secrets.token_urlsafe(32)` tokens produce distinct hashes.

The security claim "DB leak ≠ credential leak" hinges on the hash being
irreversible — that's a SHA-256 property and not tested here, but the
"deterministic + distinct" pair is.
"""

from __future__ import annotations

import json
import secrets

from persona_core.memory.repositories.serenityops import _decode_jsonb, _hash_token


class TestHashToken:
    def test_deterministic(self):
        token = "user-token-alex-abc123"  # noqa: S105 — fixture, not a real secret
        assert _hash_token(token) == _hash_token(token)

    def test_distinct_tokens_distinct_hashes(self):
        a = _hash_token("token-a")
        b = _hash_token("token-b")
        assert a != b

    def test_hash_is_hex_sha256(self):
        """64 hex chars — pins the algorithm so a silent swap to a shorter
        hash gets caught. If we ever need to rotate to a stronger primitive,
        the test will fail loudly and the migration plan can include
        the rehash sweep."""
        h = _hash_token("any-token")
        assert len(h) == 64
        assert all(c in "0123456789abcdef" for c in h)

    def test_does_not_leak_plaintext(self):
        """The hash must not include the original token as a substring —
        catches a silent regression to a non-hash transformation."""
        token = "VERY-SPECIFIC-NEEDLE-12345"  # noqa: S105 — fixture, not a real secret
        h = _hash_token(token)
        assert token not in h
        assert token.lower() not in h

    def test_realistic_token_pair_diverges(self):
        """Two freshly minted tokens (the production code path uses
        ``secrets.token_urlsafe(32)``) must hash to distinct values.
        Sanity check against any accidental collapse in the hash function."""
        a = _hash_token(secrets.token_urlsafe(32))
        b = _hash_token(secrets.token_urlsafe(32))
        assert a != b


class TestDecodeJsonb:
    def test_none_returns_none(self):
        assert _decode_jsonb(None) is None

    def test_dict_passthrough(self):
        """asyncpg's default JSONB codec already decodes — we pass through."""
        d = {"a": 1, "b": [2, 3]}
        assert _decode_jsonb(d) is d  # same object, no re-decode

    def test_list_passthrough(self):
        lst = [1, 2, {"x": "y"}]
        assert _decode_jsonb(lst) is lst

    def test_json_string_decodes(self):
        """If a row arrives as a JSON-encoded string (e.g. during data
        migration before the JSONB column was in place), parse it."""
        encoded = json.dumps({"hello": "world"})
        assert _decode_jsonb(encoded) == {"hello": "world"}

    def test_invalid_string_returns_none(self):
        """Garbage in → None out, not an exception. The prompt builder
        treats None as "no data" and skips the block."""
        assert _decode_jsonb("{not valid json") is None

    def test_unexpected_type_returns_none(self):
        """Numbers, bytes, etc. — anything we don't know how to interpret
        becomes None rather than poisoning downstream prompt assembly."""
        assert _decode_jsonb(42) is None
        assert _decode_jsonb(b"bytes") is None
