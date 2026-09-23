"""One-command OAuth smoke test for local HTTP MCP.

Starts HTTP if needed, registers a temporary MCP OAuth client (PKCE),
opens Strava Approve via /oauth/strava/open on the *bot computer*,
captures the callback, and prints athlete_id only (no tokens).

Usage:
  strava-mcp-connector smoke-oauth
  python -m strava_mcp.scripts.smoke_oauth
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

DEFAULT_SCOPES = "profile:read_all,activity:read_all,activity:read,profile:write"
CALLBACK_PATH = "/smoke-oauth/callback"
SMOKE_TIMEOUT_SEC = 300


def main() -> None:
    """Run the smoke OAuth flow; exit 0 on success with athlete_id printed."""
    _load_dotenv()
    host = os.environ.get("STRAVA_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("STRAVA_MCP_PORT", "8000"))
    base = os.environ.get("STRAVA_MCP_BASE_URL", f"http://localhost:{port}").rstrip("/")
    # Prefer loopback for local MCP API calls
    mcp_origin = f"http://127.0.0.1:{port}"

    client_id = os.environ.get("STRAVA_CLIENT_ID", "").strip()
    client_secret = os.environ.get("STRAVA_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret or client_id == "your_client_id_here":
        print(
            "ERROR: Set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in server/.env "
            "(never commit secrets).",
            file=sys.stderr,
        )
        sys.exit(1)

    server_proc = _ensure_http_server(mcp_origin, host, port)
    try:
        athlete_id = _run_flow(mcp_origin=mcp_origin, base=base)
    finally:
        if server_proc is not None:
            server_proc.terminate()
            try:
                server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server_proc.kill()

    # Contract: print athlete_id only on stdout (tokens stay server-side / not echoed)
    print(athlete_id)


def _load_dotenv() -> None:
    """Load server/.env or ~/.strava-mcp-connector.env into os.environ.

    File values override the process environment so stale shell exports
    (e.g. dummy PORT from a prior agent) do not break local smoke.
    """
    candidates = [
        Path(__file__).resolve().parents[2] / ".env",  # server/.env preferred
        Path.cwd() / ".env",
        Path.home() / ".strava-mcp-connector.env",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key:
                os.environ[key] = value
        break


def _ensure_http_server(mcp_origin: str, host: str, port: int) -> subprocess.Popen | None:
    """Return a Popen if we started the server; None if already up."""
    if _http_up(mcp_origin):
        return None

    server_dir = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env.setdefault("STRAVA_MCP_TRANSPORT", "http")
    env.setdefault("STRAVA_MCP_HOST", host)
    env.setdefault("STRAVA_MCP_PORT", str(port))
    env.setdefault("STRAVA_MCP_BASE_URL", os.environ.get("STRAVA_MCP_BASE_URL", f"http://localhost:{port}"))

    cmd: list[str]
    if (server_dir / "scripts" / "dev_up.sh").is_file():
        cmd = ["bash", str(server_dir / "scripts" / "dev_up.sh")]
    elif _which("strava-mcp-connector"):
        cmd = ["strava-mcp-connector", "--transport", "http"]
    else:
        print("ERROR: cannot start HTTP server (no dev_up.sh / strava-mcp-connector).", file=sys.stderr)
        sys.exit(1)

    proc = subprocess.Popen(
        cmd,
        cwd=str(server_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        text=True,
    )
    deadline = time.time() + 30
    while time.time() < deadline:
        if proc.poll() is not None:
            # Race: another process may have bound the port — re-check readiness
            if _http_up(mcp_origin):
                return None
            err = (proc.stderr.read() if proc.stderr else "") or ""
            print("ERROR: HTTP server exited early.", file=sys.stderr)
            if err.strip():
                print(err.strip()[-800:], file=sys.stderr)
            sys.exit(1)
        if _http_up(mcp_origin):
            return proc
        time.sleep(0.4)
    print("ERROR: HTTP server did not become ready in time.", file=sys.stderr)
    proc.terminate()
    sys.exit(1)


def _http_up(origin: str) -> bool:
    try:
        urllib.request.urlopen(f"{origin}/oauth/strava/start", timeout=2)
        return True
    except Exception:
        return False


def _which(name: str) -> str | None:
    from shutil import which

    return which(name)


def _run_flow(*, mcp_origin: str, base: str) -> int:
    """Register temp client, open Approve on bot, capture callback, return athlete_id."""
    listen_port = _free_port()
    redirect_uri = f"http://127.0.0.1:{listen_port}{CALLBACK_PATH}"
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(code_verifier.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )
    state = secrets.token_urlsafe(16)

    # Capture bucket shared with the HTTP handler
    captured: dict[str, str | None] = {"code": None, "error": None, "state": None}
    ready = threading.Event()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != CALLBACK_PATH:
                self.send_response(404)
                self.end_headers()
                return
            qs = urllib.parse.parse_qs(parsed.query)
            captured["code"] = (qs.get("code") or [None])[0]
            captured["error"] = (qs.get("error") or [None])[0]
            captured["state"] = (qs.get("state") or [None])[0]
            body = b"<html><body><h1>Smoke OAuth OK</h1><p>Return to the agent.</p></body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            ready.set()

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

    httpd = HTTPServer(("127.0.0.1", listen_port), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        reg = _http_json(
            "POST",
            f"{mcp_origin}/register",
            {
                "client_name": "strava-mcp-smoke-oauth",
                "redirect_uris": [redirect_uri],
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "none",
            },
        )
        mcp_client_id = reg["client_id"]
        # Optional secret if registration returned one
        mcp_client_secret = reg.get("client_secret")

        auth_qs = urllib.parse.urlencode(
            {
                "response_type": "code",
                "client_id": mcp_client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
                "state": state,
                "scope": DEFAULT_SCOPES,
            }
        )
        authorize_url = f"{mcp_origin}/authorize?{auth_qs}"

        # Hitting /authorize triggers provider.authorize → open_on_bot_computer(Strava).
        # Do not follow redirects (would hang on Strava HTML). Capture Location instead.
        strava_url = _authorize_no_follow(authorize_url)
        if strava_url:
            _open_on_bot(mcp_origin, strava_url)
        else:
            _open_on_bot(mcp_origin, authorize_url)

        print(
            "Approve Strava on the BOT computer browser (not your laptop). "
            f"Waiting up to {SMOKE_TIMEOUT_SEC}s…",
            file=sys.stderr,
        )
        if not ready.wait(SMOKE_TIMEOUT_SEC):
            print("ERROR: timed out waiting for OAuth callback.", file=sys.stderr)
            sys.exit(1)

        if captured["error"]:
            print(f"ERROR: OAuth error: {captured['error']}", file=sys.stderr)
            sys.exit(1)
        if captured["state"] != state:
            print("ERROR: state mismatch.", file=sys.stderr)
            sys.exit(1)
        if not captured["code"]:
            print("ERROR: missing authorization code.", file=sys.stderr)
            sys.exit(1)

        token_body: dict[str, str] = {
            "grant_type": "authorization_code",
            "code": str(captured["code"]),
            "redirect_uri": redirect_uri,
            "client_id": mcp_client_id,
            "code_verifier": code_verifier,
        }
        if mcp_client_secret:
            token_body["client_secret"] = str(mcp_client_secret)

        tokens = _http_form("POST", f"{mcp_origin}/token", token_body)
        access = tokens.get("access_token")
        if not access:
            print("ERROR: no access_token in token response.", file=sys.stderr)
            sys.exit(1)

        session = _http_json(
            "GET",
            f"{mcp_origin}/oauth/sessions/current",
            None,
            headers={"Authorization": f"Bearer {access}"},
        )
        athlete_id = (session.get("session") or {}).get("athlete_id")
        if athlete_id is None:
            print("ERROR: athlete_id missing from session.", file=sys.stderr)
            sys.exit(1)
        return int(athlete_id)
    finally:
        httpd.shutdown()



def _authorize_no_follow(url: str) -> str | None:
    """GET /authorize without following redirects; return Location if present."""
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
            return None

    opener = urllib.request.build_opener(_NoRedirect)
    try:
        opener.open(url, timeout=15)
        return None
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 303, 307, 308):
            return exc.headers.get("Location")
        # Some stacks return 200 with body; treat as no location
        return None
    except Exception:
        return None


def _open_on_bot(mcp_origin: str, url: str) -> None:
    qs = urllib.parse.urlencode({"url": url})
    try:
        urllib.request.urlopen(f"{mcp_origin}/oauth/strava/open?{qs}", timeout=10)
    except Exception as exc:  # pragma: no cover - best effort
        print(f"WARN: /oauth/strava/open failed: {exc}", file=sys.stderr)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _http_json(
    method: str,
    url: str,
    payload: dict | None,
    headers: dict[str, str] | None = None,
) -> dict:
    data = None
    req_headers = {"Accept": "application/json", **(headers or {})}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        req_headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_form(method: str, url: str, form: dict[str, str]) -> dict:
    data = urllib.parse.urlencode(form).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method=method,
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


if __name__ == "__main__":
    main()
