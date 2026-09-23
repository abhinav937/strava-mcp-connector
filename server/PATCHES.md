# Connector adaptations vs eddmann/strava-mcp 1.0.0

1. **Fetch-only tools** — dropped `analyze_training`, `compare_activities`, `find_similar_activities` and analysis prompts.
2. **HTTP default** — `--transport` defaults to `http` (marketplace OAuth).
3. **FastMCP 4** — `await ctx.get_state(...)`; `OAuthProvider.get_routes(mcp_path)` (no `mcp_endpoint`).
4. **Lazy boto3** — DynamoDB session backend imports `boto3` only when selected; memory backend works without `[http]` extras.
5. **Env file** — defaults to `~/.strava-mcp-connector.env` (avoids clobbering local trainer MCP env).
6. **Per-user Strava API apps** — Client ID/Secret are user-supplied (plugin config / env); no shared publisher app. Agent skill `strava-setup` + subscription prerequisite docs.
