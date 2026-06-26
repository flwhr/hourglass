# Hourglass

A Discord bot that tracks Uma Musume club fan progress across multiple clubs and
ranks members into a tiered promotion/relegation system.

It polls the [uma.moe](https://uma.moe) circles API once a day, records each member's
monthly fan gain, checks it against per-club quotas, and posts reports to Discord. On top
of that it adds a tier layer: each club has a rank (tier) and two fan-gain thresholds, so
members who clear the upper threshold are marked for promotion to a higher-tier club and
those below the lower threshold are marked for relegation. Actual roster moves are made
in-game by club leaders; the bot tracks and reports, it does not move anyone.

## How it works

- **Clubs are registered by circle id.** You add a club with its uma.moe `circle_id`; the
  member roster comes from the API, so there is no manual roster upkeep. A member who
  changes clubs in-game shows up under the new circle on the next poll.
- **Daily poll.** Once a day (after uma.moe publishes, around 15:10 UTC) the bot fetches
  each active club's circle. The API returns lifetime cumulative fan counts per day; the
  bot subtracts each member's join-day baseline to get the month-to-date gain. Day-one,
  data-freshness, and JST month-rollover edge cases are handled.
- **Quota and bomb warnings.** Each club has a daily quota (daily, weekly, or biweekly
  pacing). A member behind pace for three consecutive days gets a "bomb" with a seven-day
  recovery countdown; recovering clears it, running out posts an alert. Channel alerts and
  opt-in direct messages go to linked members.
- **Tiers and markers.** Each club has a tier number (1 is highest) and a promote and
  relegate threshold. A member whose monthly gain reaches the promote threshold is marked
  for promotion; below the relegate threshold, for relegation. Thresholds of zero mean
  "unset" and produce no marker.
- **Leaderboard and standings.** A global leaderboard ranks every member across every club
  by monthly gain. Tier standings group members by club and summarize who is up for
  promotion or relegation. At the start of a new month the standings are posted
  automatically to each club's report channel.
- **Storage.** All state lives in a single SQLite file. History is kept per member per day,
  so charts and recaps work without re-fetching.

## What the output looks like

Daily report:

```
Alpha — daily report 2026-06-12 (3 members)
1. Ada — 4,820,000 fans — on pace
2. Bea — 3,110,000 fans — behind 2d
3. Cyn — 1,540,000 fans — behind 5d
```

Global leaderboard (a configurable promote/relegate marker appears after the gain):

```
Leaderboard
1. Ada — Alpha (T1) — 4,820,000
2. Del — Bravo (T2) — 4,400,000
3. Bea — Alpha (T1) — 3,110,000
```

Tier standings:

```
Tier 1 — Alpha
  Ada — 4,820,000
  Bea — 3,110,000
  promote: Ada   relegate: Bea
Tier 2 — Bravo
  Del — 4,400,000
  (no moves)
```

Member views are also rendered as PNG images (a standings tally, a per-member card, and a
fan-progression chart).

## Setup

Requires Python 3.10 or newer.

```
git clone https://github.com/flwhr/hourglass
cd hourglass
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and set at least `DISCORD_TOKEN`. Then run:

```
python main.py
```

The bot reads its configuration from the `.env` file. On first run it creates the SQLite
database at the path given by `DATABASE_URL`.

## Configuration

All settings live in `.env` (see `.env.example`).

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `DISCORD_TOKEN` | yes | — | Discord bot token |
| `DATABASE_URL` | yes | `hourglass.db` | SQLite database file path |
| `UMAMOE_API_KEY` | no | unset | uma.moe key, only for protected endpoints |
| `UMAMOE_RATE_PER_MIN` | no | `20` | Shared API rate limit, requests per minute |
| `UMAMOE_RATE_BURST` | no | `5` | API rate limiter burst size |
| `POLL_TIME_UTC` | no | `15:20` | Daily poll time, UTC, `HH:MM` |
| `MANAGER_ROLE_ID` | no | unset | Role allowed to manage clubs besides server admins |
| `EMOJI_PROMOTE` | no | up arrow | Promotion marker |
| `EMOJI_RELEGATE` | no | down arrow | Relegation marker |

## Commands

Management commands require a server Administrator or the configured manager role. The rest
are open to everyone; linking and status commands reply privately.

**Clubs**

| Command | Purpose |
| --- | --- |
| `/add_club` | Register a club (name, circle id, tier, thresholds, quota) |
| `/edit_club` | Change a club's settings |
| `/list_clubs` | List tracked clubs |
| `/remove_club` | Delete a club and all its data |
| `/activate_club` | Reactivate a club |

**Tiers**

| Command | Purpose |
| --- | --- |
| `/set_tier` | Set a club's tier |
| `/set_thresholds` | Set a club's promote and relegate thresholds |
| `/leaderboard` | Global cross-club fan-gain leaderboard |
| `/tier_standings` | Per-club standings with promotion and relegation |

**Quota and checks**

| Command | Purpose |
| --- | --- |
| `/quota` | Set a club's daily quota, effective from today |
| `/force_check` | Run a club's poll and report now |
| `/reset_month` | Clear a club's monthly data |

**Channels and reports**

| Command | Purpose |
| --- | --- |
| `/set_report_channel` | Set the daily report channel |
| `/set_alert_channel` | Set the bomb and alert channel |
| `/channel_settings` | Show a club's channel configuration |
| `/post_monthly_info` | Post a club's monthly info board |
| `/update_monthly_info` | Refresh the monthly info board in place |
| `/progress_chart` | Fan progression chart for a club |
| `/previous_month` | Last month's recap for a club |

**Members**

| Command | Purpose |
| --- | --- |
| `/add_member` | Manually add a member |
| `/deactivate_member` | Deactivate a member |
| `/activate_member` | Reactivate a member |
| `/member_status` | Show a member's trainer card |
| `/bomb_status` | List active bombs in a club |

**Linking and personal**

| Command | Purpose |
| --- | --- |
| `/link_trainer` | Link your Discord account to a trainer |
| `/unlink` | Remove your trainer link |
| `/notification_settings` | Toggle your bomb and deficit DMs |
| `/my_status` | Show your linked trainer's status |

**Admin**

| Command | Purpose |
| --- | --- |
| `/stats` | Bot, club, member, and bomb counts |

## Project layout

```
bot.py            Discord client, slash-command registration, scheduler loop
main.py           Entry point: load config, open database, start the bot
config/           Settings loader
db/               SQLite wrapper, schema, and one repository module per table
scrapers/         uma.moe API client and response parser
services/         Tracking, quota, bombs, markers, leaderboard, scheduling
reports/          Text reports and PNG image rendering
commands/         Command handlers (return text, no Discord types)
tests/            Test suite
```

The command handlers and services hold the logic and contain no Discord-specific code, so
they are tested directly. `bot.py` is the only module that talks to Discord.

## Testing

```
python -m pytest
```

## Notes

- Single Discord server. Clubs, tiers, and the leaderboard span that one server.
- Markers are advisory. The bot reports who should move; leaders move members in-game and
  the next poll reflects it.
- Configuration is read from `.env` only, not from shell environment variables.
