# Hourglass — Plan 1: Foundation & API Ingestion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the tested foundation of Hourglass — project scaffold, config loading, a shared async rate limiter, the uma.moe response parser, and a retrying async fetch client — so later plans have reliable, mockable data-access primitives.

**Architecture:** A discord.py monolith (later plans) sits on top of a thin data layer. This plan delivers that data layer in isolation: a pure parser (no I/O, fully unit-testable) and an async fetch client that wraps `aiohttp` behind a shared token-bucket rate limiter with retries. No Discord or DB code yet — those arrive in Plan 2.

**Tech Stack:** Python 3.11+, `aiohttp` (HTTP), `pytest` + `pytest-asyncio` (tests). Later plans add `discord.py`, `asyncpg`, `Pillow`, `plotly`/`kaleido`.

## Global Constraints

- Python **3.11+** (uses `list[int]` / `X | None` builtins, `tomllib` if needed).
- uma.moe endpoint: `https://uma.moe/api/v4/circles`, params `circle_id`, `year`, `month`; header `X-API-Key` (optional, from env `UMAMOE_API_KEY`); request timeout **30s**.
- All uma.moe HTTP calls go through **one shared rate limiter** instance (token bucket, FIFO).
- Parser rules (verbatim): lifetime→monthly via first-`>0` baseline; negative `daily_fans` → 0; a member with 0 on the current day is a leaver → excluded; `monthly[day] = max(0, lifetime[day] - baseline)`.
- Local retries on transient failure: **3 attempts, 10s base delay, ×2 backoff**.
- TDD: write the failing test first, watch it fail, implement minimally, watch it pass, commit.
- All temp/experiment files (if any) go under the session scratchpad, never in the repo.

---

### Task 1: Project scaffold & test harness

**Files:**
- Create: `requirements.txt`
- Create: `pyproject.toml`
- Create: `hourglass/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/test_smoke.py`
- Create: `.gitignore`

**Interfaces:**
- Consumes: nothing.
- Produces: an importable `hourglass` package and a working `pytest` command for all later tasks.

- [ ] **Step 1: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.venv/
venv/
.env
*.png
```

- [ ] **Step 2: Create `requirements.txt`**

```text
aiohttp>=3.9
pytest>=8.0
pytest-asyncio>=0.23
```

- [ ] **Step 3: Create `pyproject.toml` (pytest config)**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 4: Create empty package markers**

`hourglass/__init__.py`:
```python
```

`tests/__init__.py`:
```python
```

- [ ] **Step 5: Write the smoke test**

`tests/test_smoke.py`:
```python
import hourglass


def test_package_imports():
    assert hourglass is not None
```

- [ ] **Step 6: Install deps and run the smoke test**

Run:
```bash
python -m pip install -r requirements.txt
python -m pytest tests/test_smoke.py -v
```
Expected: 1 passed.

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt pyproject.toml hourglass/__init__.py tests/__init__.py tests/test_smoke.py
git commit -m "chore: scaffold hourglass package and pytest harness"
```

---

### Task 2: Config / settings loader

**Files:**
- Create: `hourglass/config/__init__.py`
- Create: `hourglass/config/settings.py`
- Test: `tests/config/__init__.py`
- Test: `tests/config/test_settings.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `Settings` dataclass + `load_settings(env: Mapping[str, str]) -> Settings` with fields:
  `discord_token: str`, `database_url: str`, `umamoe_api_key: str | None`,
  `umamoe_rate_per_min: float` (default 20), `umamoe_rate_burst: int` (default 5),
  `poll_time_utc: str` (default `"15:20"`), `manager_role_id: int | None`,
  `emoji_promote: str` (default `"⬆️"`), `emoji_relegate: str` (default `"⬇️"`).

- [ ] **Step 1: Create package marker**

`hourglass/config/__init__.py`:
```python
```

`tests/config/__init__.py`:
```python
```

- [ ] **Step 2: Write the failing test**

`tests/config/test_settings.py`:
```python
import pytest

