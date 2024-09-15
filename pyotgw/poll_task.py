"""Describes a task that polls a specific value."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from enum import StrEnum
import logging
from typing import TYPE_CHECKING

from . import vars as v

if TYPE_CHECKING:
    from .pyotgw import OpenThermGateway
from .types import OpenThermDataSource, OpenThermReport

_LOGGER = logging.getLogger(__name__)


class OpenThermPollTaskName(StrEnum):
    """Poll task names."""

    GPIO_STATE = "gpio_state"


def get_all_poll_tasks(gateway: OpenThermGateway):
    """Get all poll tasks for a gateway."""
    return {
        OpenThermPollTaskName.GPIO_STATE: OpenThermPollTask(
            OpenThermPollTaskName.GPIO_STATE,
            gateway,
            OpenThermReport.GPIO_STATES,
            {
                OpenThermDataSource.GATEWAY: {
                    v.OTGW_GPIO_A_STATE: 0,
                    v.OTGW_GPIO_B_STATE: 0,
                },
            },
            (
                lambda: 0
                in (
                    gateway.status.status[OpenThermDataSource.GATEWAY].get(
                        v.OTGW_GPIO_A
                    ),
                    gateway.status.status[OpenThermDataSource.GATEWAY].get(
                        v.OTGW_GPIO_B
                    ),
                )
            ),
        )
    }


class OpenThermPollTask:
    """
    Describes a task that polls the gateway for certain reports.
    Some states aren't being pushed by the gateway, we need to poll
    the report method if we want updates.
    """

    _task: asyncio.Task | None = None

    def __init__(
        self,
        name: str,
        gateway: OpenThermGateway,
        report_type: OpenThermReport,
        default_values: dict[OpenThermDataSource, dict],
        run_condition: Callable[[], bool],
        interval: float = 10,
    ) -> None:
        """Initialize the object."""
        self._gateway = gateway
        self._interval = interval
        self._report_type = report_type
        self._run_condition = run_condition
        self.default_values = default_values
        self.name = name

    def start(self) -> None:
        """Start polling if necessary."""
        if self.should_run:
            self._task = asyncio.get_running_loop().create_task(self._polling_routine())

    async def stop(self) -> None:
        """Stop polling if we are active."""
        if self.is_running:
            _LOGGER.debug(f"Stopping {self.name} polling routine")
            self._task.cancel()

            try:
                await self._task
            except asyncio.CancelledError:
                self._gateway.status.submit_full_update(self.default_values)
                _LOGGER.debug(f"{self.name} polling routine stopped")
                self._task = None

    async def start_or_stop_as_needed(self) -> None:
        """Start or stop the task as needed."""
        if self.should_run and not self.is_running:
            self.start()
        elif self.is_running and not self.should_run:
            await self.stop()

    @property
    def should_run(self) -> bool:
        """Return whether or not we should be actively polling."""
        return self._run_condition()

    @property
    def is_running(self) -> bool:
        """Return whether or not we are actively polling."""
        return self._task is not None

    async def _polling_routine(self) -> None:
        """The polling mechanism."""
        _LOGGER.debug(f"{self.name} polling routine started")
        while True:
            await self._gateway.get_report(self._report_type)
            await asyncio.sleep(self._interval)
