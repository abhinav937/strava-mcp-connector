"""Strava MCP Connector — fetch-only HTTP MCP; per-user Strava API app + OAuth."""

from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv
from fastmcp import Context, FastMCP

from .env import DEFAULT_ENV_FILE, LOCAL_ENV_FILE

load_dotenv(DEFAULT_ENV_FILE)
load_dotenv(LOCAL_ENV_FILE, override=True)


def create_server(transport_mode: str = "http") -> FastMCP:
    """Create and configure FastMCP server for the specified transport mode.

    Args:
        transport_mode: Either "http" (default, OAuth with user client id/secret) or "stdio"

    Returns:
        Configured FastMCP instance with fetch-only tools registered.
    """
    transport_mode = transport_mode.lower()

    if transport_mode == "http":
        from .http_auth import StravaOAuthProvider
        from .http_middleware import HttpClientMiddleware
        from .http_session import (
            StravaAppConfig,
            StravaOAuthService,
            create_session_store_from_env,
            parse_registered_clients,
        )

        app_config = StravaAppConfig()
        session_store = create_session_store_from_env()

        host = os.getenv("STRAVA_MCP_HOST", "127.0.0.1")
        port = int(os.getenv("STRAVA_MCP_PORT", "8000"))
        http_path = os.getenv("STRAVA_MCP_PATH", "/mcp")
        if not http_path.startswith("/"):
            http_path = f"/{http_path}"

        base_url = os.getenv("STRAVA_MCP_BASE_URL")
        if not base_url:
            host_for_url = "localhost" if host in {"0.0.0.0", "127.0.0.1"} else host
            base_url = f"http://{host_for_url}:{port}"

        oauth_service = StravaOAuthService(app_config, session_store, base_url=base_url)
        registered_clients = parse_registered_clients(app_config)

        auth_provider = StravaOAuthProvider(
            base_url=base_url,
            session_store=session_store,
            oauth_service=oauth_service,
            registered_clients=registered_clients,
        )

        mcp = FastMCP("Strava", auth=auth_provider)
        mcp.add_middleware(HttpClientMiddleware(app_config, session_store, oauth_service))
    else:
        from .stdio_auth import StdioStravaAuthContext
        from .stdio_middleware import StdioClientMiddleware

        config = StdioStravaAuthContext()
        mcp = FastMCP("Strava")
        mcp.add_middleware(StdioClientMiddleware(config))

    # Fetch / mutate tools only — no training analysis (see SCOPE.md)
    from .tools.activities import get_activity_social, query_activities
    from .tools.athlete import get_athlete_profile
    from .tools.routes import export_route, query_routes
    from .tools.segments import get_segment_leaderboard, query_segments, star_segment

    mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(query_activities)
    mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(get_activity_social)
    mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(get_athlete_profile)
    mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(query_segments)
    mcp.tool(
        annotations={
            "readOnlyHint": False,
            "openWorldHint": False,
            "destructiveHint": False,
        }
    )(star_segment)
    mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(get_segment_leaderboard)
    mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": False})(query_routes)
    mcp.tool(annotations={"readOnlyHint": False, "openWorldHint": False})(export_route)

    @mcp.resource(
        "strava://athlete/profile",
        annotations={"readOnlyHint": True},
    )
    async def athlete_profile_resource(ctx: Context) -> str:  # type: ignore[reportUnusedFunction]
        """Complete athlete profile with stats, zones, and gear for context."""
        from .client import StravaAPIError
        from .response_builder import ResponseBuilder

        client = await ctx.get_state("client")

        try:
            athlete = await client.get_athlete()
            if athlete.id is None:
                return ResponseBuilder.build_error_response(
                    "Athlete ID not available",
                    error_type="invalid_data",
                )

            stats = await client.get_athlete_stats(athlete.id)
            zones = await client.get_athlete_zones()

            data = {
                "profile": {
                    "id": athlete.id,
                    "name": f"{athlete.firstname} {athlete.lastname}",
                    "location": {
                        "city": athlete.city,
                        "state": athlete.state,
                        "country": athlete.country,
                    },
                },
                "zones": ResponseBuilder.format_zones(zones.model_dump()),
                "statistics": {
                    "recent": {
                        "run": {
                            "count": stats.recent_run_totals.count,
                            "distance_km": round(stats.recent_run_totals.distance / 1000, 1),
                        },
                        "ride": {
                            "count": stats.recent_ride_totals.count,
                            "distance_km": round(stats.recent_ride_totals.distance / 1000, 1),
                        },
                    }
                },
            }

            return ResponseBuilder.build_response(data, metadata={"type": "athlete_profile"})
        except StravaAPIError as e:
            return ResponseBuilder.build_error_response(e.message, error_type="api_error")

    @mcp.prompt()
    async def segment_performance(segment_id: int) -> str:  # type: ignore[reportUnusedFunction]
        """Look up a Strava segment and my efforts / leaderboard.

        Args:
            segment_id: The ID of the segment to inspect
        """
        return f"""Inspect Strava segment {segment_id}.

1. Use query_segments with segment_id={segment_id} and include_efforts=true
2. Use get_segment_leaderboard for ranking context
3. Summarize distance, elevation, my efforts, and leaderboard position"""

    @mcp.prompt()
    async def activity_overview(activity_id: int) -> str:  # type: ignore[reportUnusedFunction]
        """Fetch a single activity with optional laps/zones/streams.

        Args:
            activity_id: The ID of the activity to fetch
        """
        return f"""Fetch Strava activity {activity_id}.

Use query_activities with activity_id={activity_id}, include_laps=true,
include_zones=true. Optionally include streams if detailed series data is needed.
Present the raw metrics clearly (distance, time, pace/speed, HR, elevation)."""

    @mcp.prompt()
    async def recent_activities(period: str = "30d") -> str:  # type: ignore[reportUnusedFunction]
        """List recent activities from Strava.

        Args:
            period: Time range (e.g. "7d", "30d", "90d", "ytd")
        """
        return f"""List my Strava activities for the past {period}.

Use query_activities with time_range="{period}". Summarize count, types,
and key totals without inventing coaching advice beyond the returned data."""

    return mcp


def main() -> None:
    """Main entry point for the Strava MCP connector."""
    parser = argparse.ArgumentParser(description="Strava MCP Connector (fetch-only)")
    parser.add_argument(
        "--transport",
        type=str,
        choices=["stdio", "http"],
        default=os.getenv("STRAVA_MCP_TRANSPORT", "http"),
        help="Transport mode: http (default, user-app OAuth) or stdio",
    )
    args = parser.parse_args()

    mcp = create_server(args.transport)

    if args.transport == "http":
        host = os.getenv("STRAVA_MCP_HOST", "127.0.0.1")
        port = int(os.getenv("STRAVA_MCP_PORT", "8000"))
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
