# Strava MCP Connector — ship checklist

**Release:** `0.2.0` (plugin, server package metadata aligned)  
**Prepared:** 2026-09-23 00:15 CDT  
**Submission status:** **Ready to submit** — public repo: https://github.com/abhinav937/strava-mcp-connector (pushed `0.2.0` / `11d3e93`).

## Validation

- [x] Cursor manifest: `plugin/.cursor-plugin/plugin.json` parses and has name, semver version `0.2.0`, description, author, MIT license, keywords, logo, MCP reference, and required Client ID/Secret variable schema.
- [x] Root multi-plugin manifest added at `.cursor-plugin/marketplace.json` because this checkout keeps the plugin under `plugin/`. It points to `plugin` and declares `strava-mcp` version `0.2.0`.
- [x] Logo present: `plugin/assets/logo.svg`.
- [x] MCP URL is `http://127.0.0.1:8000/mcp` in `plugin/mcp.json`.
- [x] `plugin/skills/strava-setup/SKILL.md` present, including the Premium prerequisite, bot-Chrome email/OTP path, MCP Connect preference, and secret-handling rules.
- [x] Root `LICENSE` present (MIT).
- [x] `.gitignore` excludes `.env`, `.env.*` (while allowing `.env.example`), private keys, caches, and local exports.
- [x] Server tests: `pytest -q` → **2 passed**.
- [x] Version kept at `0.2.0`; server `pyproject.toml` and `strava_mcp.__version__` were aligned to `0.2.0` (no release bump).

## Included tools

The connector registers eight Strava tools and no training-analysis tools:

- `query_activities`
- `get_activity_social`
- `get_athlete_profile`
- `query_routes`
- `query_segments`
- `get_segment_leaderboard`
- `export_route` (GPX/TCX export)
- `star_segment` (star/unstar)

The first six are fetch/read-oriented. `export_route` and `star_segment` are deliberately bounded export/mutate operations; the connector excludes `analyze_training`, `compare_activities`, and `find_similar_activities`.

## Requirements

1. Strava account with a **Premium/Subscriber subscription** (Standard Tier API prerequisite under the documented 2026 policy).
2. The installer's **own Strava API application** at <https://www.strava.com/settings/api>; there is no shared publisher app.
3. Client ID and Client Secret supplied through Cursor plugin variables or a gitignored env file.
4. Authorization Callback Domain `localhost` for local use (or the hosted hostname); callback `{STRAVA_MCP_BASE_URL}/oauth/strava/callback`.
5. Cursor and this connector's local or self-hosted HTTP process.
6. Default OAuth scopes: `profile:read_all`, `activity:read_all`, `activity:read`, `profile:write`.

## Known caveats

- `smoke-oauth` can report `invalid_scope` on some paths. Do not block packaging on that polish.
- Cursor MCP Connect/OAuth worked in the prior live test with the user's own app; the tested path reached `get_athlete_profile` and `query_activities`.
- Strava login can be slow when Chromium hits CAPTCHA or an unexpected-error loop. The `strava-setup` skill timeboxes pixel interaction and hands off to box help.
- If bot-browser login is needed, use the bot-Chrome email OTP skill: keep the same page after requesting the code, retrieve the newest code through Gmail MCP when available, and do not use SSO unless requested.
- Premium/Subscriber access does not guarantee Extended Access. Segment explore and some leaderboard/effort fields may be gated or partial.
- Rate limits apply to each installer's API app.
- The plugin's default MCP URL is local HTTP; hosted deployments need their own base URL, callback domain, and session backend configuration.

## Secrets check

There is currently **no Git repository or commit history in this checkout**, so there are no committed files to certify. A source-tree scan found no embedded credential values in the distributable files; only placeholders, test fixtures, and code variable names were present. A local `server/.env` containing user-supplied runtime configuration exists and is ignored; it must not be committed or included in any upload. The sanitized release zip excludes it.

## Public repository / GitHub status

- Public git remote: **https://github.com/abhinav937/strava-mcp-connector** (public, `main` @ `11d3e93`).
- Owner: `abhinav937`.
- Secrets: `server/.env` not committed; only `.env.example` shipped.

## Exact Cursor publish steps

1. Before publishing, inspect the release tree and ensure `server/.env`, tokens, client secrets, private keys, caches, and local exports are absent. Keep `.env.example`.
2. Create or choose a **public, open-source Git repository** and push the sanitized tree. Use the repository root URL; `.cursor-plugin/marketplace.json` maps the nested `plugin/` directory to the `strava-mcp` plugin.
3. Verify from the public repository view that `.cursor-plugin/marketplace.json`, `plugin/.cursor-plugin/plugin.json`, `plugin/mcp.json`, `plugin/assets/logo.svg`, `plugin/skills/strava-setup/SKILL.md`, `README.md`, `SCOPE.md`, and `LICENSE` are reachable.
4. Sign in to Cursor and open <https://cursor.com/marketplace/publish>.
5. Submit the public repository URL in the publish form. Cursor validates the manifest and performs manual review; do not submit a local path or the zip as the repository URL.
6. Address any review feedback, push updates to the same public repository, and resubmit/review the updated version as requested by Cursor.

## Local artifact

A sanitized upload artifact is prepared at `/workspace/strava-mcp-connector-0.2.0.zip`. It is a convenience/archive only; Cursor marketplace submission requires the public Git repository URL.
