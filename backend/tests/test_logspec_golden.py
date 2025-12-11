from backend.observability.log_spec import REQUIRED_FIELDS


def _assert_log_shape(data: dict):
    for key in REQUIRED_FIELDS:
        assert key in data, f"missing {key}"


def test_assert_shape_sample():
    # simple synthetic sample
    sample = dict.fromkeys(REQUIRED_FIELDS, "-")
    sample["ts"] = "2025-12-11T00:00:00Z"
    _assert_log_shape(sample)
