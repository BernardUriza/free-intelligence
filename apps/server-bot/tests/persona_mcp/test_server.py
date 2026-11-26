from persona_mcp import server


def test_turn_rides_bernards_principal_through_the_runner_pipeline():
    body = server.turn_body("frugivoro", "hola", None)
    assert body["user_id"] == server.BERNARD_PRINCIPAL
    assert body["pipeline"] == "runner"
    assert body["channel_id"] == "claude-code-frugivoro"
    assert not body["user_id"].startswith("probe-")


def test_thread_splits_the_channel():
    assert server.turn_body("insult", "x", "mealprep")["channel_id"] == "claude-code-insult-mealprep"


def test_ask_polls_the_job_until_done():
    calls = []

    def http(method, path, body=None, timeout=None):
        calls.append((method, path))
        if method == "POST":
            return {"job_id": "j1"}
        return {"status": "done", "response": {"text": "ok"}} if len(calls) > 2 else {"status": "running"}

    assert server.ask("frugivoro", "hola", http=http, sleep=lambda _s: None) == {"text": "ok"}
    assert calls[0] == ("POST", "/v1/turn/jobs")


def test_every_turn_carries_its_own_job_id():
    a, b = server.turn_body("frugivoro", "x", None), server.turn_body("frugivoro", "x", None)
    assert a["job_id"] and a["job_id"] != b["job_id"]


def test_cold_start_submit_timeout_retries_the_same_turn():
    submitted = []

    def http(method, path, body=None, timeout=None):
        if method == "POST":
            submitted.append((body["job_id"], timeout))
            if len(submitted) == 1:
                raise TimeoutError("The read operation timed out")
            return {"job_id": body["job_id"]}
        return {"status": "done", "response": {"text": "desayuno"}}

    assert server.ask("frugivoro", "hola", http=http, sleep=lambda _s: None) == {"text": "desayuno"}
    assert len(submitted) == 2 and submitted[0][0] == submitted[1][0]
    assert submitted[0][1] >= 170


def test_poll_timeout_keeps_waiting_instead_of_failing():
    polls = []

    def http(method, path, body=None, timeout=None):
        if method == "POST":
            return {"job_id": "j1"}
        polls.append(path)
        if len(polls) == 1:
            raise TimeoutError("The read operation timed out")
        return {"status": "done", "response": {"text": "ok"}}

    assert server.ask("insult", "x", http=http, sleep=lambda _s: None) == {"text": "ok"}
    assert all("wait_s=" in p for p in polls)


def test_gives_up_after_the_turn_budget():
    import pytest

    now = [0.0]

    def clock():
        return now[0]

    def sleep(s):
        now[0] += s

    def http(method, path, body=None, timeout=None):
        now[0] += 60
        raise TimeoutError("The read operation timed out")

    with pytest.raises(TimeoutError):
        server.ask("insult", "x", http=http, sleep=sleep, clock=clock)


def test_unexposed_persona_is_an_error_not_a_turn():
    out = server.tools_call({"name": "ask_persona", "arguments": {"persona": "alice", "text": "x"}})
    assert out["isError"] is True


def test_empty_reply_is_reported_as_failure():
    out = server.tools_call(
        {"name": "ask_persona", "arguments": {"persona": "insult", "text": "x"}},
        asker=lambda *_a: {"text": "", "empty_reason": "router_timeout"},
    )
    assert out["isError"] is True and "router_timeout" in out["content"][0]["text"]


def test_notifications_get_no_reply():
    assert server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


def test_non_https_runner_is_refused(monkeypatch):
    monkeypatch.setenv("PERSONA_RUNNER_URL", "file:///etc/passwd")
    import pytest

    with pytest.raises(ValueError):
        server.runner_url()
