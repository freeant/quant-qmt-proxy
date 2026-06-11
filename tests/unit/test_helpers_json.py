from __future__ import annotations

import json
import math

from app.utils.helpers import format_response, sanitize_json_value


def test_sanitize_json_value_converts_nan_and_inf_to_null():
    payload = {
        "open": float("nan"),
        "high": float("inf"),
        "low": float("-inf"),
        "close": 10.5,
        "nested": [{"volume": float("nan")}],
    }

    sanitized = sanitize_json_value(payload)

    assert sanitized["open"] is None
    assert sanitized["high"] is None
    assert sanitized["low"] is None
    assert sanitized["close"] == 10.5
    assert sanitized["nested"][0]["volume"] is None
    json.dumps(sanitized)


def test_format_response_is_json_serializable_with_non_finite_floats():
    response = format_response(
        data={"items": [{"bars": [{"open": float("nan"), "close": 1.0}]}]},
        message="ok",
    )

    encoded = json.dumps(response)
    decoded = json.loads(encoded)
    assert decoded["data"]["items"][0]["bars"][0]["open"] is None
    assert decoded["data"]["items"][0]["bars"][0]["close"] == 1.0
    assert not any(math.isnan(value) for value in [decoded["data"]["items"][0]["bars"][0]["close"]])
