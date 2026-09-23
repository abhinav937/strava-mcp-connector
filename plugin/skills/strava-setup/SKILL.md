---
name: strava-setup
description: >-
  FAST PATH Strava MCP first-time connect. ALL Strava UI on the bot computer —
  never laptop links. Prefer Cursor MCP Connect; cap Chromium computer-use;
  email+OTP on bot Chrome (no SSO unless asked); Gmail MCP for code; request_box_help for captcha; smoke-oauth CLI.
---

**ALL Strava UI (login, API settings, OAuth Approve) opens on the BOT computer — never ask the user to open Strava / OAuth links on their laptop.**

# Strava setup — FAST PATH

**Goal:** first-time connect in minutes. Chromium pixel-driving is the last resort, not the default.

## Product rules (keep)

- Per-user Strava API app (their Client ID/Secret) — no shared publisher app
- Fetch-only tools (no analysis)
- **Premium / Subscriber** prerequisite ([API FAQ](https://communityhub.strava.com/developers-knowledge-base-14/strava-api-faq-12906))
- OAuth + redirect (not paste access tokens as primary)
- Never echo Client Secret or tokens; write secrets only to gitignored `.env`

---

## Auth UI priority (strict order)

| # | Method | Use when |
| --- | --- | --- |
| **1** | Cursor MCP **Connect / OAuth** → `http://127.0.0.1:8000/mcp` | Preferred. Host opens Strava — avoid pixel Chrome for the whole login. |
| **2** | `GET {BASE}/oauth/strava/open?…` then **immediately** `request_box_help` | Browser needed for login / password / captcha / Approve leftovers. |
| **3** | Bot Chromium / computer-use | **Max 2 failed** Strava page interactions (or **max 2 form retries**) → handoff. |

`open_on_bot_computer` / `/oauth/strava/open` remains available but is **secondary** to MCP Connect and to `request_box_help` for credentials/captcha.

**Parallelize:** start HTTP with `./scripts/dev_up.sh` while the user does box-help login.

---

## Timeboxed checklist (do not burn 20+ min on Chrome login)

| Phase | Budget | Action |
| --- | --- | --- |
| 0 | ~30s | `get_athlete_profile` — stop if already connected |
| 1 | ~1 min | Confirm Premium |
| 2 | ~1–2 min | `./scripts/dev_up.sh` (parallel with any login help) |
| 3 | ~3–5 min | API settings on bot; skip create if Client ID + `localhost` already set; secret → `.env` only |
| 4 | ~2–5 min | MCP Connect **or** `strava-mcp-connector smoke-oauth` |
| 5 | ~1 min | Smoke `get_athlete_profile` + `query_activities` |

If Chromium login still stuck after ~5 min or 2 failed interactions → **stop clicking** → `request_box_help`.

---

## Login form rules (bot browser only)

**Canonical recipe:** run [Strava email OTP login](sand-workflow:strava-email-otp-login-2) on **bot Chrome only**.

Default email when known: **`abhinavchinnusamy@gmail.com`**. Prefill — do not re-ask.

### Hard rules (from that skill — do not skip)

1. **No reload / no fresh `/login` tab** after email or OTP submit (wipes the OTP modal).
2. **No Google/Apple SSO** unless the user asks (SSO often fails as “browser not secure”).
3. Dismiss cookie banner first (black banner → white **OK**) if it covers Log In.
4. After email Log In, wait on the **same page** for **“We sent you a code”**.
5. After typing OTP, click orange **Next** once (wait until enabled). Do not use navigation shortcuts.
6. Success = `/dashboard` or signed-in feed. OTP rejected → **fresh** Log In cycle for a new code (never reuse).

### Automation notes

1. Snapshot; assert main **Email** field (dismiss autofill chips).
2. Click orange **Log In** once. **Max 2** automated attempts → then `request_box_help` for captcha / unexpected errors.
3. When OTP modal appears: **stop navigating**. Gmail MCP → newest Strava one-time code for the email. Never ask the user to paste the code when Gmail works. Never store/log the code.
4. Click the 6-digit field, type code, click orange **Next** once.
5. Confirm dashboard URL/title.

### Always hand off (bot desktop via `request_box_help`)

- Password
- reCAPTCHA / unexpected-error loops after 2 tries
- Passkeys / authenticator-app 2FA (non-email)

Do **not** dismiss `request_box_help` and keep clicking Chromium.


---

## FAST PATH steps

### Step 0 — Already connected? (~30s)

1. Call `get_athlete_profile`.
2. Success → done (optional `query_activities`).
3. Else continue.

### Step 1 — Prerequisites (~1 min)

Confirm before API work:

1. Strava account (UI on **bot**, never laptop links)
2. **Strava subscription (Premium)** — hard stop if not
3. Own API app (Client ID + Secret)
4. Authorization Callback Domain `localhost` (local) → redirect `{STRAVA_MCP_BASE_URL}/oauth/strava/callback`
5. Official subscriber MCP is an alternative; this plugin is fetch-only + own app

### Step 2 — Parallel: env + HTTP (~1–2 min)

```bash
cd /workspace/strava-mcp-connector/server
# first time: cp ../.env.example .env  # then set secrets (never commit)
./scripts/dev_up.sh
```

Prints MCP URL `http://127.0.0.1:8000/mcp`, settings open URL, callback domain reminder.
Point Cursor MCP at that URL. Refresh if needed.

### Step 3 — API app on bot (smart skip) (~3–5 min)

1. Open settings: `GET {BASE}/oauth/strava/open?settings=1` → login wall? **immediate** box-help (after email/OTP rules above).
2. **If settings/api already shows Client ID + Authorization Callback Domain `localhost`:** **skip create**. One-step **reveal Client Secret** on that page → write straight into gitignored `server/.env` (and/or plugin Configure). **No chat paste** of the secret. Do **not** slow computer-use scrape loops for the secret.
3. Else create app; set callback domain `localhost`; then same one-step secret → `.env`.
4. Live-test reference: Client ID **191703** path worked; callback `localhost`; HTTP `:8000`.

### Step 4 — OAuth Approve (~2–5 min)

**Preferred A — Cursor MCP Connect** against `http://127.0.0.1:8000/mcp` (host opens Strava).

**Preferred B — one-command smoke:**

```bash
cd /workspace/strava-mcp-connector/server
strava-mcp-connector smoke-oauth
# or: python scripts/smoke_oauth.py
```

This starts HTTP if needed, registers a temp MCP client (PKCE), opens Approve via `/oauth/strava/open` on the **bot**, captures callback, prints **`athlete_id` only** (no tokens on stdout).

**If browser leftovers:** `/oauth/strava/open?url=…` → immediate `request_box_help` for Approve.
Never: “open this on your laptop.”

### Step 5 — Tool smoke (~1 min)

1. `get_athlete_profile`
2. `query_activities` (e.g. last 30d)
3. Report athlete; fetch-only only.

---

## What we deliberately stop doing

- Long Chromium / computer-use login loops (wrong autofill chip, unexpected error + invisible reCAPTCHA)
- Dismissing `request_box_help` to keep thrashing Chrome
- Asking the user to open Strava on their **laptop**
- Re-asking email / making the user type OTP when Gmail MCP can pull it
- Ad-hoc register+PKCE+callback by hand instead of `smoke-oauth` / MCP Connect
- Slow computer-use scraping of Client Secret into chat — write `.env` in one step instead

---

## Failures (fast fixes)

| Symptom | Fix |
| --- | --- |
| Laptop link suggested | Correct to bot / MCP Connect / `/oauth/strava/open` + box-help |
| Wrong autofill / captcha / unexpected error | SSO or `request_box_help` immediately (≤2 form retries) |
| OTP | Gmail MCP → fill + submitAfterFill / click fallback |
| Secret scrape slow | Reveal once on settings → write `.env` only |
| Redirect mismatch | Domain `localhost` + `{BASE}/oauth/strava/callback` |
| Tools missing | `dev_up.sh` + Cursor → `http://127.0.0.1:8000/mcp` |
| Ad-hoc OAuth pain | `strava-mcp-connector smoke-oauth` |

---

## Done checklist

- [ ] Premium confirmed
- [ ] ALL Strava UI on bot (no laptop links)
- [ ] HTTP via `dev_up.sh`; Cursor → `http://127.0.0.1:8000/mcp`
- [ ] API app ready (skipped create if ID + localhost present); secret in `.env` only
- [ ] OAuth via MCP Connect or `smoke-oauth`; Approve on bot
- [ ] Computer-use capped; password/captcha via box-help
- [ ] Email prefilled; OTP from Gmail when connected
- [ ] `get_athlete_profile` + `query_activities` passed

## Known caveat (v1 ship)

**OAuth scope polish is still landing.** Some Connect / `smoke-oauth` paths may return `invalid_scope` even when Client ID/Secret and Premium are fine. That is a connector bug being fixed, **not** a bad install by the user.

If Connect fails with a scope error: retry MCP Connect once; if it still fails, say the connector hit a known scope-registration issue and point them at an issue/retry later — do **not** tell them their Premium, API app, or callback domain is wrong solely because of `invalid_scope`.
