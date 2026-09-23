"""Middleware for stdio mode - env-file-based authentication."""

from collections.abc import Callable
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext

from .client import StravaClient
from .stdio_auth import StdioStravaAuthContext


class StdioClientMiddleware(Middleware):
    """Middleware for stdio mode - loads context from .env and creates StravaClient.

    This middleware:
    1. Receives pre-validated Strava context at initialization
    2. Creates a StravaClient instance per request and manages its lifecycle
    3. Injects the client into the context state for tools to access via await ctx.get_state("client")
    """

    def __init__(self, context: StdioStravaAuthContext) -> None:
        self.context = context

    async def on_call_tool(self, context: MiddlewareContext, call_next: Callable[..., Any]):
        """Create and inject StravaClient before every tool call."""
        # Create client and inject into context, managing lifecycle
        async with StravaClient(self.context) as client:
            if context.fastmcp_context:
                await context.fastmcp_context.set_state("client", client, serializable=False)

            # Continue to the tool execution
            return await call_next(context)

    async def on_read_resource(self, context: MiddlewareContext, call_next: Callable[..., Any]):
        """Create and inject StravaClient before every resource read."""
        # Create client and inject into context, managing lifecycle
        async with StravaClient(self.context) as client:
            if context.fastmcp_context:
                await context.fastmcp_context.set_state("client", client, serializable=False)

            return await call_next(context)
