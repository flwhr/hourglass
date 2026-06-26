# Hourglass — Multi-Club Tier Tracker (Design)

**Date:** 2026-06-26
**Status:** Approved design, pre-implementation
**Reference:** [oHaruki/UmaCore](https://github.com/oHaruki/UmaCore) (feature parity + new tier layer)

## 1. Purpose

Hourglass is a Discord bot for tracking Uma Musume club fan progress across **multiple
clubs** in a **single Discord server**, with a **tiered promotion/relegation system** layered
on top of UmaCore's quota + bomb-warning feature set.

Each club is assigned a **tier** (1 = highest) and two fan-gain thresholds. Members whose
monthly fan gain clears a club's **promote threshold** get a point-up (↑) marker — they're
ready to move to a higher-tier club next month. Members below the **relegate threshold** get
a point-down (↓) marker. A **global leaderboard** ranks every member across every club by
monthly fan gain.

Actual club moves are performed in-game by club leaders. The bot **informs** (markers +
standings); it does not move members. Because the uma.moe API returns each club's roster, a
member who moves in-game appears under the new club automatically on the next poll — the bot
needs no move command.

## 2. Scope

### In scope (v1)
- Multi-club tracking in one Discord server, sourced solely from the uma.moe v4 API.
- UmaCore-parity quota system: daily/weekly/biweekly quotas + mid-month quota changes.
- UmaCore-parity bomb-warning state machine (consecutive days behind → countdown → expiry alert).
- Tier system: per-club tier + promote/relegate thresholds, ↑/↓ markers.
- Global cross-club leaderboard and monthly tier-standings.
- Visual reports: progress charts (Plotly), monthly tally image + trainer cards (Pillow).
- Stored-history persistence (quota_history, bomb, club_rank_history) for trends/charts.
- Simple permission model: Discord Administrator (+ optional manager role) manage; everyone read-only + self-linking.

### Out of scope (v1)
- ChronoGenesis / Selenium fallback scraper (API is the sole source).
- uma.moe profile-enrichment endpoint (optional nice-to-have; may add later).
- Multi-guild / multi-tenant operation, per-club editor roles.
- Web dashboard (everything is managed via slash commands).
- Auto-moving members between clubs (leaders move in-game; bot reflects via API roster).
- Rank-ordered scrape dispatch + scrape-lock manager (single instance, sequential polling suffices).

## 3. Architecture

discord.py monolith. One process runs the gateway client, slash commands, and a
`discord.ext.tasks` daily loop. PostgreSQL via asyncpg. All uma.moe calls funnel through a
single shared token-bucket rate limiter.

```
hourglass/
├─ main.py                 # entrypoint: client init, command/cog registration, task loop start
├─ config/
│  ├─ settings.py          # env loading (token, DB url, API key, poll time, rate limits, emojis)
│  └─ database.py          # asyncpg pool + schema migrations
├─ models/                 # one module per table; query methods live on the model class
│  ├─ club.py  member.py  quota_history.py  quota_requirement.py
│  ├─ bomb.py  club_rank_history.py  user_link.py
├─ scrapers/
│  └─ umamoe_api.py        # uma.moe v4 client: fetch + parse circle roster (only API surface)
├─ services/
│  ├─ tracker.py           # daily orchestration per club (the poll flow)
│  ├─ quota_calculator.py  # expected-fans pace, deficit, days-behind
│  ├─ bomb_manager.py      # bomb state machine
│  ├─ markers.py           # ↑/↓ marker computation (tier layer)
│  ├─ leaderboard.py       # cross-club global ranking (tier layer)
│  ├─ monthly_info.py      # monthly info board (edit-in-place message)
│  └─ notification.py      # DM + channel alerts, with dedupe
├─ reports/
│  ├─ daily.py             # daily report embed/text
│  ├─ charts.py            # Plotly progression PNG
│  ├─ tally.py             # Pillow monthly tally image
│  └─ trainer_card.py      # Pillow per-member card
├─ commands/               # thin slash-command cogs → call services
│  ├─ clubs.py  channels.py  quota.py  members.py
│  ├─ tiers.py  user.py  charts.py  admin.py
├─ utils/
│  ├─ rate_limiter.py      # shared async token bucket
│  ├─ permissions.py       # admin/manager checks
│  ├─ timezone_helper.py   # tz resolution
│  └─ logger.py
└─ tests/                  # mocked-API unit + service tests
```

**Design rules:** commands are thin and never touch the DB directly — they call services.
`umamoe_api.py` is the only module that touches the network, so it is trivially mockable in
tests. Each service has one responsibility and communicates through model query methods.

## 4. Data source — uma.moe v4 API

### Endpoint
```
GET https://uma.moe/api/v4/circles?circle_id={id}&year={Y}&month={M}
Headers: Accept-Encoding: gzip, deflate
         X-API-Key: {UMAMOE_API_KEY}   # optional, from env
Timeout: 30s
```

### Response shape
```jsonc
{
  "circle": {
    "monthly_rank": int|null,
    "last_month_rank": int|null,
    "yesterday_rank": int|null,
    // + timestamps / live fields
  },
  "members": [
    {
      "viewer_id": int|str,        // trainer id (stable)
      "trainer_name": str,
      "daily_fans": [int, ...]     // LIFETIME cumulative fans, one entry per calendar day
    }
  ]
}
```

### Parsing rules (must implement exactly)
1. **Lifetime → monthly:** detect each member's baseline = first `daily_fans` entry > 0 (the
   join day). `monthly_fans[day] = max(0, lifetime[day] - baseline)`.
