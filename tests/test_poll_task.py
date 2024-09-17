"""Tests for pyotgw/poll_tasks.py"""

from unittest.mock import AsyncMock, call

import pytest

from pyotgw.poll_task import OpenThermPollTask, OpenThermPollTaskName
from pyotgw.pyotgw import OpenThermGateway
from pyotgw.types import OpenThermDataSource, OpenThermReport
import pyotgw.vars as v

from .helpers import called_x_times

TASK_TEST_PARAMETERS = ("task_name",)
TASK_TEST_VALUES = [
    (OpenThermPollTaskName.GPIO_STATE,),
    (OpenThermPollTaskName.SMART_POWER_MODE,),
]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    TASK_TEST_PARAMETERS,
    TASK_TEST_VALUES,
)
async def test_init(pygw: OpenThermGateway, task_name: str) -> None:
    """Test object initialization."""
    task = pygw._poll_tasks[task_name]
    assert isinstance(task, OpenThermPollTask)


@pytest.mark.asyncio
async def test_gpio_start_stop(pygw: OpenThermGateway) -> None:
    """Test task.start() and task.stop()"""
    task = pygw._poll_tasks[OpenThermPollTaskName.GPIO_STATE]
    assert not task.is_running
    pygw.status.submit_partial_update(OpenThermDataSource.GATEWAY, {v.OTGW_GPIO_A: 0})
    task.start()
    assert task.is_running
    await task.stop()
    assert not task.is_running


@pytest.mark.asyncio
async def test_gpio_start_or_stop_as_needed(pygw: OpenThermGateway) -> None:
    """Test task.start_or_stop_as_needed()"""
    task = pygw._poll_tasks[OpenThermPollTaskName.GPIO_STATE]
    assert task.is_running is False
    await task.start_or_stop_as_needed()
    assert task.is_running is False
    pygw.status.submit_partial_update(OpenThermDataSource.GATEWAY, {v.OTGW_GPIO_A: 0})
    await task.start_or_stop_as_needed()
    assert task.is_running is True
    await task.start_or_stop_as_needed()
    assert task.is_running is True
    pygw.status.submit_partial_update(OpenThermDataSource.GATEWAY, {v.OTGW_GPIO_A: 1})
    await task.start_or_stop_as_needed()
    assert task.is_running is False


def test_gpio_should_run(pygw: OpenThermGateway) -> None:
    """Test task.should_run()"""
    task = pygw._poll_tasks[OpenThermPollTaskName.GPIO_STATE]
    assert task.should_run is False
    pygw.status.submit_partial_update(OpenThermDataSource.GATEWAY, {v.OTGW_GPIO_A: 0})
    assert task.should_run is True


@pytest.mark.asyncio
async def test_gpio_is_running(pygw: OpenThermGateway) -> None:
    """Test task.should_run()"""
    task = pygw._poll_tasks[OpenThermPollTaskName.GPIO_STATE]
    assert task.is_running is False
    pygw.status.submit_partial_update(OpenThermDataSource.GATEWAY, {v.OTGW_GPIO_A: 0})
    task.start()
    assert task.is_running is True


@pytest.mark.asyncio
async def test_gpio_polling_routing(pygw: OpenThermGateway) -> None:
    """Test task._polling_routing()"""
    pygw.get_report = AsyncMock()
    task = pygw._poll_tasks[OpenThermPollTaskName.GPIO_STATE]
    task._interval = 0.01
    pygw.status.submit_partial_update(OpenThermDataSource.GATEWAY, {v.OTGW_GPIO_A: 0})
    task.start()
    await called_x_times(pygw.get_report, 2)
    pygw.get_report.assert_has_awaits(
        [
            call(OpenThermReport.GPIO_STATES),
            call(OpenThermReport.GPIO_STATES),
        ]
    )
    await task.stop()


@pytest.mark.asyncio
async def test_smart_pwr_start_stop(pygw: OpenThermGateway) -> None:
    """Test task.start() and task.stop()"""
    task = pygw._poll_tasks[OpenThermPollTaskName.SMART_POWER_MODE]
    assert task.is_running is False
    task.start()
    assert task.is_running is True
    await task.stop()
    assert task.is_running is False


@pytest.mark.asyncio
async def test_smart_pwr_start_or_stop_as_needed(pygw: OpenThermGateway) -> None:
    """Test task.start_or_stop_as_needed()"""
    task = pygw._poll_tasks[OpenThermPollTaskName.SMART_POWER_MODE]
    assert task.is_running is False
    await task.start_or_stop_as_needed()
    assert task.is_running is True
    # smart power task should never be stopped by start_or_stop_as_needed()


def test_smart_pwr_should_run(pygw: OpenThermGateway) -> None:
    """Test task.should_run()"""
    task = pygw._poll_tasks[OpenThermPollTaskName.SMART_POWER_MODE]
    assert task.should_run is True


@pytest.mark.asyncio
async def test_smart_pwr_is_running(pygw: OpenThermGateway) -> None:
    """Test task.is_running()"""
    task = pygw._poll_tasks[OpenThermPollTaskName.SMART_POWER_MODE]
    assert task.is_running is False
    task.start()
    assert task.is_running is True


@pytest.mark.asyncio
async def test_smart_pwr_polling_routing(pygw: OpenThermGateway) -> None:
    """Test task._polling_routing()"""
    pygw.get_report = AsyncMock()
    task = pygw._poll_tasks[OpenThermPollTaskName.SMART_POWER_MODE]
    task._interval = 0.01
    task.start()
    await called_x_times(pygw.get_report, 2)
    pygw.get_report.assert_has_awaits(
        [
            call(OpenThermReport.SMART_PWR_MODE),
            call(OpenThermReport.SMART_PWR_MODE),
        ]
    )
    await task.stop()
