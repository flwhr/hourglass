from __future__ import annotations

import aiosqlite

from db.schema import SCHEMA


class Database:
    def __init__(self) -> None:
        self._conn: aiosqlite.Connection | None = None

    async def connect(self, path: str) -> None:
        self._conn = await aiosqlite.connect(path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys=ON")
        await self._conn.commit()

    async def migrate(self) -> None:
        assert self._conn is not None
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def execute(self, sql: str, params: tuple = ()) -> int:
        assert self._conn is not None
        cursor = await self._conn.execute(sql, params)
        await self._conn.commit()
        return cursor.lastrowid

    async def fetchone(self, sql: str, params: tuple = ()):
        assert self._conn is not None
        cursor = await self._conn.execute(sql, params)
        return await cursor.fetchone()

    async def fetchall(self, sql: str, params: tuple = ()) -> list:
        assert self._conn is not None
        cursor = await self._conn.execute(sql, params)
        return list(await cursor.fetchall())

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
