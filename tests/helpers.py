"""Helper functions for tests"""

import asyncio


async def called_x_times(mocked, x, timeout=10):
    """Wait for x or more calls on mocked object or timeout"""

    async def _wait():
        while mocked.call_count < x:
            await asyncio.sleep(0)

    await asyncio.wait_for(_wait(), timeout)


async def called_once(mocked, timeout=10):
    """Wait for at least 1 call on mocked object or timeout"""
    await called_x_times(mocked, 1, timeout)


async def let_queue_drain(queue, timeout=10):
    """Wait for queue to become empty or timeout"""

    async def _wait():
        while not queue.empty():
            await asyncio.sleep(0)

    await asyncio.wait_for(_wait(), timeout)
