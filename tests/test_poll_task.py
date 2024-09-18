"""Tests for pyotgw/poll_tasks.py"""

import asyncio
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, call

import pytest

from pyotgw.poll_task import OpenThermPollTask, OpenThermPollTaskName
from pyotgw.pyotgw import OpenThermGateway
from pyotgw.types import OpenThermDataSource, OpenThermReport, OpenThermResetCause
import pyotgw.vars as v

from .helpers import called_once, called_x_times


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task_name",),
    [(task_name,) for task_name in OpenThermPollTaskName],
)
async def test_init(pygw: OpenThermGateway, task_name: OpenThermPollTaskName) -> None:
    """Test object initialization."""
    task = pygw._poll_tasks[task_name]
    assert isinstance(task, OpenThermPollTask)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task_name", "enable_start_condition_func"),
    [
        (
            OpenThermPollTaskName.ABOUT,
            None,
        ),
        (
            OpenThermPollTaskName.BUILD,
            None,
        ),
        (
            OpenThermPollTaskName.CLOCK_SPEED,
            None,
        ),
        (
            OpenThermPollTaskName.GPIO_STATE,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_GPIO_A: 0,
                        }
                    }
                )
            ),
        ),
        (
            OpenThermPollTaskName.RESET_CAUSE,
            None,
        ),
        (
            OpenThermPollTaskName.SMART_POWER_MODE,
            None,
        ),
    ],
)
async def test_task_start_stop(
    pygw: OpenThermGateway,
    task_name: OpenThermPollTaskName,
    enable_start_condition_func: Callable[[OpenThermGateway], Any] | None,
) -> None:
    """Test task.start() and task.stop()"""
    task = pygw._poll_tasks[task_name]
    assert not task.is_running
    if enable_start_condition_func is not None:
        enable_start_condition_func(pygw)
    task.start()
    assert task.is_running
    await task.stop()
    assert not task.is_running


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task_name", "disable_start_condition_func", "enable_start_condition_func"),
    [
        (
            OpenThermPollTaskName.ABOUT,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_ABOUT: "OpenTherm Gateway 5.8",
                        },
                    }
                )
            ),
            None,
        ),
        (
            OpenThermPollTaskName.BUILD,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_BUILD: "2021-12-23 16:23",
                        },
                    }
                )
            ),
            None,
        ),
        (
            OpenThermPollTaskName.CLOCK_SPEED,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_CLOCKMHZ: "4 MHz",
                        },
                    }
                )
            ),
            None,
        ),
        (
            OpenThermPollTaskName.GPIO_STATE,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_GPIO_A: 1,
                        },
                    }
                )
            ),
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_GPIO_A: 0,
                        },
                    }
                )
            ),
        ),
        (
            OpenThermPollTaskName.RESET_CAUSE,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_RST_CAUSE: OpenThermResetCause.BROWNOUT,
                        },
                    }
                )
            ),
            None,
        ),
        (
            OpenThermPollTaskName.SMART_POWER_MODE,
            None,
            None,
        ),
    ],
)
async def test_start_or_stop_as_needed(
    pygw: OpenThermGateway,
    task_name: OpenThermPollTaskName,
    disable_start_condition_func: Callable[[OpenThermGateway], Any] | None,
    enable_start_condition_func: Callable[[OpenThermGateway], Any] | None,
) -> None:
    """Test task.start_or_stop_as_needed()"""
    task = pygw._poll_tasks[task_name]
    assert task.is_running is False

    if enable_start_condition_func is not None:
        await task.start_or_stop_as_needed()
        assert task.is_running is False
        enable_start_condition_func(pygw)

    await task.start_or_stop_as_needed()
    assert task.is_running is True
    await task.start_or_stop_as_needed()
    assert task.is_running is True

    if disable_start_condition_func is not None:
        disable_start_condition_func(pygw)
        await task.start_or_stop_as_needed()
        assert task.is_running is False


