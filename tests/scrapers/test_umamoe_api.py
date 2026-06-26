import pytest

from scrapers.umamoe_api import BASE_URL, UmamoeClient


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
