import pytest

from config.settings import Settings, load_settings


def test_load_settings_full():
    env = {
        "DISCORD_TOKEN": "tok",
        "DATABASE_URL": "postgres://x",
        "UMAMOE_API_KEY": "key",
        "UMAMOE_RATE_PER_MIN": "30",
        "UMAMOE_RATE_BURST": "8",
        "POLL_TIME_UTC": "16:00",
        "MANAGER_ROLE_ID": "12345",
        "EMOJI_PROMOTE": "U",
        "EMOJI_RELEGATE": "D",
    }
    s = load_settings(env)
    assert isinstance(s, Settings)
    assert s.discord_token == "tok"
    assert s.database_url == "postgres://x"
    assert s.umamoe_api_key == "key"
    assert s.umamoe_rate_per_min == 30.0
    assert s.umamoe_rate_burst == 8
    assert s.poll_time_utc == "16:00"
    assert s.manager_role_id == 12345
    assert s.emoji_promote == "U"
    assert s.emoji_relegate == "D"


def test_load_settings_defaults():
    env = {"DISCORD_TOKEN": "tok", "DATABASE_URL": "postgres://x"}
    s = load_settings(env)
    assert s.umamoe_api_key is None
    assert s.umamoe_rate_per_min == 20.0
    assert s.umamoe_rate_burst == 5
    assert s.poll_time_utc == "15:20"
    assert s.manager_role_id is None
    assert s.emoji_promote == "⬆️"
    assert s.emoji_relegate == "⬇️"


def test_load_settings_missing_required_raises():
    with pytest.raises(KeyError):
        load_settings({"DATABASE_URL": "postgres://x"})
