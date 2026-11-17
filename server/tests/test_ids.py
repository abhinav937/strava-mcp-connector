"""Unit tests for 64-bit activity/athlete ID handling."""

from __future__ import annotations

import json

import pytest

from strava_mcp.ids import as_str_id, entity_id, optional_str_id
from strava_mcp.models import MetaActivity, MetaAthlete, SummaryActivity
from strava_mcp.response_builder import ResponseBuilder

# Larger than JavaScript Number.MAX_SAFE_INTEGER (2^53 - 1)
UNSAFE_JS_ID = 9_007_199_254_740_993
UNSAFE_JS_ID_STR = "9007199254740993"
I64_MAX = 9_223_372_036_854_775_807
I64_MAX_STR = "9223372036854775807"


def test_as_str_id_accepts_str_and_int_without_coercing_strings() -> None:
    assert as_str_id(UNSAFE_JS_ID_STR) == UNSAFE_JS_ID_STR
    assert as_str_id(f"  {I64_MAX_STR}  ") == I64_MAX_STR
    assert as_str_id(UNSAFE_JS_ID) == UNSAFE_JS_ID_STR
    assert as_str_id(12345) == "12345"


def test_as_str_id_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        as_str_id("")
    with pytest.raises(ValueError):
        as_str_id("   ")
    with pytest.raises(ValueError):
        as_str_id(None)
    with pytest.raises(ValueError):
        as_str_id(True)
    with pytest.raises(ValueError):
        as_str_id(12.0)


def test_optional_str_id() -> None:
    assert optional_str_id(None) is None
    assert optional_str_id(UNSAFE_JS_ID) == UNSAFE_JS_ID_STR
    assert optional_str_id(I64_MAX_STR) == I64_MAX_STR


def test_entity_id_prefers_id_str() -> None:
    assert entity_id({"id": 1, "id_str": UNSAFE_JS_ID_STR}) == UNSAFE_JS_ID_STR
    assert entity_id({"id": UNSAFE_JS_ID}) == UNSAFE_JS_ID_STR
    assert entity_id(None) is None
    assert entity_id({"name": "no id"}) is None

    athlete = MetaAthlete(id=1, id_str=UNSAFE_JS_ID_STR)
    assert entity_id(athlete) == UNSAFE_JS_ID_STR

    activity = MetaActivity(id=UNSAFE_JS_ID, id_str=I64_MAX_STR)
    assert entity_id(activity) == I64_MAX_STR

    fallback = MetaActivity(id=UNSAFE_JS_ID)
    assert entity_id(fallback) == UNSAFE_JS_ID_STR


def test_models_accept_id_str_from_api_payload() -> None:
    athlete = MetaAthlete.model_validate({"id": I64_MAX, "id_str": I64_MAX_STR})
    assert athlete.id == I64_MAX
    assert athlete.id_str == I64_MAX_STR
    assert entity_id(athlete) == I64_MAX_STR


def test_format_activity_emits_string_id_in_json() -> None:
    formatted = ResponseBuilder.format_activity(
        {
            "id": UNSAFE_JS_ID,
            "id_str": UNSAFE_JS_ID_STR,
            "name": "Tempo",
            "type": "Run",
        }
    )
    assert formatted["id"] == UNSAFE_JS_ID_STR
    assert isinstance(formatted["id"], str)

    raw = ResponseBuilder.build_response({"activity": formatted})
    assert f'"{UNSAFE_JS_ID_STR}"' in raw
    # Must not appear as a JSON number, which JS would round.
    assert f":{UNSAFE_JS_ID}" not in raw
    payload = json.loads(raw)
    assert payload["data"]["activity"]["id"] == UNSAFE_JS_ID_STR


def test_python_json_loads_keeps_64bit_ids_exact() -> None:
    """Server-side parsing is already safe; this documents the Python guarantee."""
    payload = json.loads(f'{{"id": {I64_MAX_STR}, "id_str": "{I64_MAX_STR}"}}')
    assert payload["id"] == I64_MAX
    assert str(payload["id"]) == I64_MAX_STR
    activity = SummaryActivity.model_validate(
        {
            "id": payload["id"],
            "id_str": payload["id_str"],
            "name": "Long run",
            "distance": 1000,
            "moving_time": 300,
            "elapsed_time": 300,
            "total_elevation_gain": 0,
            "type": "Run",
            "start_date": "2026-11-17T06:00:00Z",
            "start_date_local": "2026-11-17T00:00:00Z",
            "timezone": "America/Chicago",
        }
    )
    assert activity.id == I64_MAX
    assert entity_id(activity) == I64_MAX_STR
