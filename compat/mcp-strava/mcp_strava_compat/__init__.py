"""`mcp-strava` -> strava-mcp-connector, stdio by default.

The legacy command name is kept so an MCP host registered as
`uv tool uvx mcp-strava` picks up the connector without re-registration.
The connector itself defaults to HTTP; a host spawning a bare command expects stdio.
"""

import os


def main() -> None:
    os.environ.setdefault("STRAVA_MCP_TRANSPORT", "stdio")
    from strava_mcp.cli import main as connector_main

    connector_main()
