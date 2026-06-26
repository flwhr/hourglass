SCHEMA = """
CREATE TABLE IF NOT EXISTS club (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    guild_id INTEGER,
    circle_id TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    tier INTEGER NOT NULL DEFAULT 1,
    promote_threshold INTEGER NOT NULL DEFAULT 0,
    relegate_threshold INTEGER NOT NULL DEFAULT 0,
    daily_quota INTEGER NOT NULL DEFAULT 0,
    quota_period TEXT NOT NULL DEFAULT 'daily',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    scrape_time TEXT NOT NULL DEFAULT '15:20',
    bomb_trigger_days INTEGER NOT NULL DEFAULT 3,
    bomb_countdown_days INTEGER NOT NULL DEFAULT 7,
    bombs_enabled INTEGER NOT NULL DEFAULT 1,
    image_report_enabled INTEGER NOT NULL DEFAULT 0,
    report_channel_id INTEGER,
    alert_channel_id INTEGER,
    monthly_info_channel_id INTEGER,
    monthly_info_message_id INTEGER,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS member (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL REFERENCES club(id) ON DELETE CASCADE,
    trainer_id TEXT NOT NULL,
    trainer_name TEXT NOT NULL,
    join_date TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    manually_deactivated INTEGER NOT NULL DEFAULT 0,
    last_seen TEXT,
    UNIQUE (club_id, trainer_id)
);

CREATE TABLE IF NOT EXISTS quota_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id INTEGER NOT NULL REFERENCES member(id) ON DELETE CASCADE,
    club_id INTEGER NOT NULL REFERENCES club(id) ON DELETE CASCADE,
    date TEXT NOT NULL,
    cumulative_fans INTEGER NOT NULL,
    expected_fans INTEGER NOT NULL,
    deficit_surplus INTEGER NOT NULL,
    days_behind INTEGER NOT NULL,
    UNIQUE (member_id, date)
);

CREATE TABLE IF NOT EXISTS quota_requirement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL REFERENCES club(id) ON DELETE CASCADE,
    effective_date TEXT NOT NULL,
    daily_quota INTEGER NOT NULL,
    set_by INTEGER
);
"""