@pytest.mark.parametrize(
    ("task_name", "enable_start_condition_func"),
    [
        (
            OpenThermPollTaskName.ABOUT,
            None,
        ),
        (
            OpenThermPollTaskName.BUILD,
            None,
        ),
        (
            OpenThermPollTaskName.CLOCK_SPEED,
            None,
        ),
        (
            OpenThermPollTaskName.GPIO_STATE,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_GPIO_A: 0,
                        }
                    }
                )
            ),
        ),
        (
            OpenThermPollTaskName.RESET_CAUSE,
            None,
        ),
        (
            OpenThermPollTaskName.SMART_POWER_MODE,
            None,
        ),
    ],
)
def test_should_run(
    pygw: OpenThermGateway,
    task_name: OpenThermPollTaskName,
    enable_start_condition_func: Callable[[OpenThermGateway], Any],
) -> None:
    """Test task.should_run()"""
    task = pygw._poll_tasks[task_name]
    if enable_start_condition_func is not None:
        assert task.should_run is False
        enable_start_condition_func(pygw)
    assert task.should_run is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("task_name", "enable_start_condition_func"),
    [
        (
            OpenThermPollTaskName.ABOUT,
            None,
        ),
        (
            OpenThermPollTaskName.BUILD,
            None,
        ),
        (
            OpenThermPollTaskName.CLOCK_SPEED,
            None,
        ),
        (
            OpenThermPollTaskName.GPIO_STATE,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_GPIO_A: 0,
                        }
                    }
                )
            ),
        ),
        (
            OpenThermPollTaskName.RESET_CAUSE,
            None,
        ),
        (
            OpenThermPollTaskName.SMART_POWER_MODE,
            None,
        ),
    ],
)
async def test_is_running(
    pygw: OpenThermGateway,
    task_name: OpenThermPollTaskName,
    enable_start_condition_func: Callable[[OpenThermGateway], Any],
) -> None:
    """Test task.is_running()"""
    task = pygw._poll_tasks[task_name]
    if enable_start_condition_func is not None:
        assert task.is_running is False
        enable_start_condition_func(pygw)
    task.start()
    assert task.is_running is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "task_name",
        "disable_start_condition_func",
        "enable_start_condition_func",
        "report_type",
    ),
    [
        (
            OpenThermPollTaskName.ABOUT,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_ABOUT: "OpenTherm Gateway 5.8",
                        },
                    }
                )
            ),
            None,
            OpenThermReport.ABOUT,
        ),
        (
            OpenThermPollTaskName.BUILD,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_BUILD: "2021-12-23 16:23",
                        },
                    }
                )
            ),
            None,
            OpenThermReport.BUILD,
        ),
        (
            OpenThermPollTaskName.CLOCK_SPEED,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_CLOCKMHZ: "4 MHz",
                        },
                    }
                )
            ),
            None,
            OpenThermReport.CLOCK_SPEED,
        ),
        (
            OpenThermPollTaskName.GPIO_STATE,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_GPIO_A: 1,
                        },
                    }
                )
            ),
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_GPIO_A: 0,
                        },
                    }
                )
            ),
            OpenThermReport.GPIO_STATES,
        ),
        (
            OpenThermPollTaskName.RESET_CAUSE,
            (
                lambda gateway: gateway.status.submit_full_update(
                    {
                        OpenThermDataSource.GATEWAY: {
                            v.OTGW_RST_CAUSE: OpenThermResetCause.BROWNOUT,
                        },
                    }
                )
            ),
            None,
            OpenThermReport.RESET_CAUSE,
        ),
        (
            OpenThermPollTaskName.SMART_POWER_MODE,
            None,
            None,
            OpenThermReport.SMART_PWR_MODE,
        ),
    ],
)
async def test_polling_routing(
    pygw: OpenThermGateway,
    task_name: OpenThermPollTaskName,
    disable_start_condition_func: Callable[[OpenThermGateway], Any],
    enable_start_condition_func: Callable[[OpenThermGateway], Any],
    report_type: OpenThermReport,
) -> None:
    """Test task._polling_routing()"""
    pygw.get_report = AsyncMock()
    task = pygw._poll_tasks[task_name]
    task._interval = 0
    if enable_start_condition_func is not None:
        enable_start_condition_func(pygw)
    task.start()
    await called_x_times(pygw.get_report, 2)
    pygw.get_report.assert_has_awaits(
        [
            call(report_type),
            call(report_type),
        ]
    )
    if task._stop_on_success is True:
        pygw.get_report.reset_mock()
        disable_start_condition_func(pygw)
        await called_once(pygw.get_report)
        pygw.get_report.assert_awaited_once_with(report_type)
        while task.is_running is True:
            await asyncio.sleep(0)
        assert task.is_running is False