2. **Monthly gain** = last valid day's monthly value (= `lifetime[last] - baseline`).
3. **Negative values** in `daily_fans` are transfer markers → treat as 0.
4. **Leavers:** a member showing 0 on the current day is dropped by the API; do not compute
   gains for absent members.
5. **Mid-month joiner:** first non-zero entry on day N → days 1..N-1 are 0, days ≥ N are
   `lifetime[day] - lifetime[N-1-baseline]`.
6. **Day-1-of-month:** current month not yet populated. Fetch **previous month** as the
   reporting source, and also fetch current month to read index 0 as the endpoint correction.
   Report date = last day of previous month.
7. **Freshness:** data publishes ~15:10 UTC. If today's slot is empty, fall back to yesterday
   but verify fan growth vs the day before; if no growth, treat as stale (re-queue later
   rather than write stale data).
8. **JST rollover:** on the last UTC day of the month, if JST (UTC+9) has crossed into the
   next month, the rank fields reflect the new near-empty period — drop rank data to avoid
   false display.

### Rate limiting / retries
- Single shared async token bucket across the daily loop, `/force_check`, and chart commands.
  Configurable `UMAMOE_RATE_PER_MIN` and `UMAMOE_RATE_BURST`. FIFO fairness.
- On 429: back off and retry. Local retries: 3 attempts, 10s delay, ×2 backoff.
- All other non-200 / network errors: log, return None for that club, continue the run.

## 5. Data model (PostgreSQL)

Stored-history parity with UmaCore plus tier fields. All tables carry `guild_id` for safety
even though v1 targets one server.

```
club
  id PK · guild_id · circle_id (unique) · name
  tier int                       -- 1 = highest  [TIER LAYER]
  promote_threshold  bigint      -- monthly gain ≥ → ↑ marker  [TIER LAYER]
  relegate_threshold bigint      -- monthly gain < → ↓ marker  [TIER LAYER]
  daily_quota bigint · quota_period enum(daily,weekly,biweekly)
  timezone text · scrape_time time
  bomb_trigger_days int=3 · bomb_countdown_days int=7 · bombs_enabled bool
  image_report_enabled bool
  report_channel_id · alert_channel_id
  monthly_info_channel_id · monthly_info_message_id
  is_active bool · created_at · updated_at

member
  id PK · club_id FK · trainer_id · trainer_name
  join_date date · is_active bool · manually_deactivated bool · last_seen date
  -- (club_id, trainer_id) unique

quota_history
  id PK · member_id FK · club_id FK · date
  cumulative_fans bigint · expected_fans bigint
  deficit_surplus bigint · days_behind int
  -- (member_id, date) unique; days_behind & deficit computed at write time

quota_requirement
  id PK · club_id FK · effective_date date · daily_quota bigint · set_by
  -- mid-month quota changes; get_quota_for_date() picks latest ≤ date

bomb
  id PK · member_id FK · club_id FK
  activation_date date · days_remaining int · is_active bool
  deactivation_date date · last_countdown_update date   -- idempotent decrement

club_rank_history
  id PK · club_id FK · date · club_rank int · monthly_rank int · scraped_at

user_link
  id PK · discord_user_id · member_id FK
  notify_on_bombs bool=true · notify_on_deficit bool=false · created_at · updated_at
```

