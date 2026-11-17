# mcp-strava compat shim

Installs as the uv tool **`mcp-strava`** and exposes the `mcp-strava` / `strava-mcp`
commands, which start **strava-mcp-connector** (from `../../server`) in **stdio** mode.

Why: an MCP host that was registered against the old eddmann `mcp-strava` 1.0.0 runs
`uv tool uvx mcp-strava`. `uvx` reuses an installed tool with that name, so installing
this shim switches the host to the connector without touching its registration.

```
uv tool install --force --reinstall \
  --with /workspace/strava-mcp-connector/server \
  /workspace/strava-mcp-connector/compat/mcp-strava
```

Tokens: `~/.strava-mcp-connector.env` (`STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`,
`STRAVA_ACCESS_TOKEN`, `STRAVA_REFRESH_TOKEN`). A `.env` in the host's working
directory would take precedence; keep none there.

Upgrade: bump the connector, bump `version` + the `==` pin here, re-run the install.
Rollback: `uv tool install --force --editable <archived mcp-strava-1.0.0 dir>`.
