from __future__ import annotations

import asyncio
import logging

import aiohttp
from dotenv import dotenv_values

from bot import build_bot
from config.settings import load_settings
from db.database import Database
from scrapers.umamoe_api import UmamoeClient
from utils.rate_limiter import RateLimiter


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings(dotenv_values())  # read config from .env

    db = Database()
    await db.connect(settings.database_url)
    await db.migrate()

    async with aiohttp.ClientSession() as session:
        limiter = RateLimiter(settings.umamoe_rate_per_min, settings.umamoe_rate_burst)
        client = UmamoeClient(session, limiter, api_key=settings.umamoe_api_key)
        bot = build_bot(db, client, settings)
        try:
            await bot.start(settings.discord_token)
        finally:
            await db.close()


if __name__ == "__main__":
    asyncio.run(main())