## 6. Core flows

### 6.1 Daily poll (scheduled, once/day after 15:10 UTC)
For each active club, sequentially (respecting the rate limiter):
1. Fetch + parse roster (Section 4 rules). On failure: log, post "Club X unreachable", continue.
2. **Monthly reset detection:** if any member's current fans < 50% of the stored previous
   value → new month. Clear `quota_history`, `bomb`, `quota_requirement` for the club and
   reset `manually_deactivated` flags. (API year/month scoping makes this rare, but keep it
   as a safety net for the stored-history tables.)
3. **Upsert members:** new trainers inserted with detected `join_date`; reappearing members
   reactivated (unless `manually_deactivated`); set `last_seen`.
4. **Quota pace** (`quota_calculator`): `start_date` = join_date if joined this month else
   1st of month; `days_active = (current - start).days + 1`. `expected = Σ over active days of
   (quota_for_date / period_days)` where period_days = 1/7/14. `deficit_surplus =
   cumulative_fans - expected`. `days_behind` = consecutive days with deficit < 0 (current
   month only). Write `quota_history` row.
5. **Bomb state machine** (`bomb_manager`): see 6.2.
6. **Markers** (`markers`): see 6.3.
7. **Reports + alerts:** post daily report (PNG tally if `image_report_enabled`, else embed)
   to `report_channel`; bomb/kick alerts to `alert_channel`; refresh monthly info board; DM
   linked users per their prefs (deduped, once/day).
8. Record `club_rank_history` (unless dropped due to JST rollover).

`/force_check` runs this flow on demand for one club.

### 6.2 Bomb state machine
- **Activate:** `days_behind ≥ club.bomb_trigger_days` (default 3) and no active bomb →
  create bomb with `days_remaining = bomb_countdown_days` (default 7), `activation_date =
  today`.
- **Decrement:** once per calendar day, guarded by `last_countdown_update` (idempotent under
  repeated `/force_check`).
- **Recover/deactivate:** latest `deficit_surplus ≥ 0` → deactivate immediately.
- **Expire:** `days_remaining ≤ 0` and still behind → post a "bomb expired" alert. (UmaCore
  kicks; Hourglass cannot kick in-game, so this is alert-only.)
- Monthly reset clears all bombs.

### 6.3 Marker computation (tier layer)
Per member, from current-month gain vs the member's **club** thresholds:
- `gain ≥ club.promote_threshold` → `↑` (promote: ready for a higher tier).
- `gain < club.relegate_threshold` → `↓` (relegate: drop toward a lower tier).
- otherwise → none.

Markers are recomputed every poll (always live) and rendered beside member names in reports,
the leaderboard, and tier-standings. Emojis configurable via env.

### 6.4 Global leaderboard (tier layer)
Aggregate all active members across all clubs; rank by current-month gain descending. Each
row: rank, member, club, club tier, gain, marker. Served by `/leaderboard` and used in the
monthly standings. Computed on demand from the latest `quota_history` per member (or a fresh
poll if forced).

### 6.5 Monthly rollover / tier-standings
On wall-clock month change, post per-club final standings (members sorted by gain with ↑/↓
markers) plus a promotion/relegation summary (who cleared promote, who fell below relegate).
Leaders then move members in-game; next poll the API roster reflects moves automatically.
`/tier_standings` renders this on demand.

## 7. Commands

