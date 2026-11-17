"""Helpers for Strava activity and athlete IDs.

After June 1, 2027, Strava may return 64-bit Activity and Athlete IDs. The API
also includes `id_str` (the same value as a string) and recommends using it.

This package is Python, so `json.loads` and `int` keep 64-bit values exact.
Tool responses are still JSON consumed by JavaScript MCP hosts, where `Number`
is only safe up to 2^53 - 1. Always expose these IDs as strings in tool output,
prefer `id_str`, and accept string (or legacy numeric) IDs on the way back in
without `int()`/`float()` coercion of the string form.
"""

from __future__ import annotations

from typing import Any, TypeAlias

EntityId: TypeAlias = str | int


def as_str_id(value: object) -> str:
    """Return an entity ID as a decimal string without numeric coercion.

    Accepts `str` or `int` so existing numeric tool inputs stay valid. String
    values are stripped only; they are not passed through `int()` or `float()`.
    Integers are stringified with Python's arbitrary-precision `str()`.
    """
    if isinstance(value, bool) or value is None:
        raise ValueError(f"Invalid ID: {value!r}")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("ID must be a non-empty string")
        return text
    raise ValueError(f"ID must be a string or int, got {type(value).__name__}")


def optional_str_id(value: object | None) -> str | None:
    """Like `as_str_id`, but `None` stays `None`."""
    if value is None:
        return None
    return as_str_id(value)


def entity_id(obj: object | None) -> str | None:
    """Read an activity or athlete ID, preferring `id_str` over `id`.

    Accepts a model, a dict, or a raw str/int ID. Returns `None` when neither
    field is present.
    """
    if obj is None:
        return None
    if isinstance(obj, (str, int)) and not isinstance(obj, bool):
        try:
            return as_str_id(obj)
        except ValueError:
            return None

    id_str: Any
    ident: Any
    if isinstance(obj, dict):
        id_str = obj.get("id_str")
        ident = obj.get("id")
    else:
        id_str = getattr(obj, "id_str", None)
        ident = getattr(obj, "id", None)

    if id_str is not None and id_str != "":
        try:
            return as_str_id(id_str)
        except ValueError:
            return None
    if ident is None:
        return None
    try:
        return as_str_id(ident)
    except ValueError:
        return None