from hourglass.config.settings import Settings, load_settings


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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/config/test_settings.py -v`
Expected: FAIL with `ModuleNotFoundError: hourglass.config.settings`.

- [ ] **Step 4: Write minimal implementation**

`hourglass/config/settings.py`:
```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/config/test_settings.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add hourglass/config tests/config
git commit -m "feat: add settings loader"
```

---

### Task 3: Shared async token-bucket rate limiter

**Files:**
- Create: `hourglass/utils/__init__.py`
- Create: `hourglass/utils/rate_limiter.py`
- Test: `tests/utils/__init__.py`
- Test: `tests/utils/test_rate_limiter.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `RateLimiter(rate_per_min: float, burst: int, *, clock=time.monotonic, sleep=asyncio.sleep)`
  with `async def acquire() -> None`. Injectable `clock`/`sleep` for deterministic tests.

- [ ] **Step 1: Create package markers**

`hourglass/utils/__init__.py`:
```python
```

`tests/utils/__init__.py`:
```python
```

- [ ] **Step 2: Write the failing tests**

`tests/utils/test_rate_limiter.py`:
```python
import pytest

from hourglass.utils.rate_limiter import RateLimiter


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def time(self):
        return self.t


@pytest.mark.asyncio
async def test_burst_does_not_sleep():
    clock = FakeClock()
    slept = []

    async def fake_sleep(s):
        slept.append(s)

    rl = RateLimiter(rate_per_min=60, burst=3, clock=clock.time, sleep=fake_sleep)
    for _ in range(3):
        await rl.acquire()
    assert slept == []  # 3 tokens available up front


@pytest.mark.asyncio
async def test_fourth_acquire_waits_for_refill():
    clock = FakeClock()
    slept = []

    async def fake_sleep(s):
        slept.append(s)
        clock.t += s  # advance time as if we slept

    # 60/min => 1 token/sec. burst=1 => second acquire must wait ~1s.
    rl = RateLimiter(rate_per_min=60, burst=1, clock=clock.time, sleep=fake_sleep)
    await rl.acquire()
    await rl.acquire()
    assert len(slept) == 1
    assert slept[0] == pytest.approx(1.0, abs=0.01)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/utils/test_rate_limiter.py -v`
Expected: FAIL with `ModuleNotFoundError: hourglass.utils.rate_limiter`.

- [ ] **Step 4: Write minimal implementation**

`hourglass/utils/rate_limiter.py`:
```python
from __future__ import annotations

import asyncio
import time
from typing import Awaitable, Callable


class RateLimiter:
    """Async token bucket. Holding the lock across the wait gives FIFO fairness."""

    def __init__(
        self,
        rate_per_min: float,
        burst: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.rate_per_sec = max(float(rate_per_min), 1.0) / 60.0
        self.capacity = float(max(int(burst), 1))
        self._tokens = self.capacity
        self._clock = clock
        self._sleep = sleep
        self._updated = clock()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._clock()
        elapsed = now - self._updated
        if elapsed > 0:
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate_per_sec)
            self._updated = now

    async def acquire(self) -> None:
        async with self._lock:
            self._refill()
            if self._tokens < 1.0:
                wait = (1.0 - self._tokens) / self.rate_per_sec
                await self._sleep(wait)
                self._refill()
            self._tokens -= 1.0
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/utils/test_rate_limiter.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add hourglass/utils/__init__.py hourglass/utils/rate_limiter.py tests/utils
git commit -m "feat: add shared async token-bucket rate limiter"
```

---

### Task 4: uma.moe response parser (pure, no I/O)

**Files:**
- Create: `hourglass/scrapers/__init__.py`
- Create: `hourglass/scrapers/parser.py`
- Test: `tests/scrapers/__init__.py`
- Test: `tests/scrapers/test_parser.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `@dataclass MemberGain` with fields `viewer_id: str`, `trainer_name: str`,
    `monthly_fans: list[int]`, `gain: int`, `join_day: int`.
  - `parse_circle(payload: dict, current_day: int) -> list[MemberGain]` — raises `ValueError`
    if `members` key absent.

- [ ] **Step 1: Create package markers**

`hourglass/scrapers/__init__.py`:
```python
```

`tests/scrapers/__init__.py`:
```python
```

- [ ] **Step 2: Write the failing tests**

`tests/scrapers/test_parser.py`:
```python
import pytest

