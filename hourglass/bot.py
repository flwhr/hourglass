from __future__ import annotations

import datetime as _dt
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from hourglass.commands import clubs_cmd, ops_cmd, links_cmd
from hourglass.services.scheduler import run_due_clubs
from hourglass.utils.permissions import user_is_manager

logger = logging.getLogger(__name__)


def build_bot(db, client, settings) -> commands.Bot:
    intents = discord.Intents.default()
    bot = commands.Bot(command_prefix="!", intents=intents)
    last_runs: dict[int, _dt.date] = {}

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
        from hourglass.db import clubs as _clubs
        row = await _clubs.get_club_by_name(db, club)
        if row is None:
            await interaction.response.send_message(f"No club named '{club}'.")
            return
        await _clubs.update_club(db, row["id"], alert_channel_id=channel.id)
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

    @bot.tree.command(name="my_status", description="Show your linked trainer's bomb status")
    @app_commands.guild_only()
    async def my_status(interaction: discord.Interaction):
        await interaction.response.send_message(
            "Use /bomb_status <club> for now.", ephemeral=True)

    @bot.tree.command(name="bomb_status", description="List active bombs in a club")
    @app_commands.guild_only()
    async def bomb_status(interaction: discord.Interaction, club: str):
        await interaction.response.send_message(await links_cmd.cmd_bomb_status(db, club_name=club))

    return bot
