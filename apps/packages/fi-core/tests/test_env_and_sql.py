from fi_core.env import env_flag
from fi_core.sql import affected_rows


def test_env_flag(monkeypatch):
    monkeypatch.setenv("FI_FLAG", " Yes ")
    assert env_flag("FI_FLAG") is True
    monkeypatch.setenv("FI_FLAG", "0")
    assert env_flag("FI_FLAG", default=True) is False
    monkeypatch.delenv("FI_FLAG")
    assert env_flag("FI_FLAG", default=True) is True


def test_affected_rows():
    assert affected_rows("DELETE 3") == 3
    assert affected_rows("INSERT 0 1") == 1
    assert affected_rows("UPDATE 0") == 0
    assert affected_rows(None) == 0
    assert affected_rows("CREATE TABLE") == 0
