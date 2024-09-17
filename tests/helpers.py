"""Helper functions for tests"""

import asyncio
from collections.abc import Callable

from pyotgw.types import OpenThermCommand, OpenThermReport


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


def respond_to_reports(
    cmds: list[OpenThermReport] | None = None, responses: list[str] | None = None
) -> Callable[[OpenThermCommand, str, float | None], str]:
    """
    Respond to PR= commands with test values.
    Override response values by specifying cmds and responses in order.
    """

    if len(cmds) != len(responses):
        raise ValueError(
            "There should be an equal amount of provided cmds and responses"
        )

    if cmds is None:
        cmds = []
    if responses is None:
        responses = []

    default_responses = {
        OpenThermReport.ABOUT: "A=OpenTherm Gateway 5.8",
        OpenThermReport.BUILD: "B=17:52 12-03-2023",
        OpenThermReport.CLOCK_SPEED: "C=4 MHz",
        OpenThermReport.TEMP_SENSOR_FUNCTION: "D=R",
        OpenThermReport.GPIO_MODES: "G=46",
        OpenThermReport.GPIO_STATES: "I=10",
        OpenThermReport.LED_MODES: "L=HWCEMP",
        OpenThermReport.OP_MODE: "M=G",
        OpenThermReport.SETPOINT_OVERRIDE: "O=c17.25",
        OpenThermReport.SMART_PWR_MODE: "P=Medium power",
        OpenThermReport.RESET_CAUSE: "Q=B",
        OpenThermReport.THERMOSTAT_DETECTION_STATE: "R=C",
        OpenThermReport.SETBACK_TEMPERATURE: "S=15.1",
        OpenThermReport.TWEAKS: "T=10",
        OpenThermReport.VREF: "V=6",
        OpenThermReport.DHW: "W=1",
    }

    for cmd, response in zip(cmds, responses):
        if cmd not in default_responses:
            raise ValueError(f"Command {cmd} not found in default responses.")

        default_responses[cmd] = response

    def responder(cmd: OpenThermCommand, value: str, timeout: float = 1) -> str:
        """Respond to command requests"""
        if cmd != OpenThermCommand.REPORT:
            return
        return default_responses[value[0]]

    return responder
