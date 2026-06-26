import pytest

from hourglass.bot import build_bot
from hourglass.config.settings import load_settings


@pytest.mark.asyncio
async def test_build_bot_registers_expected_commands():
    settings = load_settings({"DISCORD_TOKEN": "x", "DATABASE_URL": "y"})
    bot = build_bot(db=None, client=None, settings=settings)
    names = {c.name for c in bot.tree.get_commands()}
    assert {
        "add_club", "edit_club", "list_clubs",
        "set_report_channel", "quota", "force_check",
        "set_alert_channel", "link_trainer", "unlink",
        "notification_settings", "my_status", "bomb_status",
        "set_tier", "set_thresholds", "leaderboard", "tier_standings",
    } <= names
