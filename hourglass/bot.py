from __future__ import annotations

import datetime as _dt
import logging

import discord
from discord import app_commands
from discord.ext import commands, tasks

from hourglass.commands import clubs_cmd, ops_cmd
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

    @tasks.loop(minutes=1)
    async def scheduler_loop():
        now = _dt.datetime.now(_dt.timezone.utc)
        await run_due_clubs(db, client, now, _send, last_runs)

    @bot.event
    async def on_ready():
        await bot.tree.sync()
        if not scheduler_loop.is_running():
            scheduler_loop.start()
        logger.info("Hourglass logged in as %s", bot.user)

    @bot.tree.command(name="list_clubs", description="List tracked clubs")
    async def list_clubs(interaction: discord.Interaction):
        await interaction.response.send_message(await clubs_cmd.cmd_list_clubs(db))

    @bot.tree.command(name="add_club", description="Register a club for tracking")
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
    async def set_report_channel(
        interaction: discord.Interaction, club: str, channel: discord.TextChannel
    ):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        msg = await ops_cmd.cmd_set_report_channel(db, club_name=club, channel_id=channel.id)
        await interaction.response.send_message(msg)

    @bot.tree.command(name="quota", description="Set a club's daily quota (from today)")
    async def quota(interaction: discord.Interaction, club: str, amount: int):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        today = _dt.datetime.now(_dt.timezone.utc).date().isoformat()
        msg = await ops_cmd.cmd_set_quota(db, club_name=club, amount=amount, on_date=today)
        await interaction.response.send_message(msg)

    @bot.tree.command(name="force_check", description="Run a club's check now")
    async def force_check(interaction: discord.Interaction, club: str):
        if not _is_manager(interaction):
            await interaction.response.send_message("You lack permission.", ephemeral=True)
            return
        await interaction.response.defer()
        now = _dt.datetime.now(_dt.timezone.utc)
        msg = await ops_cmd.cmd_force_check(db, client, club_name=club, now_utc=now, send=_send)
        await interaction.followup.send(msg[:1900])

    return bot