from hourglass.scrapers.parser import MemberGain, parse_circle


def _payload(members):
    return {"circle": {}, "members": members}


def test_normal_member_gain_is_last_minus_baseline():
    # joined before this month: baseline = day1 value 100; gain = 250 - 100
    payload = _payload([
        {"viewer_id": 1, "trainer_name": "A", "daily_fans": [100, 180, 250]},
    ])
    out = parse_circle(payload, current_day=3)
    assert len(out) == 1
    g = out[0]
    assert isinstance(g, MemberGain)
    assert g.viewer_id == "1"
    assert g.join_day == 1
    assert g.gain == 150
    assert g.monthly_fans == [0, 80, 150]


def test_mid_month_joiner_baseline_is_first_nonzero():
    # first non-zero on day 3 => join_day 3, baseline 500
    payload = _payload([
        {"viewer_id": 2, "trainer_name": "B", "daily_fans": [0, 0, 500, 700]},
    ])
    out = parse_circle(payload, current_day=4)
    g = out[0]
    assert g.join_day == 3
    assert g.monthly_fans == [0, 0, 0, 200]
    assert g.gain == 200


def test_negative_transfer_marker_treated_as_zero():
    payload = _payload([
        {"viewer_id": 3, "trainer_name": "C", "daily_fans": [-5, 100, 240]},
    ])
    out = parse_circle(payload, current_day=3)
    g = out[0]
    assert g.join_day == 2  # first >0 is day 2
    assert g.monthly_fans == [0, 0, 140]
    assert g.gain == 140


def test_leaver_with_zero_on_current_day_is_excluded():
    payload = _payload([
        {"viewer_id": 4, "trainer_name": "D", "daily_fans": [100, 200, 0]},
    ])
    out = parse_circle(payload, current_day=3)
    assert out == []


def test_current_day_truncates_future_days():
    payload = _payload([
        {"viewer_id": 5, "trainer_name": "E", "daily_fans": [100, 150, 999, 999]},
    ])
    out = parse_circle(payload, current_day=2)
    g = out[0]
    assert g.monthly_fans == [0, 50]
    assert g.gain == 50


def test_member_missing_fields_skipped():
    payload = _payload([
        {"viewer_id": 6, "daily_fans": [100, 200]},        # no name
        {"trainer_name": "G", "daily_fans": [100, 200]},   # no viewer_id
    ])
    assert parse_circle(payload, current_day=2) == []


def test_missing_members_key_raises():
    with pytest.raises(ValueError):
        parse_circle({"circle": {}}, current_day=2)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest tests/scrapers/test_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: hourglass.scrapers.parser`.

- [ ] **Step 4: Write minimal implementation**

`hourglass/scrapers/parser.py`:
```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MemberGain:
    viewer_id: str
    trainer_name: str
    monthly_fans: list[int]
    gain: int
    join_day: int


def _clean_lifetime(raw: list) -> list[int]:
    out = []
    for v in raw:
        if isinstance(v, (int, float)):
            iv = int(v)
            out.append(iv if iv > 0 else 0)  # negatives / transfer markers -> 0
        else:
            out.append(0)
    return out


