"""Open URLs on the *bot computer* (this machine), not the user's laptop."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import webbrowser

log = logging.getLogger(__name__)

# Prefer Chromium/Chrome on headless agent boxes, then xdg-open, then webbrowser.
_CANDIDATES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "firefox",
)


def open_on_bot_computer(url: str, *, new: int = 1) -> dict:
    """Open `url` in a browser on the machine running this MCP server.

    Returns a small status dict for agents/logs. Never silently assumes the
    user's laptop will see the window — this is intentionally local to the box.
    """
    if not url or not str(url).strip():
        return {"ok": False, "error": "empty url"}

    url = str(url).strip()
    display = os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")

    for name in _CANDIDATES:
        binary = shutil.which(name)
        if not binary:
            continue
        try:
            subprocess.Popen(
                [binary, "--new-window", url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            log.info("Opened on bot computer via %s: %s", binary, url)
            return {"ok": True, "method": binary, "url": url, "display": display}
        except OSError as exc:
            log.warning("Failed to launch %s: %s", binary, exc)

    xdg = shutil.which("xdg-open")
    if xdg:
        try:
            subprocess.Popen(
                [xdg, url],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            log.info("Opened on bot computer via xdg-open: %s", url)
            return {"ok": True, "method": "xdg-open", "url": url, "display": display}
        except OSError as exc:
            log.warning("xdg-open failed: %s", exc)

    try:
        opened = webbrowser.open(url, new=new)
        return {
            "ok": bool(opened),
            "method": "webbrowser",
            "url": url,
            "display": display,
            "error": None if opened else "webbrowser.open returned False",
        }
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "method": None, "url": url, "error": str(exc), "display": display}
