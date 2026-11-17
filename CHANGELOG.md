# Changelog

## 0.2.1 — 2026-11-17

### Safe 64-bit Activity and Athlete IDs

Strava will allow Activity and Athlete IDs to be 64-bit integers after June 1, 2027, and now also returns `id_str` (the same value as a string). JavaScript MCP hosts cannot hold integers larger than 2^53 − 1 exactly, so this connector now:

- Prefers `id_str` from API responses and falls back to stringifying `id`
- Exposes activity and athlete IDs as strings in tool and resource output
- Accepts string IDs on tool inputs such as `query_activities(activity_id=...)` and `get_activity_social`, while still accepting numeric IDs for backward compatibility
- Uses those string IDs in Strava API URLs without converting them with `int()` or `float()`
- Stores session `athlete_id` as a string (existing numeric session values are coerced on load)

The server is Python, so `json.loads` already preserves 64-bit integers internally. The string-ID change is to keep values exact when responses are parsed by JavaScript clients.

Segment, route, lap, comment, and gear IDs are unchanged; Strava's notice covers Activity and Athlete IDs only.
