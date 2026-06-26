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
