# Strava MCP Connector

Fetch-only [Model Context Protocol](https://modelcontextprotocol.io) server for Strava, packaged as a **Cursor marketplace plugin**.

**Each installer creates their own Strava API application** at https://www.strava.com/settings/api and supplies **their** Client ID + Client Secret. There is no shared publisher Strava app. After credentials are set, the agent (or Cursor Connect) runs normal **OAuth**: authorize → Approve → redirect/callback → token exchange. Tokens are stored server-side. No training analysis, plots, or coaching tools.

Upstream basis: [eddmann/strava-mcp](https://github.com/eddmann/strava-mcp) 1.0.0 (MIT), adapted with FastMCP 4-compatible async context state. Analysis tools removed — see [`SCOPE.md`](./SCOPE.md).

## Requirements (before install)

Strava’s 2026 developer policy: **a Strava subscription is a prerequisite** for building with the API ([Strava API FAQ](https://communityhub.strava.com/developers-knowledge-base-14/strava-api-faq-12906)). This connector uses **your** Standard Tier API app — subscription is a **hard requirement** for it to work for you.

| # | Requirement | Notes |
| --- | --- | --- |
| 1 | **Strava account** | Normal athlete login |
| 2 | **Strava subscription (Premium/Subscriber)** | Required for Standard Tier API access (2026). No extra API fee beyond subscription. |
| 3 | **Your own API application** | Create at [strava.com/settings/api](https://www.strava.com/settings/api) → Client ID + Client Secret. **No shared publisher app.** |
| 4 | **Authorization Callback Domain** | Local: `localhost`. Hosted: your MCP hostname. Redirect URI: `{STRAVA_MCP_BASE_URL}/oauth/strava/callback` |
| 5 | **OAuth scopes** | Defaults: `profile:read_all`, `activity:read_all`, `activity:read`, `profile:write` |
| 6 | **Runtime** | Cursor + this MCP process (local HTTP default `http://127.0.0.1:8000/mcp`, or self-hosted) |
| 7 | **Tool limits** | Subscription ≠ every gated field. Segment **explore** may need Extended Access; leaderboard/effort fields may degrade. See [`SCOPE.md`](./SCOPE.md). |
| 8 | **Rate limits** | Apply to **your** API app (not a shared publisher quota). |

**Official alternative:** Strava ships a [subscriber MCP](https://communityhub.strava.com/developers-knowledge-base-14/strava-api-faq-12906) for single-user conversational access without building an API app. This plugin is a **fetch-only alternative** that uses **your own** API application + OAuth.

When auth is missing, the agent skill **`strava-setup`** walks through these prerequisites first, then Client ID/Secret + OAuth + smoke test.


## Fast path (first-time connect)

See [`FRICTION.md`](./FRICTION.md) for the live-test postmortem. Agent skill **`strava-setup`** is a **FAST PATH** playbook:

1. Prefer Cursor MCP **Connect/OAuth** against `http://127.0.0.1:8000/mcp` (host opens Strava).
2. Or run `strava-mcp-connector smoke-oauth` (registers temp client, opens Approve on the **bot**, prints `athlete_id` only).
3. If a browser login wall appears: `/oauth/strava/open` then **immediately** `request_box_help` for password/captcha — do not thrash Chromium.
4. Parallel bring-up: `server/scripts/dev_up.sh` while login help is in progress.

**ALL Strava UI is on the bot computer — never laptop links as the primary path.**

`open_on_bot_computer` / `GET {BASE}/oauth/strava/open` remains available but is **secondary** to MCP Connect and box-help:

- `?settings=1` — API settings on the bot browser
- `?url=<authorize_url>` — Approve on the bot browser

## Architecture

```
┌─────────────┐     MCP (HTTP)      ┌──────────────────────────┐
│ Cursor IDE  │ ◄─────────────────► │ Strava MCP Connector     │
│  (plugin)   │   OAuth + tools     │  FastMCP streamable-http │
└─────────────┘                     │  session store (memory / │
       │                            │  DynamoDB)               │
       │ Connect                    └───────────┬──────────────┘
       ▼                                        │ Strava REST
┌─────────────┐                                 ▼
│   Strava    │ ◄────── OAuth authorize/token ──┘
│  OAuth UI   │         callback on connector
└─────────────┘
```

1. **User** creates a Strava API application (Client ID + Client Secret) and puts them in plugin config / `.env` / MCP env — see [Environment](#environment).
2. **User / agent** runs this connector locally (HTTP) with those credentials; Cursor points at `http://127.0.0.1:8000/mcp`.
3. Cursor (or the agent) starts OAuth; Strava redirects to `{STRAVA_MCP_BASE_URL}/oauth/strava/callback`.
4. Connector exchanges the code for tokens, stores them in the session backend, and issues an MCP access token to Cursor.
5. Tool calls use the athlete’s Strava token via middleware (`HttpClientMiddleware`).

The plugin skill **`strava-setup`** walks agents through this end-to-end when Strava is not connected yet.

Stdio + local tokens remain available for developers (`strava-mcp-connector auth`); marketplace UX is **HTTP + OAuth**, not “paste access/refresh tokens”.

## Repository layout

```
strava-mcp-connector/
├── server/                 # Python FastMCP package (runnable)
│   ├── pyproject.toml
│   ├── scripts/dev_up.sh   # one-command HTTP bring-up
│   ├── scripts/smoke_oauth.py
│   └── strava_mcp/
├── plugin/                 # Cursor marketplace plugin scaffold
│   ├── .cursor-plugin/plugin.json
│   ├── mcp.json
│   ├── skills/strava-setup/SKILL.md   # FAST PATH playbook
│   └── README.md
├── SCOPE.md                # Included vs excluded tools
├── FRICTION.md             # live-test postmortem + improvements
├── .env.example
└── README.md
```

## Tools

**Included:** `query_activities`, `get_activity_social`, `get_athlete_profile`, `query_routes`, `export_route`, `query_segments`, `get_segment_leaderboard`, `star_segment`.

**Excluded:** `analyze_training`, `compare_activities`, `find_similar_activities`.

Full table: [`SCOPE.md`](./SCOPE.md).

## Activity and athlete IDs

After June 1, 2027, Strava may return 64-bit Activity and Athlete IDs. The API also includes `id_str`, and this connector uses that (falling back to a string form of `id`) so JavaScript clients do not lose precision.

Tool outputs expose these IDs as strings. Tool inputs such as `query_activities(activity_id=...)` accept the string form and still accept numeric IDs for backward compatibility. See [`CHANGELOG.md`](./CHANGELOG.md) for 0.2.1.

## Environment

Copy [`.env.example`](./.env.example) to `server/.env` (or `~/.strava-mcp-connector.env`). **You** supply Client ID + Secret from your Strava API app. Never commit secrets.

| Variable | Required | Purpose |
| --- | --- | --- |
| `STRAVA_CLIENT_ID` | yes | **Your** Strava API application client ID |
| `STRAVA_CLIENT_SECRET` | yes | **Your** Strava API application secret |
| `STRAVA_MCP_BASE_URL` | yes (HTTP) | Public URL of this server (OAuth callback base) |
| `STRAVA_MCP_HOST` / `STRAVA_MCP_PORT` | no | Bind address (default `127.0.0.1:8000`) |
| `STRAVA_MCP_PATH` | no | MCP path (default `/mcp`) |
| `STRAVA_SESSION_BACKEND` | no | `memory` (default) or `dynamodb` |
| `STRAVA_OAUTH_SCOPES` | no | Comma-separated Strava scopes |

**Cursor plugin config:** the marketplace plugin declares `STRAVA_CLIENT_ID` and `STRAVA_CLIENT_SECRET` as [plugin variables](https://cursor.com/docs/reference/plugins) (Plugins → Configure). For local HTTP, the agent/`strava-setup` skill also writes them into a gitignored `.env` so the server process can read them.

**Strava app redirect URI** (Authorization Callback Domain + callback path):

```text
{STRAVA_MCP_BASE_URL}/oauth/strava/callback
```

Local example: `http://localhost:8000/oauth/strava/callback`  
Authorization Callback Domain: `localhost` (local) or your hosted hostname.

## Run locally (HTTP + OAuth)

```bash
cd /workspace/strava-mcp-connector/server
cp ../.env.example .env
# edit .env — set YOUR STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET, STRAVA_MCP_BASE_URL

# Python 3.11+ with uv (recommended) or pip
uv venv && source .venv/bin/activate
uv pip install -e .

# One-command bring-up (loads .env, starts HTTP, prints URLs)
./scripts/dev_up.sh
# → MCP:              http://127.0.0.1:8000/mcp
# → OAuth callback:   http://localhost:8000/oauth/strava/callback
# → Open settings:    http://localhost:8000/oauth/strava/open?settings=1

# Optional one-command OAuth smoke (Approve on bot; prints athlete_id only)
strava-mcp-connector smoke-oauth
```

Point Cursor MCP Connect at `http://127.0.0.1:8000/mcp` (preferred) or use `smoke-oauth`.

### Stdio (debug only)

```bash
# Prefer: strava-mcp-connector auth  (OAuth wizard → writes tokens to env)
# Then:
strava-mcp-connector --transport stdio
```

Do not treat pasting access/refresh tokens as the primary install path.

## Cursor plugin

See [`plugin/`](./plugin/) for the marketplace scaffold:

- `.cursor-plugin/plugin.json` — name, description, keywords, **user variables** for Client ID/Secret, `mcpServers` pin
- `mcp.json` — local HTTP URL (`http://127.0.0.1:8000/mcp`)
- `skills/strava-setup/` — agent walkthrough when auth is missing

**Install story:** install plugin → agent runs **strava-setup** (your Strava API app + OAuth) → use fetch-only tools.

## Known limitations (v1)

- **OAuth scope polish still landing** — occasional `invalid_scope` on Connect / smoke-oauth is a known connector issue, not necessarily a bad Client ID, callback domain, or missing Premium.
- Segment **explore** / some leaderboard fields may need Extended Access beyond Standard Tier.
- Login on bot Chrome: use email + Gmail OTP ([strava email OTP](sand-workflow:strava-email-otp-login-2)); avoid SSO unless asked.

## Next steps (before marketplace publish)

1. **Each user creates a Strava API app** — https://www.strava.com/settings/api; callback `{BASE}/oauth/strava/callback`.
2. **Document / test `strava-setup`** — agent guides Client ID/Secret → local HTTP → OAuth → smoke test.
3. **Optional self-host** — Deploy `server/` on Fly.io, Railway, Render, or AWS Lambda (`lambda_handler.py` + Mangum) **with that user’s own** client credentials (still not a shared publisher app). Prefer `STRAVA_SESSION_BACKEND=dynamodb` for multi-instance.
4. **Cursor packaging** — Confirm `plugin/.cursor-plugin/plugin.json` fields; logo; public Git repo; submit at https://cursor.com/marketplace/publish.
5. **Live OAuth test** — Requires the installer’s real Strava app credentials.

## Attribution

Portions © Edd Mann (eddmann/strava-mcp). Fetch-only Cursor packaging © Abhinav Chinnusamy / Austin Half Trainer contributors. MIT — see [`LICENSE`](./LICENSE).

## Running under the legacy `mcp-strava` command

Hosts registered as `uv tool uvx mcp-strava` can be switched without re-registration by installing
the `compat/mcp-strava` shim (stdio by default). See [SWITCH.md](SWITCH.md).
