from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    discord_token: str
    database_url: str
    umamoe_api_key: str | None
    umamoe_rate_per_min: float
    umamoe_rate_burst: int
    poll_time_utc: str
    manager_role_id: int | None
    emoji_promote: str
    emoji_relegate: str


def load_settings(env: Mapping[str, str]) -> Settings:
    manager = env.get("MANAGER_ROLE_ID")
    return Settings(
        discord_token=env["DISCORD_TOKEN"],
        database_url=env["DATABASE_URL"],
        umamoe_api_key=env.get("UMAMOE_API_KEY"),
        umamoe_rate_per_min=float(env.get("UMAMOE_RATE_PER_MIN", "20")),
        umamoe_rate_burst=int(env.get("UMAMOE_RATE_BURST", "5")),
        poll_time_utc=env.get("POLL_TIME_UTC", "15:20"),
        manager_role_id=int(manager) if manager else None,
        emoji_promote=env.get("EMOJI_PROMOTE", "⬆️"),
        emoji_relegate=env.get("EMOJI_RELEGATE", "⬇️"),
    )