def parse_circle(payload: dict, current_day: int) -> list[MemberGain]:
    members = payload.get("members")
    if members is None:
        raise ValueError("response missing 'members'")

    result: list[MemberGain] = []
    for m in members:
        viewer_id = m.get("viewer_id")
        name = m.get("trainer_name")
        if viewer_id is None or name is None:
            continue

        window = _clean_lifetime(m.get("daily_fans") or [])[:current_day]
        if not window or window[-1] <= 0:  # leaver: absent / 0 on current day
            continue

        join_day = 1
        baseline = 0
        for idx, fans in enumerate(window, start=1):
            if fans > 0:
                join_day = idx
                baseline = fans
                break

        monthly = [max(0, v - baseline) if v > 0 else 0 for v in window]
        result.append(
            MemberGain(
                viewer_id=str(viewer_id),
                trainer_name=str(name),
                monthly_fans=monthly,
                gain=monthly[-1],
                join_day=join_day,
            )
        )
    return result
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/scrapers/test_parser.py -v`
Expected: 7 passed.

- [ ] **Step 6: Commit**

```bash
git add hourglass/scrapers/__init__.py hourglass/scrapers/parser.py tests/scrapers
git commit -m "feat: add uma.moe circle response parser"
```

---

### Task 5: uma.moe async fetch client (aiohttp + limiter + retries)

**Files:**
- Create: `hourglass/scrapers/umamoe_api.py`
- Test: `tests/scrapers/test_umamoe_api.py`

**Interfaces:**
- Consumes: `RateLimiter` (Task 3) — `async def acquire() -> None`.
- Produces:
  - `class StaleDataError(Exception)`.
  - `class UmamoeClient(session, rate_limiter, *, api_key=None, max_retries=3, base_delay=10.0, sleep=asyncio.sleep)`.
  - `async def fetch_circle(circle_id, year, month) -> dict | None` — returns parsed JSON on
    HTTP 200; `None` after exhausting retries on non-200/network errors. Calls
    `rate_limiter.acquire()` before each attempt. Sends `X-API-Key` header when `api_key` set.
    Retries transient failures `max_retries` times with `base_delay * 2**attempt` backoff via
    the injected `sleep`.
  - `BASE_URL = "https://uma.moe/api/v4/circles"`.

  Note: `session` is any object exposing `get(url, params=, headers=, timeout=)` as an async
  context manager whose value has `.status` (int) and an async `.json()` — real use passes an
  `aiohttp.ClientSession`; tests pass a fake. Day-1 / freshness / JST orchestration is built on
  top of this client in Plan 2 (the tracker), where calendar context lives.

- [ ] **Step 1: Write the failing tests**

`tests/scrapers/test_umamoe_api.py`:
```python
import pytest

from hourglass.scrapers.umamoe_api import BASE_URL, UmamoeClient


class FakeResponse:
    def __init__(self, status, payload):
        self.status = status
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def json(self):
        return self._payload


class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": params, "headers": headers})
        return self._responses.pop(0)


class FakeLimiter:
    def __init__(self):
        self.acquired = 0

    async def acquire(self):
        self.acquired += 1


@pytest.mark.asyncio
async def test_fetch_circle_success_returns_payload_and_rate_limits():
    payload = {"members": [], "circle": {}}
    session = FakeSession([FakeResponse(200, payload)])
    limiter = FakeLimiter()
    client = UmamoeClient(session, limiter, api_key="K")

    out = await client.fetch_circle(860280110, 2026, 6)

    assert out == payload
    assert limiter.acquired == 1
    call = session.calls[0]
    assert call["url"] == BASE_URL
    assert call["params"] == {"circle_id": 860280110, "year": 2026, "month": 6}
    assert call["headers"]["X-API-Key"] == "K"


@pytest.mark.asyncio
async def test_fetch_circle_no_api_key_omits_header():
    session = FakeSession([FakeResponse(200, {"members": []})])
    client = UmamoeClient(session, FakeLimiter())
    await client.fetch_circle(1, 2026, 6)
    assert "X-API-Key" not in session.calls[0]["headers"]


@pytest.mark.asyncio
async def test_fetch_circle_retries_then_gives_up_on_non_200():
    slept = []

    async def fake_sleep(s):
        slept.append(s)

    session = FakeSession([FakeResponse(500, {}), FakeResponse(500, {}), FakeResponse(500, {})])
    limiter = FakeLimiter()
    client = UmamoeClient(
        session, limiter, max_retries=3, base_delay=10.0, sleep=fake_sleep
    )

    out = await client.fetch_circle(1, 2026, 6)

    assert out is None
    assert limiter.acquired == 3            # one acquire per attempt
    assert slept == [10.0, 20.0]            # backoff between the 3 attempts (no sleep after last)


