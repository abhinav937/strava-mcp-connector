#!/usr/bin/env python3
"""Wrapper: python server/scripts/smoke_oauth.py → strava_mcp.scripts.smoke_oauth."""
from __future__ import annotations

import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parents[1]
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from strava_mcp.scripts.smoke_oauth import main

if __name__ == "__main__":
    main()
