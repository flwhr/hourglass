import pytest

from bot import build_bot
from config.settings import load_settings


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
        "add_member", "deactivate_member", "activate_member",
        "remove_club", "activate_club", "reset_month", "stats",
        "channel_settings", "previous_month",
        "post_monthly_info", "update_monthly_info", "progress_chart", "member_status",
    } <= names
