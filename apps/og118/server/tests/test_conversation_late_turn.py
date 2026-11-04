"""OG118-EXTERNAL-TURN-1 — an external engine's answer that outlives the live turn
lands in the record instead of being thrown away, and survives the stale client
PUT that follows."""

from __future__ import annotations

import uuid

from conversations import ConversationStore

OWNER = "google-oauth2|owner"
T0, T1, T2, T3 = (
    "2026-10-15T19:43:00.000Z",
    "2026-10-15T19:43:05.000Z",
    "2026-10-15T19:43:06.000Z",
    "2026-10-15T19:45:11.000Z",
)
USER_LATE = {"role": "user", "content": "Nos enseñaron que la propiedad privada…", "timestamp": T2}
ANSWER_LATE = {"role": "assistant", "content": "Chale, qué coraje.", "timestamp": T3, "reactions": ["🔥"]}


def _store(tmp_path) -> ConversationStore:
    return ConversationStore(tmp_path / "conversations")


def _record(cid: str) -> dict:
    return {
        "id": cid,
        "title": "inmobiliarias",
        "createdAt": T0,
        "updatedAt": T1,
        "messages": [
            {"role": "user", "content": "hola", "timestamp": T0},
            {"role": "assistant", "content": "qué onda", "timestamp": T1},
        ],
        "preview": "qué onda",
    }


def test_late_turn_appends_the_pair_marked_background(tmp_path) -> None:
    store, cid = _store(tmp_path), str(uuid.uuid4())
    store.put(OWNER, _record(cid))
    merged = store.append_late_turn(OWNER, cid, USER_LATE, ANSWER_LATE)
    tail = [(m["role"], m.get("origin"), m["content"]) for m in merged["messages"][-2:]]
    assert tail == [
        ("user", "background", USER_LATE["content"]),
        ("assistant", "background", ANSWER_LATE["content"]),
    ]
    assert merged["messages"][-1]["reactions"] == ["🔥"]
    assert merged["updatedAt"] == T3
    assert merged["preview"] == ANSWER_LATE["content"]
    assert store.get(OWNER, cid) == merged


def test_late_turn_does_not_duplicate_a_user_message_the_client_already_saved(tmp_path) -> None:
    store, cid = _store(tmp_path), str(uuid.uuid4())
    record = _record(cid)
    record["messages"].append({"role": "user", "content": USER_LATE["content"], "timestamp": T2})
    store.put(OWNER, record)
    merged = store.append_late_turn(OWNER, cid, USER_LATE, ANSWER_LATE)
    users = [m for m in merged["messages"] if m["role"] == "user" and m["content"] == USER_LATE["content"]]
    assert len(users) == 1
    assert merged["messages"][-1]["role"] == "assistant"


def test_late_turn_creates_the_record_for_a_never_persisted_conversation(tmp_path) -> None:
    store, cid = _store(tmp_path), str(uuid.uuid4())
    assert store.get(OWNER, cid) is None
    merged = store.append_late_turn(OWNER, cid, USER_LATE, ANSWER_LATE)
    assert merged["id"] == cid
    assert merged["createdAt"] == T2
    assert merged["title"] == USER_LATE["content"][:60].strip()
    assert [m["role"] for m in merged["messages"]] == ["user", "assistant"]
    assert store.list_for(OWNER)[0]["id"] == cid


def test_a_stale_client_put_cannot_erase_the_late_pair(tmp_path) -> None:
    store, cid = _store(tmp_path), str(uuid.uuid4())
    store.put(OWNER, _record(cid))
    store.append_late_turn(OWNER, cid, USER_LATE, ANSWER_LATE)
    stale = _record(cid)
    stale["messages"].append({"role": "user", "content": "¿y luego?", "timestamp": "2026-10-15T19:46:00.000Z"})
    kept = store.put_content(OWNER, stale)
    contents = [m["content"] for m in kept["messages"]]
    assert contents == ["hola", "qué onda", USER_LATE["content"], ANSWER_LATE["content"], "¿y luego?"]
