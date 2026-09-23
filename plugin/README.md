# Strava MCP (Cursor plugin)

Connect Strava to Cursor with **your own** Strava API application and OAuth.
Fetch-only tools (activities, routes, segments, athlete profile) — no training analysis.

**Requires a Strava subscription (Premium/Subscriber)** for Standard Tier API access
([Strava API FAQ, 2026](https://communityhub.strava.com/developers-knowledge-base-14/strava-api-faq-12906)).
Strava also offers an official subscriber MCP; this plugin is a fetch-only alternative
that uses **your** API app (no shared publisher credentials).

## Requirements checklist

1. Strava account  
2. **Strava subscription (Premium/Subscriber)** — hard requirement for API access  
3. Your own API app at https://www.strava.com/settings/api (Client ID + Client Secret)  
4. Authorization Callback Domain (`localhost` or your hosted host)  
5. OAuth scopes: `profile:read_all`, `activity:read_all`, `activity:read`, `profile:write`  
6. Cursor + local (or hosted) MCP HTTP process for this connector  
7. Tool limits: segment explore / some leaderboard fields may need Extended Access or stay gated — Premium does not unlock everything  
8. Rate limits are per **your** app  

## Install (marketplace)

1. Install from the Cursor Marketplace.
2. Ask the agent to set up Strava (skill: **`strava-setup`**). It will:
   - Confirm subscription / prerequisites **before** API app creation
   - Walk you through creating an API app at https://www.strava.com/settings/api
   - Collect **your** Client ID + Client Secret (plugin Configure / env — never echoed)
   - Start local HTTP OAuth and complete authorize → redirect → token exchange
   - Smoke-test `get_athlete_profile` and a recent activity query
3. Use tools such as `query_activities` and `get_athlete_profile`.

## Configure credentials

Prefer one of:

| Method | How |
| --- | --- |
| Plugin variables | Cursor → Plugins → Configure → `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET` |
| Env file | `server/.env` or `~/.strava-mcp-connector.env` (see repo `.env.example`) |
| MCP env | Cursor MCP server `env` (do not commit secrets) |

Then run the connector HTTP server (agent/`strava-setup` will help) and keep
`mcp.json` pointed at `http://127.0.0.1:8000/mcp`.

## Local development

1. Confirm Strava subscription; create your API app; set Authorization Callback Domain to `localhost`.
2. Copy `.env.example` → `server/.env` with your Client ID/Secret and
   `STRAVA_MCP_BASE_URL=http://localhost:8000`.
3. From `../server` run `./scripts/dev_up.sh` (or `strava-mcp-connector --transport http`).
4. Prefer Cursor MCP Connect to `http://127.0.0.1:8000/mcp`, or `strava-mcp-connector smoke-oauth`.
   All Strava UI is on the bot computer — never laptop links. See repo `FRICTION.md`.

## Packaging checklist

- [ ] Confirm `mcp.json` URL for local default (`http://127.0.0.1:8000/mcp`) or your docs
- [ ] Plugin `variables` declare Client ID / Secret (no real values in the repo)
- [ ] `skills/strava-setup/SKILL.md` present (prerequisites + Premium called out first)
- [ ] Add a real `assets/logo.svg` (Strava brand guidelines apply to any Strava marks)
- [ ] Fill `author.email` / `homepage` / `repository` in `.cursor-plugin/plugin.json` if desired
- [ ] Public Git repo + submit at https://cursor.com/marketplace/publish

This plugin does **not** ship Strava secrets. Every user supplies their own.
