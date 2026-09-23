"""Smoke tests: fetch tools registered; analysis tools absent."""

from __future__ import annotations

import asyncio

import pytest

REQUIRED = {
    "STRAVA_CLIENT_ID": "test-client-id",
    "STRAVA_CLIENT_SECRET": "test-client-secret",
    "STRAVA_ACCESS_TOKEN": "test-access-token",
    "STRAVA_REFRESH_TOKEN": "test-refresh-token",
}


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    for k, v in REQUIRED.items():
        monkeypatch.setenv(k, v)


def _tool_names(mcp) -> set[str]:
    tools = getattr(mcp, "_tool_manager", None)
    if tools is not None and hasattr(tools, "_tools"):
        return set(tools._tools.keys())

    async def _names() -> set[str]:
        listed = await mcp.list_tools()
        return {t.name for t in listed}

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.run(_names())  # may fail; use new loop
    except RuntimeError:
        pass
    return asyncio.run(_names())


def test_fetch_tools_registered_analysis_absent() -> None:
    from strava_mcp.server import create_server

    mcp = create_server("stdio")
    names = _tool_names(mcp)

    expected = {
        "query_activities",
        "get_activity_social",
        "get_athlete_profile",
        "query_routes",
        "export_route",
        "query_segments",
        "get_segment_leaderboard",
        "star_segment",
    }
    excluded = {
        "analyze_training",
        "compare_activities",
        "find_similar_activities",
    }

    assert expected <= names, f"missing tools: {expected - names}"
    assert names.isdisjoint(excluded), f"analysis tools leaked: {names & excluded}"
    assert len(names) == 8


def test_analysis_module_absent() -> None:
    import importlib.util

    spec = importlib.util.find_spec("strava_mcp.tools.analysis")
    assert spec is None
