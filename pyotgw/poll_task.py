"""Describes a task that polls a specific value."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod, abstractproperty
from typing import TYPE_CHECKING

from . import vars as v

if TYPE_CHECKING:
    from .pyotgw import OpenThermGateway
from .types import OpenThermDataSource

_LOGGER = logging.getLogger(__name__)


class OpenThermPollTask(ABC):
    """
    Describes a task that polls the gateway for certain states.
    Some states aren't being pushed by the gateway, we need to poll
    if we want updates.
    """

    default_values: dict[OpenThermDataSource, dict]
    _task: asyncio.Task | None = None

    def __init__(self, name: str, gateway: OpenThermGateway, interval: float = 10):
        """Initialize the object."""
        self._gateway = gateway
        self._interval: float = interval
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

    @abstractproperty
    def should_run(self) -> bool:
        """Return whether or not we should be actively polling."""
        raise NotImplementedError

    @property
    def is_running(self) -> bool:
        """Return whether or not we are actively polling."""
        return self._task is not None

    @abstractmethod
    async def get_actual_value(self) -> dict[OpenThermDataSource, dict] | None:
        """Get the values from the gateway, return status dict update or None."""
        raise NotImplementedError

    async def _polling_routine(self) -> None:
        """The polling mechanism."""
        _LOGGER.debug(f"{self.name} polling routine started")
        while True:
            update = await self.get_actual_value()
            if update:
                self._gateway.status.submit_full_update(update)
            await asyncio.sleep(self._interval)


class OpenThermGpioStatePollTask(OpenThermPollTask):
    """
    Describes a task that polls GPIO states.
    Some states aren't being pushed by the gateway, we need to poll
    if we want updates.
    """

    default_values: dict[OpenThermDataSource, dict] = {
        OpenThermDataSource.GATEWAY: {
            v.OTGW_GPIO_A_STATE: None,
            v.OTGW_GPIO_B_STATE: None,
        }
    }

    @property
    def should_run(self) -> bool:
        """Return whether or not we should be actively polling."""
        return 0 in (
            self._gateway.status.status[OpenThermDataSource.GATEWAY].get(v.OTGW_GPIO_A),
            self._gateway.status.status[OpenThermDataSource.GATEWAY].get(v.OTGW_GPIO_B),
        )

    async def get_actual_value(self) -> dict[OpenThermDataSource, dict] | None:
        """Get the values from the gateway, return status dict update or None."""
        ret = await self._gateway.get_report(v.OTGW_REPORT_GPIO_STATES)
        if not ret:
            return None

        pios = ret[2:]
        return {
            OpenThermDataSource.GATEWAY: {
                v.OTGW_GPIO_A_STATE: int(pios[0]),
                v.OTGW_GPIO_B_STATE: int(pios[1]),
            }
        }
