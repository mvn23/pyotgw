import asyncio


async def has_been_called_x_times(mocked, x, timeout=10):
    """Wait for more than x calls on mocked object or timeout"""

    async def _wait():
        while mocked.call_count < x:
            await asyncio.sleep(0)

    await asyncio.wait_for(_wait(), timeout)
