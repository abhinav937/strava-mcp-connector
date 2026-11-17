# Box switch: `strava-local` → strava-mcp-connector (2026-11-17)

The box MCP `user-strava-local` is registered (hidden host config, not edited) as:

```
uv tool uvx mcp-strava
```

It used to run eddmann `mcp-strava` 1.0.0 (patched, editable from
`/workspace/austin-half-trainer-tooling/mcp-strava`). It now runs this connector.

## What was done

1. `compat/mcp-strava/` — a tiny package **named `mcp-strava`** (version 0.2.1) that depends on
   `strava-mcp-connector==0.2.1` and exposes `mcp-strava` / `strava-mcp` →
   `mcp_strava_compat:main`, which sets `STRAVA_MCP_TRANSPORT=stdio` (the connector defaults to
   HTTP) and calls `strava_mcp.cli:main`.
2. Installed over the old uv tool (uvx reuses an installed tool of the same name):
   ```
   uv tool install --force --reinstall --with ./server ./compat/mcp-strava
   ```
3. Tokens copied (not printed) from `~/.strava-mcp.env` into `~/.strava-mcp-connector.env`
   (mode 600). `~/.strava-mcp.env` is now a **symlink** to it so older scripts still read live
   tokens; the pre-switch file is kept at `~/.strava-mcp.env.pre-switch-20261117`.
   The host's cwd is `/workspace` and has no `.env`, so the connector reads/refreshes
   `~/.strava-mcp-connector.env`.
4. Killed the running `uv tool uvx mcp-strava` processes; the host respawned on next call.
5. Old package archived at `/workspace/_archive/mcp-strava-1.0.0-20261117` (not deleted).

## Verified (2026-11-17 23:52 IST)

- stdio `tools/list`: `export_route, get_activity_social, get_athlete_profile,
  get_segment_leaderboard, query_activities, query_routes, query_segments, star_segment`
  (no `analyze_training` / `compare_activities` / `find_similar_activities`).
- Live via the host: `get_athlete_profile` OK (id returned as a string), `query_activities`
  `time_range=7d` OK, `query_activities activity_id="20990444031"` OK. Calling
  `analyze_training` → tool not found.

Training analysis moved to `bin/analyze-training` in the private
`abhinav937/austin-half-trainer-tooling` repo.

## Upgrade / rollback

- Upgrade: bump `server/pyproject.toml`, bump `compat/mcp-strava` version + `==` pin, re-run step 2,
  then `pkill -f 'uvx mcp-strava'`.
- Rollback: `uv tool install --force --editable /workspace/_archive/mcp-strava-1.0.0-20261117`,
  then `pkill -f 'uvx mcp-strava'`.