@pytest.mark.asyncio
async def test_fetch_circle_recovers_on_second_attempt():
    async def fake_sleep(s):
        pass

    payload = {"members": [{"viewer_id": 1, "trainer_name": "A", "daily_fans": [1]}]}
    session = FakeSession([FakeResponse(503, {}), FakeResponse(200, payload)])
    client = UmamoeClient(session, FakeLimiter(), max_retries=3, sleep=fake_sleep)

    out = await client.fetch_circle(1, 2026, 6)
    assert out == payload
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/scrapers/test_umamoe_api.py -v`
Expected: FAIL with `ModuleNotFoundError: hourglass.scrapers.umamoe_api`.

- [ ] **Step 3: Write minimal implementation**

`hourglass/scrapers/umamoe_api.py`:
```python
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

logger = logging.getLogger(__name__)

BASE_URL = "https://uma.moe/api/v4/circles"
TIMEOUT_SECONDS = 30


class StaleDataError(Exception):
    """Raised when fetched data is not fresh and the club should be re-queued later."""


class UmamoeClient:
    def __init__(
        self,
        session,
        rate_limiter,
        *,
        api_key: str | None = None,
        max_retries: int = 3,
        base_delay: float = 10.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._session = session
        self._limiter = rate_limiter
        self._api_key = api_key
        self._max_retries = max(int(max_retries), 1)
        self._base_delay = float(base_delay)
        self._sleep = sleep

    def _headers(self) -> dict:
        headers = {"Accept-Encoding": "gzip, deflate"}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    async def fetch_circle(self, circle_id, year: int, month: int) -> dict | None:
        params = {"circle_id": circle_id, "year": year, "month": month}
        for attempt in range(self._max_retries):
            await self._limiter.acquire()
            try:
                async with self._session.get(
                    BASE_URL,
                    params=params,
                    headers=self._headers(),
                    timeout=TIMEOUT_SECONDS,
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    logger.warning(
                        "uma.moe non-200 for circle %s: %s (attempt %d)",
                        circle_id,
                        resp.status,
                        attempt + 1,
                    )
            except Exception as exc:  # network/timeout
                logger.warning(
                    "uma.moe request error for circle %s: %r (attempt %d)",
                    circle_id,
                    exc,
                    attempt + 1,
                )

            if attempt < self._max_retries - 1:
                await self._sleep(self._base_delay * (2 ** attempt))

        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/scrapers/test_umamoe_api.py -v`
Expected: 4 passed.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest -v`
Expected: all tests from Tasks 1–5 pass.

- [ ] **Step 6: Commit**

```bash
git add hourglass/scrapers/umamoe_api.py tests/scrapers/test_umamoe_api.py
git commit -m "feat: add retrying uma.moe async fetch client"
```

---

## Plan 1 deliverable

A tested data layer: `Settings` loader, shared `RateLimiter`, pure `parse_circle`, and a
retrying `UmamoeClient` — all unit-tested with mocks, no Discord/DB yet. Plan 2 builds the DB
models, the tracker poll flow (including Day-1/freshness/JST orchestration on top of
`UmamoeClient`), quota calculator, scheduler, and the first slash commands.

## Self-review notes

- **Spec coverage (this plan's slice):** API endpoint/headers/timeout (Task 5), shared
  rate limiter (Task 3), parser rules incl. baseline/negatives/leaver/mid-month/truncation
  (Task 4), retries 3×/10s/×2 (Task 5), config incl. tier emojis (Task 2). Day-1, freshness,
  JST rollover, DB, and all tier/quota/bomb logic are explicitly deferred to plans 2–5.
- **No placeholders:** every code/test step is complete and runnable.
- **Type consistency:** `RateLimiter.acquire`, `parse_circle` signature, and
  `UmamoeClient.fetch_circle` signature match between their definitions and their test/consumer
  usages; `MemberGain` field names are used identically in tests.
