"""HTTP mode authentication - OAuth provider and session management."""

from __future__ import annotations

import html
from collections.abc import Mapping, Sequence
from typing import Any, cast

import httpx
from fastmcp.server.auth import AccessToken, OAuthProvider
from mcp.server.auth.provider import (
    AuthorizationCode,
    AuthorizationParams,
    TokenError,
    construct_redirect_uri,
)
from mcp.server.auth.settings import ClientRegistrationOptions
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from starlette.requests import Request
from starlette.responses import (
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
)
from starlette.routing import Route

from .browser_open import open_on_bot_computer
from .http_session import (
    ProviderAccessToken,
    ProviderRefreshToken,
    SessionStore,
    StravaOAuthService,
)


class StravaOAuthProvider(OAuthProvider):
    """OAuth provider that performs a two-hop OAuth flow via Strava."""

    def __init__(
        self,
        *,
        base_url: str,
        session_store: SessionStore,
        oauth_service: StravaOAuthService,
        registered_clients: Mapping[str, Sequence[str]],
    ) -> None:
        registration_options = ClientRegistrationOptions(
            enabled=True,
            valid_scopes=list(oauth_service.scopes),
            default_scopes=list(oauth_service.scopes),
        )
        super().__init__(
            base_url=base_url,
            required_scopes=oauth_service.scopes,
            client_registration_options=registration_options,
        )
        self.session_store = session_store
        self.oauth_service = oauth_service
        self._registered_clients = registered_clients
        self._clients_registered = False
        self._registration_options = registration_options

    async def _ensure_registered_clients(self) -> None:
        if self._clients_registered:
            return
        await self.session_store.register_clients(
            self._registered_clients, self.oauth_service.scopes
        )
        self._clients_registered = True

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        await self._ensure_registered_clients()
        return await self.session_store.get_client(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        await self.session_store.register_client_info(client_info)

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        await self._ensure_registered_clients()
        pending = await self.session_store.create_authorization_request(
            client_id=client.client_id,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            code_challenge=params.code_challenge,
            scopes=params.scopes,
            resource=params.resource,
            client_state=params.state,
        )
        auth_url = self.oauth_service.build_authorization_url(pending.state)
        # Open Strava on the *bot computer* (this host), not the user's laptop.
        open_on_bot_computer(auth_url)
        return auth_url

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        return await self.session_store.load_authorization_code(authorization_code)

    async def exchange_authorization_code(
        self,
        client: OAuthClientInformationFull,
        authorization_code: AuthorizationCode,
    ) -> OAuthToken:
        consumed = await self.session_store.consume_authorization_code(authorization_code.code)
        if consumed is None:
            raise TokenError("invalid_grant", "authorization code has expired or is invalid")

        stored_code, session = consumed
        session.resource = stored_code.resource
        tokens = await self.session_store.issue_tokens(
            session,
            client_id=client.client_id,
            scopes=stored_code.scopes,
            resource=stored_code.resource,
        )
        return tokens

    async def load_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: str,
    ) -> ProviderRefreshToken | None:
        return await self.session_store.get_refresh_token(refresh_token)

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: ProviderRefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        result = await self.session_store.exchange_refresh_token(refresh_token.token, scopes=scopes)
        if result is None:
            raise TokenError("invalid_grant", "refresh token is invalid or expired")
        tokens, _ = result
        return tokens

    async def load_access_token(self, token: str) -> AccessToken | None:
        result = await self.session_store.get_access_token(token)
        return cast(AccessToken | None, result)

    async def revoke_token(self, token: ProviderAccessToken | ProviderRefreshToken) -> None:
        if isinstance(token, ProviderAccessToken):
            await self.session_store.revoke_access_token(token.token)
        else:
            await self.session_store.revoke_refresh_token(token.token)

    def get_routes(
        self,
        mcp_path: str | None = None,
    ) -> list[Route]:
        # FastMCP 4+: get_routes(mcp_path) only — no mcp_endpoint kwarg
        routes = super().get_routes(mcp_path)
        routes.extend(
            [
                Route("/oauth/strava/callback", self.complete_authorization, methods=["GET"]),
                Route("/oauth/sessions/current", self.session_introspection, methods=["GET"]),
                Route("/oauth/strava/start", self.manual_instructions, methods=["GET"]),
                Route("/oauth/strava/open", self.open_strava_on_bot, methods=["GET"]),
            ]
        )
        return routes

    async def complete_authorization(self, request: Request) -> Response:
        """Handle Strava's callback, generate an authorization code, and redirect to the client."""
        query = request.query_params
        error = query.get("error")
        state = query.get("state")
        code = query.get("code")

        if error:
            return PlainTextResponse(f"Strava authorization failed: {error}", status_code=400)

        if not state:
            return PlainTextResponse("Missing OAuth state.", status_code=400)

        pending = await self.session_store.pop_authorization_request(state)
        if pending is None:
            return PlainTextResponse("OAuth session expired or invalid state.", status_code=400)

        if not code:
            return PlainTextResponse("Missing authorization code.", status_code=400)

        try:
            session = await self.oauth_service.create_session_from_code(code)
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text.strip() or exc.response.reason_phrase or "unknown error"
            return PlainTextResponse(
                f"Failed to exchange authorization code: {detail}",
                status_code=exc.response.status_code,
            )
        except httpx.HTTPError as exc:
            return PlainTextResponse(
                f"Network error while contacting Strava: {exc}",
                status_code=502,
            )
        except Exception as exc:  # pragma: no cover - defensive
            return PlainTextResponse(str(exc), status_code=500)

        authorization_code = await self.session_store.store_authorization_code(session, pending)
        redirect_url = construct_redirect_uri(
            str(pending.redirect_uri),
            code=authorization_code.code,
            state=pending.client_state,
        )
        return RedirectResponse(redirect_url, status_code=302)

    async def session_introspection(self, request: Request) -> Response:
        """Return basic information about the current session (if authenticated)."""
        token = request.headers.get("authorization")
        if token and token.lower().startswith("bearer "):
            token = token.split(" ", 1)[1]
        else:
            token = request.query_params.get("access_token")

        if not token:
            return JSONResponse({"detail": "Missing access token."}, status_code=401)

        session = await self.session_store.get_session_by_token(token)
        if session is None:
            return JSONResponse({"detail": "Session not found or expired."}, status_code=404)

        return JSONResponse(
            {
                "session": session.as_public_dict(),
                "token": token,
            }
        )

    async def open_strava_on_bot(self, request: Request) -> Response:
        """Build the Strava authorize URL and open it on this machine's browser.

        Agents should call this (or drive Chromium on the bot desktop) so the
        user never has to open Strava on their laptop during setup.
        """
        # Prefer an explicit URL from the query (agent already built authorize URL).
        url = request.query_params.get("url")
        if not url:
            # Fall back to start page which explains Connect; still open Strava settings
            # if ?settings=1 so API-app creation happens on the bot computer too.
            if request.query_params.get("settings") == "1":
                url = "https://www.strava.com/settings/api"
            else:
                url = "https://www.strava.com/oauth/authorize"

        result = open_on_bot_computer(url)
        if request.query_params.get("format") == "html" or "text/html" in (
            request.headers.get("accept") or ""
        ):
            status = "opened" if result.get("ok") else "failed"
            body = f"""
<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/><title>Bot browser</title></head>
<body>
  <h1>Strava on bot computer: {status}</h1>
  <p>Method: <code>{html.escape(str(result.get("method")))}</code></p>
  <p>URL: <code>{html.escape(str(result.get("url")))}</code></p>
  <p>DISPLAY: <code>{html.escape(str(result.get("display")))}</code></p>
  <p>{"Open this URL in the bot desktop browser if the popup did not appear:" if not result.get("ok") else "A browser window should be on the bot desktop — complete Approve there."}</p>
  <p><a href="{html.escape(str(result.get("url") or ""))}">Open link</a></p>
</body></html>
"""
            return HTMLResponse(body, status_code=200 if result.get("ok") else 500)
        return JSONResponse(result, status_code=200 if result.get("ok") else 500)

    async def manual_instructions(self, request: Request) -> Response:
        """Provide guidance for initiating the OAuth flow manually."""
        base_url = str(self.base_url) if self.base_url else ""
        content = f"""
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Strava MCP OAuth</title>
    <style>
      body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        margin: 2rem auto;
        max-width: 720px;
        line-height: 1.6;
      }}
      code {{
        background: #f5f5f5;
        border-radius: 6px;
        padding: 0.2rem 0.4rem;
      }}
    </style>
  </head>
  <body>
    <h1>Connect Strava to your MCP client</h1>
    <p>This server uses <strong>your</strong> Strava API Client ID/Secret (no shared publisher app).
       A Strava subscription is required for Standard Tier API access.</p>
    <p>This MCP server supports the standard OAuth flow used by Cursor and other MCP clients. To initiate the connection:</p>
    <ol>
      <li>In Cursor, install the Strava MCP plugin (or add a Streamable HTTP MCP server).</li>
      <li>Use <code>{html.escape(base_url)}/mcp</code> as the server URL.</li>
      <li><strong>Preferred:</strong> Cursor MCP Connect against this server — the host opens Strava. All Strava UI is on the <strong>bot computer</strong> (never laptop links). Secondary: <code>/oauth/strava/open</code> then <code>request_box_help</code> for password/captcha; do not thrash Chromium.</li>
    </ol>
    <p>If you need to run the flow manually, supply a <code>client_id</code> and <code>redirect_uri</code> when calling the standard OAuth <code>/authorize</code> endpoint.</p>
  </body>
</html>
"""
        return HTMLResponse(content)


# HTTP Mode: OAuth-based multi-user authentication
