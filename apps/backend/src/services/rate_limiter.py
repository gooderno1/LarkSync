from __future__ import annotations

import asyncio
import time
import weakref


class AsyncTokenBucket:
    """面向单个事件循环的异步令牌桶。"""

    def __init__(self, rate_per_second: float, capacity: int) -> None:
        self._rate = max(0.01, float(rate_per_second))
        self._capacity = max(1, int(capacity))
        self._tokens = float(self._capacity)
        self._updated_at = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                elapsed = max(0.0, now - self._updated_at)
                self._tokens = min(
                    float(self._capacity), self._tokens + elapsed * self._rate
                )
                self._updated_at = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                delay = (1.0 - self._tokens) / self._rate
            await asyncio.sleep(delay)


_GLOBAL_LIMITERS: weakref.WeakKeyDictionary[
    asyncio.AbstractEventLoop, dict[tuple[float, int], AsyncTokenBucket]
] = weakref.WeakKeyDictionary()


def get_global_rate_limiter(rate_per_second: float, capacity: int) -> AsyncTokenBucket:
    """同一事件循环和参数组合共享一个令牌桶，覆盖所有 FeishuClient。"""
    loop = asyncio.get_running_loop()
    buckets = _GLOBAL_LIMITERS.setdefault(loop, {})
    key = (float(rate_per_second), int(capacity))
    limiter = buckets.get(key)
    if limiter is None:
        limiter = AsyncTokenBucket(*key)
        buckets[key] = limiter
    return limiter
