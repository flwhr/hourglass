from __future__ import annotations

import datetime as _dt
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

import io

from hourglass.commands import clubs_cmd, ops_cmd, links_cmd, tier_cmd
from hourglass.commands import admin_cmd, club_admin_cmd, members_cmd, status_cmd
from hourglass.commands import board_cmd
from hourglass.db import clubs
from hourglass.db import history as history_repo
from hourglass.reports.images import render_progress_chart, render_trainer_card
from hourglass.services.scheduler import run_due_clubs
from hourglass.services.rollover import period_key, should_post_rollover
from hourglass.utils.permissions import user_is_manager

logger = logging.getLogger(__name__)


def build_bot(db, client, settings) -> commands.Bot:
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)
    last_runs: dict[int, _dt.date] = {}
    last_posted_period = [None]

    def _is_manager(interaction: discord.Interaction) -> bool:
        perms = interaction.user.guild_permissions
        role_ids = {r.id for r in getattr(interaction.user, "roles", [])}
        return user_is_manager(perms.administrator, role_ids, settings.manager_role_id)

    async def _send(channel_id: int, text: str) -> None:
        channel = bot.get_channel(channel_id)
        if channel is not None:
            await channel.send(text)

    async def _dm(discord_user_id: int, text: str) -> None:
        user = bot.get_user(discord_user_id)
        if user is None:
            try:
                user = await bot.fetch_user(discord_user_id)
            except Exception:
                return
        try:
            await user.send(text)
        except Exception:
            pass

    @tasks.loop(minutes=1)
    async def scheduler_loop():
        now = _dt.datetime.now(_dt.timezone.utc)
        await run_due_clubs(db, client, now, _send, last_runs, _dm)
        if should_post_rollover(now, last_posted_period[0]):
            last_posted_period[0] = period_key(now)
            standings = await tier_cmd.cmd_tier_standings(
                db, up_emoji=settings.emoji_promote, down_emoji=settings.emoji_relegate)
            for club_row in await clubs.list_clubs(db, active_only=True):
                if club_row["report_channel_id"] is not None:
                    await _send(club_row["report_channel_id"], standings[:1900])
        else:
            last_posted_period[0] = period_key(now)

    @bot.event
    async def on_ready():
        await bot.tree.sync()
        if not scheduler_loop.is_running():
            scheduler_loop.start()
        logger.info("Hourglass logged in as %s", bot.user)

    @bot.tree.command(name="list_clubs", description="List tracked clubs")
    @app_commands.guild_only()
    async def list_clubs(interaction: discord.Interaction):
        await interaction.response.send_message(await clubs_cmd.cmd_list_clubs(db))

    @bot.tree.command(name="add_club", description="Register a club for tracking")
    @app_commands.guild_only()
    async def add_club(
        interaction: discord.Interaction, name: str, circle_id: str, tier: int = 1,
        promote_threshold: int = 0, relegate_threshold: int = 0,
        daily_quota: int = 0, quota_period: str = "daily",
    ):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        msg = await clubs_cmd.cmd_add_club(
            db, name=name, circle_id=circle_id, tier=tier,
            promote_threshold=promote_threshold, relegate_threshold=relegate_threshold,
            daily_quota=daily_quota, quota_period=quota_period,
        )
        await interaction.response.send_message(msg)

    @bot.tree.command(name="edit_club", description="Edit a club's settings")
    @app_commands.guild_only()
    async def edit_club(
        interaction: discord.Interaction, name: str, tier: int | None = None,
        promote_threshold: int | None = None, relegate_threshold: int | None = None,
        daily_quota: int | None = None, quota_period: str | None = None,
    ):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        msg = await clubs_cmd.cmd_edit_club(
            db, name=name, tier=tier, promote_threshold=promote_threshold,
            relegate_threshold=relegate_threshold, daily_quota=daily_quota,
            quota_period=quota_period,
        )
        await interaction.response.send_message(msg)

    @bot.tree.command(name="set_report_channel", description="Set a club's daily report channel")
    @app_commands.guild_only()
    async def set_report_channel(
        interaction: discord.Interaction, club: str, channel: discord.TextChannel
    ):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        msg = await ops_cmd.cmd_set_report_channel(db, club_name=club, channel_id=channel.id)
        await interaction.response.send_message(msg)

    @bot.tree.command(name="quota", description="Set a club's daily quota (from today)")
    @app_commands.guild_only()
    async def quota(interaction: discord.Interaction, club: str, amount: int):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        today = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
        msg = await ops_cmd.cmd_set_quota(db, club_name=club, amount=amount, on_date=today)
        await interaction.response.send_message(msg)

    @bot.tree.command(name="force_check", description="Run a club's check now")
    @app_commands.guild_only()
    async def force_check(interaction: discord.Interaction, club: str):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.defer()
        now = _dt.datetime.now(_dt.timezone.utc)
        msg = await ops_cmd.cmd_force_check(db, client, club_name=club, now_utc=now, send=_send)
        await interaction.followup.send(msg[:1900])

    @bot.tree.command(name="set_alert_channel", description="Set a club's bomb/alert channel")
    @app_commands.guild_only()
    async def set_alert_channel(interaction: discord.Interaction, club: str, channel: discord.TextChannel):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        row = await clubs.get_club_by_name(db, club)
        if row is None:
            await interaction.response.send_message(f"No club named '{club}'.")
            return
        await clubs.update_club(db, row["id"], alert_channel_id=channel.id)
        await interaction.response.send_message(f"Alert channel set for '{club}'.")

    @bot.tree.command(name="link_trainer", description="Link your Discord to a trainer")
    @app_commands.guild_only()
    async def link_trainer(interaction: discord.Interaction, club: str, trainer_name: str):
        msg = await links_cmd.cmd_link_trainer(
            db, discord_user_id=interaction.user.id, club_name=club, trainer_name=trainer_name)
        await interaction.response.send_message(msg, ephemeral=True)

    @bot.tree.command(name="unlink", description="Remove your trainer link")
    @app_commands.guild_only()
    async def unlink(interaction: discord.Interaction):
        msg = await links_cmd.cmd_unlink(db, discord_user_id=interaction.user.id)
        await interaction.response.send_message(msg, ephemeral=True)

    @bot.tree.command(name="notification_settings", description="Toggle your DM alerts")
    @app_commands.guild_only()
    async def notification_settings(
        interaction: discord.Interaction, bomb_warnings: bool | None = None, deficit_alerts: bool | None = None
    ):
        msg = await links_cmd.cmd_notification_settings(
            db, discord_user_id=interaction.user.id, on_bombs=bomb_warnings, on_deficit=deficit_alerts)
        await interaction.response.send_message(msg, ephemeral=True)

    @bot.tree.command(name="my_status", description="Show your linked trainer's status")
    @app_commands.guild_only()
    async def my_status(interaction: discord.Interaction):
        msg = await status_cmd.cmd_my_status(db, discord_user_id=interaction.user.id)
        await interaction.response.send_message(msg, ephemeral=True)

    @bot.tree.command(name="bomb_status", description="List active bombs in a club")
    @app_commands.guild_only()
    async def bomb_status(interaction: discord.Interaction, club: str):
        await interaction.response.send_message(await links_cmd.cmd_bomb_status(db, club_name=club))

    @bot.tree.command(name="set_tier", description="Set a club's tier (1 = highest)")
    @app_commands.guild_only()
    async def set_tier(interaction: discord.Interaction, club: str, tier: int):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.send_message(await tier_cmd.cmd_set_tier(db, club_name=club, tier=tier))

    @bot.tree.command(name="set_thresholds", description="Set a club's promote/relegate thresholds")
    @app_commands.guild_only()
    async def set_thresholds(interaction: discord.Interaction, club: str, promote: int, relegate: int):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.send_message(
            await tier_cmd.cmd_set_thresholds(db, club_name=club, promote=promote, relegate=relegate))

    @bot.tree.command(name="leaderboard", description="Global cross-club fan-gain leaderboard")
    @app_commands.guild_only()
    async def leaderboard(interaction: discord.Interaction):
        msg = await tier_cmd.cmd_leaderboard(
            db, up_emoji=settings.emoji_promote, down_emoji=settings.emoji_relegate)
        await interaction.response.send_message(msg[:1900])

    @bot.tree.command(name="tier_standings", description="Per-club standings with promotion/relegation")
    @app_commands.guild_only()
    async def tier_standings(interaction: discord.Interaction):
        msg = await tier_cmd.cmd_tier_standings(
            db, up_emoji=settings.emoji_promote, down_emoji=settings.emoji_relegate)
        await interaction.response.send_message(msg[:1900])

    @bot.tree.command(name="add_member", description="Manually add a member")
    @app_commands.guild_only()
    async def add_member(interaction: discord.Interaction, club: str, trainer_name: str,
                         trainer_id: str, join_date: str):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.send_message(await members_cmd.cmd_add_member(
            db, club_name=club, trainer_name=trainer_name, trainer_id=trainer_id, join_date=join_date))

    @bot.tree.command(name="deactivate_member", description="Deactivate a member")
    @app_commands.guild_only()
    async def deactivate_member(interaction: discord.Interaction, club: str, trainer_name: str):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.send_message(await members_cmd.cmd_deactivate_member(
            db, club_name=club, trainer_name=trainer_name))

    @bot.tree.command(name="activate_member", description="Reactivate a member")
    @app_commands.guild_only()
    async def activate_member(interaction: discord.Interaction, club: str, trainer_name: str):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.send_message(await members_cmd.cmd_activate_member(
            db, club_name=club, trainer_name=trainer_name))

    @bot.tree.command(name="remove_club", description="Delete a club and all its data")
    @app_commands.guild_only()
    async def remove_club(interaction: discord.Interaction, club: str):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.send_message(await club_admin_cmd.cmd_remove_club(db, club_name=club))

    @bot.tree.command(name="activate_club", description="Reactivate a club")
    @app_commands.guild_only()
    async def activate_club(interaction: discord.Interaction, club: str):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.send_message(await club_admin_cmd.cmd_activate_club(db, club_name=club))

    @bot.tree.command(name="reset_month", description="Clear a club's monthly data")
    @app_commands.guild_only()
    async def reset_month(interaction: discord.Interaction, club: str):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.send_message(await admin_cmd.cmd_reset_month(db, club_name=club))

    @bot.tree.command(name="stats", description="Show bot statistics")
    @app_commands.guild_only()
    async def stats(interaction: discord.Interaction):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.send_message(await admin_cmd.cmd_stats(db))

    @bot.tree.command(name="channel_settings", description="Show a club's channel config")
    @app_commands.guild_only()
    async def channel_settings(interaction: discord.Interaction, club: str):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.send_message(await admin_cmd.cmd_channel_settings(db, club_name=club))

    @bot.tree.command(name="previous_month", description="Show last month's recap for a club")
    @app_commands.guild_only()
    async def previous_month(interaction: discord.Interaction, club: str):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.defer()
        now = _dt.datetime.now(_dt.timezone.utc)
        msg = await status_cmd.cmd_previous_month(db, client, club_name=club, now_utc=now)
        await interaction.followup.send(msg[:1900])

    @bot.tree.command(name="post_monthly_info", description="Post a club's monthly info board")
    @app_commands.guild_only()
    async def post_monthly_info(interaction: discord.Interaction, club: str, channel: discord.TextChannel):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.defer()
        now = _dt.datetime.now(_dt.timezone.utc)
        content = await board_cmd.cmd_monthly_info_content(db, client, club_name=club, now_utc=now)
        sent = await channel.send(content[:1900])
        row = await clubs.get_club_by_name(db, club)
        if row is not None:
            await clubs.set_monthly_info(db, row["id"], channel_id=channel.id, message_id=sent.id)
        await interaction.followup.send("Posted.", ephemeral=True)

    @bot.tree.command(name="update_monthly_info", description="Refresh a club's monthly info board")
    @app_commands.guild_only()
    async def update_monthly_info(interaction: discord.Interaction, club: str):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        row = await clubs.get_club_by_name(db, club)
        if row is None:
            await interaction.followup.send(f"No club named '{club}'.", ephemeral=True)
            return
        ch_id, msg_id = row["monthly_info_channel_id"], row["monthly_info_message_id"]
        if ch_id is None or msg_id is None:
            await interaction.followup.send("Post it first with /post_monthly_info.", ephemeral=True)
            return
        now = _dt.datetime.now(_dt.timezone.utc)
        content = await board_cmd.cmd_monthly_info_content(db, client, club_name=club, now_utc=now)
        channel = bot.get_channel(ch_id)
        try:
            msg = await channel.fetch_message(msg_id)
            await msg.edit(content=content[:1900])
            await interaction.followup.send("Updated.", ephemeral=True)
        except Exception:
            await interaction.followup.send("Could not edit the stored message.", ephemeral=True)

    @bot.tree.command(name="progress_chart", description="Fan progression chart for a club")
    @app_commands.guild_only()
    async def progress_chart(interaction: discord.Interaction, club: str):
        await interaction.response.defer()
        try:
            row = await clubs.get_club_by_name(db, club)
            if row is None:
                await interaction.followup.send(f"No club named '{club}'.")
                return
            series = await history_repo.get_club_history(db, row["id"])
            png = render_progress_chart(series)
            await interaction.followup.send(file=discord.File(io.BytesIO(png), filename="progress.png"))
        except Exception:
            await interaction.followup.send("Could not generate the image.")

    @bot.tree.command(name="member_status", description="Show a member's trainer card")
    @app_commands.guild_only()
    async def member_status(interaction: discord.Interaction, club: str, trainer_name: str):
        await interaction.response.defer()
        try:
            row = await clubs.get_club_by_name(db, club)
            if row is None:
                await interaction.followup.send(f"No club named '{club}'.")
                return
            member = await db.fetchone(
                "SELECT * FROM member WHERE club_id=? AND trainer_name=?", (row["id"], trainer_name))
            if member is None:
                await interaction.followup.send(f"No member named '{trainer_name}' in '{club}'.")
                return
            from hourglass.db import bombs as _bombs
            hist = await db.fetchone(
                "SELECT cumulative_fans, days_behind FROM quota_history WHERE member_id=? "
                "ORDER BY date DESC, id DESC LIMIT 1", (member["id"],))
            gain = hist["cumulative_fans"] if hist else 0
            days_behind = hist["days_behind"] if hist else 0
            bomb = await _bombs.get_active_for_member(db, member["id"])
            bomb_days = bomb["days_remaining"] if bomb else None
            png = render_trainer_card(trainer_name, club, gain, days_behind, bomb_days)
            await interaction.followup.send(file=discord.File(io.BytesIO(png), filename="card.png"))
        except Exception:
            await interaction.followup.send("Could not generate the image.")

    return bot
