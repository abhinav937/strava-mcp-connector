# Tool scope — Strava MCP Connector

This connector exposes **Strava API fetch/mutate** tools that map closely to Strava itself.
Training analysis, comparison, and coaching-style tools are **intentionally excluded**
(those remain with the Austin Half Trainer agent / local `user-strava-local` MCP).

## Requirements (marketplace)

Before install / OAuth, the user needs:

1. **Strava account**
2. **Strava subscription (Premium/Subscriber)** — hard requirement for Standard Tier API access under Strava’s 2026 developer policy ([API FAQ](https://communityhub.strava.com/developers-knowledge-base-14/strava-api-faq-12906))
3. **Their own API application** at https://www.strava.com/settings/api (Client ID + Client Secret) — **no shared publisher app**
4. Correct **Authorization Callback Domain** (`localhost` locally, or hosted hostname)
5. OAuth scopes (defaults): `profile:read_all`, `activity:read_all`, `activity:read`, `profile:write`
6. **Cursor** + local or self-hosted MCP HTTP process for this connector
7. Awareness of **tool limitations** below (subscription ≠ full Extended Access)
8. **Rate limits** are per **their** API app

Strava also offers an **official subscriber MCP** for single-user AI access without building an API app. This plugin is a **fetch-only alternative** using the user’s own API app + OAuth. Agent skill: **`strava-setup`**.

## Marketplace install story

1. Install the Cursor plugin.
2. Agent runs **`strava-setup`**: confirms subscription → user creates API app → Client ID/Secret → OAuth (authorize → redirect → token exchange) → smoke test.
3. Use the fetch-only tools below.

## Included (8 tools)

| Tool | Kind | Notes |
| --- | --- | --- |
| `query_activities` | fetch | List/get activities; optional streams, laps, zones |
| `get_activity_social` | fetch | Comments / kudos for an activity |
| `get_athlete_profile` | fetch | Athlete profile, stats, zones, gear |
| `query_routes` | fetch | List/get routes |
| `export_route` | mutate/export | Export route as GPX/TCX to `ROUTE_EXPORT_PATH` |
| `query_segments` | fetch | Starred / explore / single segment (+ efforts). **Explore may fail** on Standard Tier without Extended Access — prefer starred / by id. |
| `get_segment_leaderboard` | fetch | Segment leaderboard — may return partial/empty or errors if fields are access-gated |
| `star_segment` | mutate | Star / unstar a segment (`profile:write`) |

Also registered:

- Resource: `strava://athlete/profile`
- Prompts: `segment_performance`, `activity_overview`, `recent_activities` (fetch-oriented only)

### Access honesty

- A Strava **subscription** unlocks **Standard Tier** public API use for the user’s own app; it does **not** grant Partner APIs or guarantee every historically Premium-gated field.
- **Extended Access** is a separate tier (review, higher limits, Partner eligibility). Segment **explore** and some commercial surfaces often need it — do not claim Premium alone unlocks explore.
- Rate limits and athlete capacity apply to **that user’s** application.

## Excluded (stay with trainer agent)

| Tool | Reason |
| --- | --- |
| `analyze_training` | Training volume / intensity / coaching analysis |
| `compare_activities` | Side-by-side performance comparison |
| `find_similar_activities` | Similarity search over past activities |

Analysis-heavy MCP prompts that referenced those tools (`analyze_recent_training`,
`compare_recent_runs`, `training_summary`, `race_performance_analysis`) are also omitted.