Permission tiers: **Manage** = Discord Administrator or an optional configured manager role;
**Everyone** = read-only + self-service linking.

| Group | Command | Perm | Purpose |
|---|---|---|---|
| Clubs | `/add_club` | Manage | Register club (circle_id, name, tier, thresholds, quota, tz, scrape_time) |
| | `/edit_club` | Manage | Edit any club setting incl. tier + thresholds + bomb params |
| | `/remove_club` | Manage | Delete club + data (confirm modal) |
| | `/activate_club` | Manage | Reactivate a deactivated club |
| | `/list_clubs` | Everyone | List clubs with tier, quota, status |
| Channels | `/set_report_channel` | Manage | Daily report destination |
| | `/set_alert_channel` | Manage | Bomb/kick alert destination |
| | `/channel_settings` | Manage | View channel config |
| | `/post_monthly_info` | Manage | Post the monthly info board |
| | `/update_monthly_info` | Manage | Refresh the monthly info board |
| Quota | `/quota` | Manage | Set daily/weekly/biweekly quota (effective forward) |
| | `/quota_history` | Manage | List quota changes this month |
| | `/delete_quota` | Manage | Remove a quota entry |
| | `/force_check` | Manage | Run the poll flow now for a club |
| Members | `/add_member` | Manage | Manually add a member (name, join_date, trainer_id) |
| | `/activate_member` | Manage | Reactivate a member |
| | `/deactivate_member` | Manage | Deactivate (blocks auto-reactivation) |
| | `/member_status` | Everyone | Trainer card: progress, days behind, bomb, marker |
| | `/bomb_status` | Manage | List active bombs |
| Tiers | `/set_tier` | Manage | Set a club's tier number |
| | `/set_thresholds` | Manage | Set a club's promote/relegate thresholds |
| | `/leaderboard` | Everyone | Global cross-club ranking by monthly gain |
| | `/tier_standings` | Everyone | Per-club standings + promotion/relegation summary |
| User | `/link_trainer` | Everyone | Link Discord ↔ trainer (enables DMs) |
| | `/unlink` | Everyone | Remove own link |
| | `/notification_settings` | Linked | Toggle bomb / deficit DMs |
| | `/my_status` | Linked | Own trainer card |
| Charts | `/progress_chart` | Everyone | Monthly fan progression line chart (PNG) |
| | `/previous_month` | Everyone | Last month's totals + quota recap |
| Admin | `/recalculate` | Manage | Recompute days-behind/bombs without clearing history |
| | `/reset_month` | Manage | Clear monthly data for a club |
| | `/stats` | Manage | Bot/club/member counts |

## 8. Error handling
- Per-club try/except in the daily loop: a failing club never aborts the run; report notes it.
- API: retry then skip; never crash the loop. Freshness/stale → re-queue rather than write.
- DM failures (Forbidden, etc.) logged, never fatal.
- DB writes per member in their own transaction so one bad row doesn't roll back the club.

## 9. Testing
- **Mocked API client** with fixture JSON covering: normal month, day-1 boundary, mid-month
  joiner, leaver, negative/transfer values, monthly reset (<50% drop).
- **Unit tests:** lifetime→monthly gain, quota pace (daily/weekly/biweekly + mid-month change),
  deficit/days-behind, bomb state machine (activate/decrement/recover/expire, idempotent
  decrement), marker thresholds (↑/↓/none at boundaries).
- **Service tests:** global leaderboard ordering across clubs, monthly tier-standings summary,
  notification dedupe.
- **Render smoke tests:** charts/tally/trainer-card produce a valid PNG for a sample payload.

## 10. Configuration (env)
`DISCORD_TOKEN`, `DATABASE_URL`, `UMAMOE_API_KEY` (optional), `UMAMOE_RATE_PER_MIN`,
`UMAMOE_RATE_BURST`, `POLL_TIME_UTC` (default after 15:10), `MANAGER_ROLE_ID` (optional),
`EMOJI_PROMOTE` (↑), `EMOJI_RELEGATE` (↓). Deployed via Docker + docker-compose (bot + Postgres).
