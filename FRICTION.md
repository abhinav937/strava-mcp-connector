# First-time connect friction — live-test postmortem

Connect **succeeded** but took too long. Below is the exact live-test friction
and what we changed so the next first-time connect is much faster.

## FRICTION (confirmed live test)

1. **Chromium login/captcha thrash = largest cost**
   - Wrong autofill chip (not the real Email field)
   - “Unexpected error” + invisible reCAPTCHA
   - Dismissed `request_box_help` and kept pixel-clicking
2. **Wrongly asked the user to open Strava on their laptop** (then corrected to bot) — wasted turns
3. **Didn’t prefill known email** (`abhinavchinnusamy@gmail.com`) / **didn’t pull OTP from Gmail MCP** — user typed OTP
4. **Ad-hoc OAuth register + PKCE + callback** instead of a one-command path
5. **computerUse to scrape Client Secret → `.env` was slow**

What worked once past login: API settings → Client ID **191703** (user’s own app) →
callback domain **`localhost`** → secret in **`.env`** → HTTP `:8000` → OAuth Approve →
smoke `get_athlete_profile` + `query_activities`.

## Product rules (unchanged)

- Per-user Strava API app (their Client ID/Secret)
- Fetch-only tools (no analysis)
- Premium prerequisite documented
- OAuth + redirect (not paste access tokens as primary)
- No secrets in git

## Improvements shipped

| Deliverable | Change |
| --- | --- |
| A | `plugin/skills/strava-setup/SKILL.md` **FAST PATH** — first line: ALL Strava UI on bot, never laptop links |
| B | Prefill known email; after email submit, Gmail MCP → newest Strava verify email → fill OTP (`submitAfterFill` + click fallback) |
| C | Snapshot before fill: assert main Email input; dismiss autofill chips; reCAPTCHA / unexpected error → SSO or `request_box_help` **immediately** (max 2 form retries) |
| D | If settings/api already has Client ID + `localhost`: **skip create**; one-step reveal secret → write `.env` (no chat paste) |
| E | `strava-mcp-connector smoke-oauth` (+ `server/scripts/smoke_oauth.py`): start HTTP if needed, register temp client, open Approve via `/oauth/strava/open`, capture callback, print **athlete_id only** |
| F | `server/scripts/dev_up.sh` — parallel server start during login |
| G | This `FRICTION.md` |

`open_on_bot_computer` / `/oauth/strava/open` kept as **secondary** to MCP Connect + `request_box_help`.

## What we deliberately stopped doing

- Pixel Chrome login loops (autofill thrash, invisible captcha, unexpected-error retries)
- Dismissing box-help to “just click more”
- Laptop Strava / OAuth link dumps as the primary path
- Making the user type email OTP when Gmail MCP is available
- Hand-rolled register+PKCE+callback instead of `smoke-oauth` / Cursor MCP Connect
- Slow computer-use secret scraping into chat — one-step reveal → `.env` only

## Known caveat (v1 ship)

**OAuth scope polish is still landing.** Some Connect / `smoke-oauth` paths may return `invalid_scope` even when Client ID/Secret and Premium are fine. That is a connector bug being fixed, **not** a bad install by the user.

If Connect fails with a scope error: retry MCP Connect once; if it still fails, say the connector hit a known scope-registration issue and point them at an issue/retry later — do **not** tell them their Premium, API app, or callback domain is wrong solely because of `invalid_scope`.
