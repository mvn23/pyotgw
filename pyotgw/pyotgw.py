# This file is part of pyotgw.
#
# pyotgw is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyotgw is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyotgw.  If not, see <http://www.gnu.org/licenses/>.
#
# Copyright 2018 Milan van Nugteren
#
"""pyotgw is a library to interface with the OpenTherm Gateway."""


import asyncio
import copy
import logging
from asyncio import TimeoutError
from datetime import datetime

import serial
import serial_asyncio
from pyotgw import protocol as otgw
from pyotgw import vars as v

_LOGGER = logging.getLogger(__name__)


class pyotgw:
    def __init__(self):
        """Create a pyotgw object."""
        self._connected = False
        self._conn_error = False
        self._notify = []
        return

    async def connect(
        self,
        loop,
        port,
        baudrate=9600,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        connection_timeout=10,
        inactivity_timeout=5,
    ):
        """
        Connect to Opentherm Gateway at @port.
        Initialize the parameters obtained from the PS= and PR=
        commands and returns the status dict with the obtained values.
        If called while connected, reconnect to the gateway.

        This method is a coroutine
        """
        if self._connected:
            # We are actually reconnecting, cleanup first.
            _LOGGER.debug("Reconnecting to serial device on %s", port)
            if self._gpio_task:
                self._gpio_task.cancel()
            self._connected = False
            self._transport.close()
        self.loop = loop

        async def attempt_connect():
            """Try to connect to the OpenTherm Gateway."""
            transport = None
            while transport is None:
                try:
                    transport, protocol = await serial_asyncio.create_serial_connection(
                        loop,
                        otgw.protocol,
                        port,
                        baudrate,
                        bytesize,
                        parity,
                        stopbits,
                        connection_timeout,
                        write_timeout=0,
                    )
                except serial.serialutil.SerialException as e:
                    if not self._conn_error:
                        _LOGGER.error(
                            "Could not connect to serial device on %s. "
                            "Will keep trying. Reported error was: %s",
                            port,
                            e,
                        )
                        self._conn_error = True
                    transport = None
                    await asyncio.sleep(5)
                except asyncio.CancelledError:
                    return
            return (transport, protocol)

        self._attempt_connect = self.loop.create_task(attempt_connect())
        transport, protocol = await self._attempt_connect
        if transport is None:
            return {}
        self._attempt_connect = None
        self._conn_error = False
        _LOGGER.debug("Connected to serial device on %s", port)
        self._transport = transport
        self._protocol = protocol
        self.loop.create_task(self._protocol.set_update_cb(self._send_report))
        if 0 < inactivity_timeout < 3:
            _LOGGER.error(
                "Inactivity timeout too low. Should be at least 3 seconds, got %d",
                inactivity_timeout,
            )
        if inactivity_timeout >= 3:

            async def reconnect():
                """Reconnect to the OpenTherm Gateway."""
                _LOGGER.debug("Scheduling reconnect...")
                await self.connect(
                    loop,
                    port,
                    baudrate,
                    bytesize,
                    parity,
                    stopbits,
                    connection_timeout,
                    inactivity_timeout,
                )

            self.loop.create_task(
                self._protocol.setup_watchdog(reconnect, inactivity_timeout)
            )
        self._gpio_task = None
        self._connected = True
        await self.get_reports()
        await self.get_status()
        if self._protocol.status.get(v.OTGW_GPIO_A) or self._protocol.status.get(
            v.OTGW_GPIO_B
        ):
            await self._poll_gpio(True)
        return copy.deepcopy(self._protocol.status)

    async def disconnect(self):
        """
        Disconnect from the OpenTherm Gateway.
        """
        if self._attempt_connect is not None:
            self._attempt_connect.cancel()
        if not self._connected:
            return
        await self._protocol.disconnect()

    def get_room_temp(self):
        """
        Get the current room temperature.
        """
        if not self._connected:
            return
        return self._protocol.status[v.THERMOSTAT].get(v.DATA_ROOM_TEMP)

    def get_target_temp(self):
        """
        Get the target temperature.
        """
        if not self._connected:
            return
        temp_ovrd = self._protocol.status[v.THERMOSTAT].get(v.DATA_ROOM_SETPOINT_OVRD)
        if temp_ovrd:
            return temp_ovrd
        return self._protocol.status[v.THERMOSTAT].get(v.DATA_ROOM_SETPOINT)

    async def set_target_temp(
        self, temp, temporary=True, timeout=v.OTGW_DEFAULT_TIMEOUT
    ):
        """
        Set the thermostat setpoint and return the newly accepted
        value.
        kwarg @temporary specifies whether or not the thermostat
            program may override this temperature.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_TARGET_TEMP if temporary else v.OTGW_CMD_TARGET_TEMP_CONST
        value = f"{temp:2.1f}"
        status_update = {v.OTGW: {}, v.THERMOSTAT: {}}
        ret = await self._wait_for_cmd(cmd, value, timeout)
        if ret is None:
            return
        ret = float(ret)
        if 0 <= ret <= 30:
            if ret == 0:
                status_update = {
                    v.OTGW: {v.OTGW_SETP_OVRD_MODE: v.OTGW_SETP_OVRD_DISABLED},
                    v.THERMOSTAT: {v.DATA_ROOM_SETPOINT_OVRD: None},
                }
            else:
                if temporary:
                    ovrd_mode = v.OTGW_SETP_OVRD_TEMPORARY
                else:
                    ovrd_mode = v.OTGW_SETP_OVRD_PERMANENT
                status_update = {
                    v.OTGW: {v.OTGW_SETP_OVRD_MODE: ovrd_mode},
                    v.THERMOSTAT: {v.DATA_ROOM_SETPOINT_OVRD: ret},
                }
            self._update_full_status(status_update)
            return ret

    def get_outside_temp(self):
        """
        Return the outside temperature as known in the gateway.
        """
        if not self._connected:
            return
        return self._protocol.status[v.THERMOSTAT].get(
            v.DATA_OUTSIDE_TEMP
        ) or self._protocol.status[v.BOILER].get(v.DATA_OUTSIDE_TEMP)

    async def set_outside_temp(self, temp, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Configure the outside temperature to send to the thermostat.
        Allowed values are between -40.0 and +64.0, although
        thermostats may not display the full range. Specify a value
        above 64 (suggestion: 99) to clear a previously configured
        value.
        Return the accepted value on success, '-' if a previously
        configured value has been cleared or None on failure.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_OUTSIDE_TEMP
        status_thermostat = {}
        if temp < -40:
            return None
        value = f"{temp:2.1f}"
        ret = await self._wait_for_cmd(cmd, value, timeout)
        if ret is None:
            return
        if ret not in ["-", None]:
            ret = float(ret)
        if ret == "-":
            status_thermostat[v.DATA_OUTSIDE_TEMP] = 0.0
        else:
            status_thermostat[v.DATA_OUTSIDE_TEMP] = ret
        self._update_status(v.THERMOSTAT, status_thermostat)
        return ret

    async def set_clock(self, date=datetime.now(), timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Change the time and day of the week of the thermostat. The
        gateway will send the specified time and day of the week in
        response to the next time and date message from the thermostat.
        @date is a :datetime: object which defaults to now()
        Return the response from the gateway with format HH:MM/DOW,
        where DOW is a single digit: 1=Monday, 7=Sunday.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_SET_CLOCK
        value = "{}/{}".format(date.strftime("%H:%M"), date.isoweekday())
        return await self._wait_for_cmd(cmd, value, timeout)

    def get_hot_water_ovrd(self):
        """
        Return the current hot water override mode if set, otherwise
        None.
        """
        if not self._connected:
            return
        return self._protocol.status[v.OTGW].get(v.OTGW_DHW_OVRD)

    async def get_reports(self):
        """
        Update the pyotgw object with the information from all of the
        PR commands and return the updated status dict.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_REPORT
        reports = {}
        for value in v.OTGW_REPORTS.keys():
            ret = await self._wait_for_cmd(cmd, value)
            if ret is None:
                reports[value] = None
                continue
            reports[value] = ret[2:]
        status_otgw = {
            v.OTGW_ABOUT: reports.get(v.OTGW_REPORT_ABOUT),
            v.OTGW_BUILD: reports.get(v.OTGW_REPORT_BUILDDATE),
            v.OTGW_CLOCKMHZ: reports.get(v.OTGW_REPORT_CLOCKMHZ),
            v.OTGW_MODE: reports.get(v.OTGW_REPORT_GW_MODE),
            v.OTGW_SMART_PWR: reports.get(v.OTGW_REPORT_SMART_PWR),
            v.OTGW_THRM_DETECT: reports.get(v.OTGW_REPORT_THERMOSTAT_DETECT),
            v.OTGW_DHW_OVRD: reports.get(v.OTGW_REPORT_DHW_SETTING),
        }
        status_thermostat = {}
        ovrd_mode = reports.get(v.OTGW_REPORT_SETPOINT_OVRD)
        if ovrd_mode is not None:
            ovrd_mode = str.upper(ovrd_mode[0])
            status_otgw.update({v.OTGW_SETP_OVRD_MODE: ovrd_mode})
        gpio_funcs = reports.get(v.OTGW_REPORT_GPIO_FUNCS)
        if gpio_funcs is not None:
            status_otgw.update(
                {v.OTGW_GPIO_A: int(gpio_funcs[0]), v.OTGW_GPIO_B: int(gpio_funcs[1])}
            )
        led_funcs = reports.get(v.OTGW_REPORT_LED_FUNCS)
        if led_funcs is not None:
            status_otgw.update(
                {
                    v.OTGW_LED_A: led_funcs[0],
                    v.OTGW_LED_B: led_funcs[1],
                    v.OTGW_LED_C: led_funcs[2],
                    v.OTGW_LED_D: led_funcs[3],
                    v.OTGW_LED_E: led_funcs[4],
                    v.OTGW_LED_F: led_funcs[5],
                }
            )
        tweaks = reports.get(v.OTGW_REPORT_TWEAKS)
        if tweaks is not None:
            status_otgw.update(
                {
                    v.OTGW_IGNORE_TRANSITIONS: int(tweaks[0]),
                    v.OTGW_OVRD_HB: int(tweaks[1]),
                }
            )
        sb_temp = reports.get(v.OTGW_REPORT_SETBACK_TEMP)
        if sb_temp is not None:
            status_otgw.update({v.OTGW_SB_TEMP: float(sb_temp)})
        vref = reports.get(v.OTGW_REPORT_VREF)
        if vref is not None:
            status_otgw.update({v.OTGW_VREF: int(vref)})
        if ovrd_mode is not None and ovrd_mode != v.OTGW_SETP_OVRD_DISABLED:
            status_thermostat = {
                v.DATA_ROOM_SETPOINT_OVRD: float(
                    reports[v.OTGW_REPORT_SETPOINT_OVRD][1:]
                )
            }
        self._update_full_status({v.THERMOSTAT: status_thermostat, v.OTGW: status_otgw})
        return copy.deepcopy(self._protocol.status)

    async def get_status(self):
        """
        Update the pyotgw object with the information from the PS
        command and return the updated status dict.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_SUMMARY
        ret = await self._wait_for_cmd(cmd, 1)
        # Return to 'reporting' mode
        asyncio.ensure_future(self._wait_for_cmd(cmd, 0), loop=self.loop)
        if ret is None:
            return
        fields = ret[1].split(",")
        device_status = fields[0].split("/")
        master_status = device_status[0]
        slave_status = device_status[1]
        remote_params = fields[2].split("/")
        capmodlimits = fields[4].split("/")
        dhw_setp_bounds = fields[13].split("/")
        ch_setp_bounds = fields[14].split("/")
        status = {
            v.DATA_MASTER_CH_ENABLED: int(master_status[7]),
            v.DATA_MASTER_DHW_ENABLED: int(master_status[6]),
            v.DATA_MASTER_COOLING_ENABLED: int(master_status[5]),
            v.DATA_MASTER_OTC_ENABLED: int(master_status[4]),
            v.DATA_MASTER_CH2_ENABLED: int(master_status[3]),
            v.DATA_SLAVE_FAULT_IND: int(slave_status[7]),
            v.DATA_SLAVE_CH_ACTIVE: int(slave_status[6]),
            v.DATA_SLAVE_DHW_ACTIVE: int(slave_status[5]),
            v.DATA_SLAVE_FLAME_ON: int(slave_status[4]),
            v.DATA_SLAVE_COOLING_ACTIVE: int(slave_status[3]),
            v.DATA_SLAVE_CH2_ACTIVE: int(slave_status[2]),
            v.DATA_SLAVE_DIAG_IND: int(slave_status[1]),
            v.DATA_CONTROL_SETPOINT: float(fields[1]),
            v.DATA_REMOTE_TRANSFER_DHW: int(remote_params[0][7]),
            v.DATA_REMOTE_TRANSFER_MAX_CH: int(remote_params[0][6]),
            v.DATA_REMOTE_RW_DHW: int(remote_params[1][7]),
            v.DATA_REMOTE_RW_MAX_CH: int(remote_params[1][6]),
            v.DATA_SLAVE_MAX_RELATIVE_MOD: float(fields[3]),
            v.DATA_SLAVE_MAX_CAPACITY: int(capmodlimits[0]),
            v.DATA_SLAVE_MIN_MOD_LEVEL: int(capmodlimits[1]),
            v.DATA_ROOM_SETPOINT: float(fields[5]),
            v.DATA_REL_MOD_LEVEL: float(fields[6]),
            v.DATA_CH_WATER_PRESS: float(fields[7]),
            v.DATA_ROOM_TEMP: float(fields[8]),
            v.DATA_CH_WATER_TEMP: float(fields[9]),
            v.DATA_DHW_TEMP: float(fields[10]),
            v.DATA_OUTSIDE_TEMP: float(fields[11]),
            v.DATA_RETURN_WATER_TEMP: float(fields[12]),
            v.DATA_SLAVE_DHW_MAX_SETP: int(dhw_setp_bounds[0]),
            v.DATA_SLAVE_DHW_MIN_SETP: int(dhw_setp_bounds[1]),
            v.DATA_SLAVE_CH_MAX_SETP: int(ch_setp_bounds[0]),
            v.DATA_SLAVE_CH_MIN_SETP: int(ch_setp_bounds[1]),
            v.DATA_DHW_SETPOINT: float(fields[15]),
            v.DATA_MAX_CH_SETPOINT: float(fields[16]),
            v.DATA_TOTAL_BURNER_STARTS: int(fields[17]),
            v.DATA_CH_PUMP_STARTS: int(fields[18]),
            v.DATA_DHW_PUMP_STARTS: int(fields[19]),
            v.DATA_DHW_BURNER_STARTS: int(fields[20]),
            v.DATA_TOTAL_BURNER_HOURS: int(fields[21]),
            v.DATA_CH_PUMP_HOURS: int(fields[22]),
            v.DATA_DHW_PUMP_HOURS: int(fields[23]),
            v.DATA_DHW_BURNER_HOURS: int(fields[24]),
        }
        self._update_full_status({v.BOILER: status, v.THERMOSTAT: status})
        return copy.deepcopy(self._protocol.status)

    async def set_hot_water_ovrd(self, state, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Control the domestic hot water enable option. If the boiler has
        been configured to let the room unit control when to keep a
        small amount of water preheated, this command can influence
        that.
        @state should be 0 or 1 to enable the override in off or on
        state, or any other single character to disable the override.
        Return the accepted value, 'A' if the override is disabled
        or None on failure.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_HOT_WATER
        status_otgw = {}
        ret = await self._wait_for_cmd(cmd, state, timeout)
        if ret is None:
            return
        if ret == "A":
            status_otgw[v.OTGW_DHW_OVRD] = None
        elif ret in ["0", "1"]:
            status_otgw[v.OTGW_DHW_OVRD] = int(ret)
        self._update_status(v.OTGW, status_otgw)
        return ret

    def get_mode(self):
        """
        Return the last known gateway operating mode. Return "G" for
        Gateway mode or "M" for Monitor mode.
        """
        if not self._connected:
            return
        return self._protocol.status[v.OTGW].get(v.OTGW_MODE)

    async def set_mode(self, mode, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Set the operating mode to either "Gateway" mode (:mode: =
        OTGW_MODE_GATEWAY or 1) or "Monitor" mode (:mode: =
        OTGW_MODE_MONITOR or 0), or use this method to reset the device
        (:mode: = OTGW_MODE_RESET).
        Return the newly activated mode, or the full renewed status
        dict after a reset.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_MODE
        status_otgw = {}
        ret = await self._wait_for_cmd(cmd, mode, timeout)
        if ret is None:
            return
        if mode is v.OTGW_MODE_RESET:
            self._protocol.status = {v.BOILER: {}, v.OTGW: {}, v.THERMOSTAT: {}}
            await self.get_reports()
            await self.get_status()
            return copy.deepcopy(self._protocol.status)
        status_otgw[v.OTGW_MODE] = ret
        self._update_status(v.OTGW, status_otgw)
        return ret

    def get_led_mode(self, led_id):
        """
        Return the led mode for led :led_id:.
        @led_id Character in range A-F
        """
        if not self._connected:
            return
        return self._protocol.status[v.OTGW].get(getattr(v, f"OTGW_LED_{led_id}"))

    async def set_led_mode(self, led_id, mode, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Configure the functions of the six LEDs (A-F) that can
        optionally be connected to pins RB3/RB4/RB6/RB7 and the GPIO
        pins of the PIC. The following functions are currently
        available:

        R Receiving an Opentherm message from the thermostat or boiler
        X Transmitting an Opentherm message to the thermostat or boiler
        T Transmitting or receiving a message on the master interface
        B Transmitting or receiving a message on the slave interface
        O Remote setpoint override is active
        F Flame is on
        H Central heating is on
        W Hot water is on
        C Comfort mode (Domestic Hot Water Enable) is on
        E Transmission error has been detected
        M Boiler requires maintenance
        P Raised power mode active on thermostat interface.

        Return the new mode for the specified led, or None on failure.

        This method is a coroutine
        """
        if led_id in "ABCDEF" and mode in "RXTBOFHWCEMP":
            cmd = getattr(v, f"OTGW_CMD_LED_{led_id}")
            status_otgw = {}
            ret = await self._wait_for_cmd(cmd, mode, timeout)
            if ret is None:
                return
            var = getattr(v, f"OTGW_LED_{led_id}")
            status_otgw[var] = ret
            self._update_status(v.OTGW, status_otgw)
            return ret

    def get_gpio_mode(self, gpio_id):
        """
        Return the gpio mode for gpio :gpio_id:.
        @gpio_id Character A or B.
        """
        if not self._connected:
            return
        return self._protocol.status[v.OTGW].get(getattr(v, f"OTGW_GPIO_{gpio_id}"))

    async def set_gpio_mode(self, gpio_id, mode, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Configure the functions of the two GPIO pins of the gateway.
        The following functions are available:

        0 No function, default for both ports on a freshly flashed chip
        1 Ground - A permanently low output (0V). Could be used for a
            power LED
        2 Vcc - A permanently high output (5V). Can be used as a
            short-proof power supply for some external circuitry used
            by the other GPIO port
        3 LED E - An additional LED if you want to present more than 4
            LED functions
        4 LED F - An additional LED if you want to present more than 5
            LED functions
        5 Home - Set thermostat to setback temperature when pulled low
        6 Away - Set thermostat to setback temperature when pulled high
        7 DS1820 (GPIO port B only) - Data line for a DS18S20 or
            DS18B20 temperature sensor used to measure the outside
            temperature. A 4k7 resistor should be connected between
            GPIO port B and Vcc

        Return the new mode for the specified gpio, or None on
        failure.

        This method is a coroutine
        """
        if gpio_id in "AB" and mode in range(8):
            if mode == 7 and gpio_id != "B":
                return None
            cmd = getattr(v, f"OTGW_CMD_GPIO_{gpio_id}")
            status_otgw = {}
            ret = await self._wait_for_cmd(cmd, mode, timeout)
            if ret is None:
                return
            ret = int(ret)
            var = getattr(v, f"OTGW_GPIO_{gpio_id}")
            status_otgw[var] = ret
            self._update_status(v.OTGW, status_otgw)
            asyncio.ensure_future(
                self._poll_gpio(
                    self._protocol.status[v.OTGW].get(v.OTGW_GPIO_A)
                    or self._protocol.status[v.OTGW].get(v.OTGW_GPIO_B)
                )
            )
            return ret

    def get_setback_temp(self):
        """
        Return the last known setback temperature from the device.
        """
        if not self._connected:
            return
        return self._protocol.status[v.OTGW].get(v.OTGW_SB_TEMP)

    async def set_setback_temp(self, sb_temp, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Configure the setback temperature to use in combination with
        GPIO functions HOME (5) and AWAY (6).
        Return the new setback temperature, or None on failure.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_SETBACK
        status_otgw = {}
        ret = await self._wait_for_cmd(cmd, sb_temp, timeout)
        if ret is None:
            return
        ret = float(ret)
        status_otgw[v.OTGW_SB_TEMP] = ret
        self._update_status(v.OTGW, status_otgw)
        return ret

    async def add_alternative(self, alt, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Add the specified Data-ID to the list of alternative commands
        to send to the boiler instead of a Data-ID that is known to be
        unsupported by the boiler. Alternative Data-IDs will always be
        sent to the boiler in a Read-Data request message with the
        data-value set to zero. The table of alternative Data-IDs is
        stored in non-volatile memory so it will persist even if the
        gateway has been powered off. Data-ID values from 1 to 255 are
        allowed.
        Return the ID that was added to the list, or None on failure.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_ADD_ALT
        alt = int(alt)
        if alt < 1 or alt > 255:
            return None
        ret = await self._wait_for_cmd(cmd, alt, timeout)
        if ret is not None:
            return int(ret)

    async def del_alternative(self, alt, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Remove the specified Data-ID from the list of alternative
        commands. Only one occurrence is deleted. If the Data-ID
        appears multiple times in the list of alternative commands,
        this command must be repeated to delete all occurrences. The
        table of alternative Data-IDs is stored in non-volatile memory
        so it will persist even if the gateway has been powered off.
        Data-ID values from 1 to 255 are allowed.
        Return the ID that was removed from the list, or None on
        failure.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_DEL_ALT
        alt = int(alt)
        if alt < 1 or alt > 255:
            return None
        ret = await self._wait_for_cmd(cmd, alt, timeout)
        if ret is not None:
            return int(ret)

    async def add_unknown_id(self, unknown_id, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Inform the gateway that the boiler doesn't support the
        specified Data-ID, even if the boiler doesn't indicate that
        by returning an Unknown-DataId response. Using this command
        allows the gateway to send an alternative Data-ID to the boiler
        instead.
        Return the added ID, or None on failure.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_UNKNOWN_ID
        unknown_id = int(unknown_id)
        if unknown_id < 1 or unknown_id > 255:
            return None
        ret = await self._wait_for_cmd(cmd, unknown_id, timeout)
        if ret is not None:
            return int(ret)

    async def del_unknown_id(self, unknown_id, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Start forwarding the specified Data-ID to the boiler again.
        This command resets the counter used to determine if the
        specified Data-ID is supported by the boiler.
        Return the ID that was marked as supported, or None on failure.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_KNOWN_ID
        unknown_id = int(unknown_id)
        if unknown_id < 1 or unknown_id > 255:
            return None
        ret = await self._wait_for_cmd(cmd, unknown_id, timeout)
        if ret is not None:
            return int(ret)

    async def prio_message(self, message, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        NOT IMPLEMENTED YET!
        Specify a one-time priority message to be sent to the boiler at
        the first opportunity. If the specified message returns the
        number of Transparent Slave Parameters (TSPs) or Fault History
        Buffers (FHBs), the gateway will proceed to request those TSPs
        or FHBs.

        This method is a coroutine
        """
        # TODO: implement this, including FHB/TSP processing
        return

    async def set_response(self, data_id, data, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        NOT IMPLEMENTED YET!
        Configure a response to send back to the thermostat instead of
        the response produced by the boiler.
        @data is a list of either one or two hex byte values
        Return the data ID for which the response was set, or None on
        failure.

        This method is a coroutine
        """
        # TODO: implement this
        return

    async def clear_response(self, data_id, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Clear a previously configured response to send back to the
        thermostat for :data_id:.
        Return the data ID for which the response was cleared, or None
        on failure.

        This method is a coroutine
        """
        # TODO: implement this
        return

    async def set_max_ch_setpoint(self, temperature, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Set the maximum central heating setpoint. This command is only
        available with boilers that support this function.
        Return the newly accepted setpoint, or None on failure.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_SET_MAX
        status_boiler = {}
        ret = await self._wait_for_cmd(cmd, temperature, timeout)
        if ret is None:
            return
        ret = float(ret)
        status_boiler[v.DATA_MAX_CH_SETPOINT] = ret
        self._update_status(v.BOILER, status_boiler)
        return ret

    async def set_dhw_setpoint(self, temperature, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Set the domestic hot water setpoint. This command is only
        available with boilers that support this function.
        Return the newly accepted setpoint, or None on failure.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_SET_WATER
        status_boiler = {}
        ret = await self._wait_for_cmd(cmd, temperature, timeout)
        if ret is None:
            return
        ret = float(ret)
        status_boiler[v.DATA_DHW_SETPOINT] = ret
        self._update_status(v.BOILER, status_boiler)
        return ret

    async def set_max_relative_mod(self, max_mod, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Override the maximum relative modulation from the thermostat.
        Valid values are 0 through 100. Clear the setting by specifying
        a non-numeric value.
        Return the newly accepted value, '-' if a previous value was
        cleared, or None on failure.

        This method is a coroutine
        """
        if isinstance(max_mod, int) and not 0 <= max_mod <= 100:
            return None
        cmd = v.OTGW_CMD_MAX_MOD
        status_boiler = {}
        ret = await self._wait_for_cmd(cmd, max_mod, timeout)
        if ret not in ["-", None]:
            ret = int(ret)
        if ret == "-":
            status_boiler[v.DATA_SLAVE_MAX_RELATIVE_MOD] = None
        else:
            status_boiler[v.DATA_SLAVE_MAX_RELATIVE_MOD] = ret
        self._update_status(v.BOILER, status_boiler)
        return ret

    async def set_control_setpoint(self, setpoint, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Manipulate the control setpoint being sent to the boiler. Set
        to 0 to pass along the value specified by the thermostat.
        Return the newly accepted value, or None on failure.

        This method is a coroutine
        """
        cmd = v.OTGW_CMD_CONTROL_SETPOINT
        status_boiler = {}
        ret = await self._wait_for_cmd(cmd, setpoint, timeout)
        if ret is None:
            return
        ret = float(ret)
        status_boiler[v.DATA_CONTROL_SETPOINT] = ret
        self._update_status(v.BOILER, status_boiler)
        return ret

    async def set_ch_enable_bit(self, ch_bit, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Control the CH enable status bit when overriding the control
        setpoint. By default the CH enable bit is set after a call to
        set_control_setpoint with a value other than 0. With this
        method, the bit can be manipulated.
        @ch_bit can be either 0 or 1.
        Return the newly accepted value (0 or 1), or None on failure.

        This method is a coroutine
        """
        if ch_bit not in [0, 1]:
            return None
        cmd = v.OTGW_CMD_CONTROL_HEATING
        status_boiler = {}
        ret = await self._wait_for_cmd(cmd, ch_bit, timeout)
        if ret is None:
            return
        ret = int(ret)
        status_boiler[v.DATA_MASTER_CH_ENABLED] = ret
        self._update_status(v.BOILER, status_boiler)
        return ret

    async def set_ventilation(self, pct, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Configure a ventilation setpoint override value (0-100%).
        Return the newly accepted value, or None on failure.
        @pct :int: Must be between 0 and 100.

        This method is a coroutine
        """
        if not 0 <= pct <= 100:
            return None
        cmd = v.OTGW_CMD_VENT
        status_boiler = {}
        ret = await self._wait_for_cmd(cmd, pct, timeout)
        if ret is None:
            return
        ret = int(ret)
        status_boiler[v.DATA_COOLING_CONTROL] = ret
        self._update_status(v.BOILER, status_boiler)
        return ret

    def subscribe(self, coro):
        """
        Subscribe to status updates from the Opentherm Gateway.
        Can only be used after connect()
        @coro is a coroutine which will be called with a single
        argument (status) when a status change occurs.
        Return True on success, False if not connected or already
        subscribed.
        """
        if coro not in self._notify:
            self._notify.append(coro)
            return True
        return False

    def unsubscribe(self, coro):
        """
        Unsubscribe from status updates from the Opentherm Gateway.
        Can only be used after connect()
        @coro is a coroutine which has been subscribed with subscribe()
        earlier.
        Return True on success, false if not connected or subscribed.
        """
        if coro in self._notify:
            self._notify.remove(coro)
            return True
        return False

    async def _send_report(self, status):
        """
        Call all subscribed coroutines in _notify whenever a status
        update occurs.

        This method is a coroutine
        """
        if len(self._notify) > 0:
            # Each client gets its own copy of the dict.
            asyncio.gather(
                *[coro(copy.deepcopy(status)) for coro in self._notify], loop=self.loop
            )

    async def _wait_for_cmd(self, cmd, value, timeout=v.OTGW_DEFAULT_TIMEOUT):
        """
        Wrap @cmd in applicable asyncio call.

        This method is a coroutine.
        """
        if not self._connected:
            return
        try:
            return await asyncio.wait_for(
                self._protocol.issue_cmd(cmd, value), timeout, loop=self.loop
            )
        except TimeoutError:
            _LOGGER.error("Timed out waiting for command: %s, value: %s.", cmd, value)
            return
        except (RuntimeError, SyntaxError, ValueError) as exc:
            _LOGGER.error(
                "Command %s with value %s raised exception: %s", cmd, value, exc
            )

    async def _poll_gpio(self, poll, interval=10):
        """
        Start or stop polling GPIO states.

        GPIO states aren't being pushed by the gateway, we need to poll
        if we want updates.
        """
        if poll and self._gpio_task is None:

            async def polling_routine(interval):
                """Poll GPIO state every @interval seconds."""
                while True:
                    try:
                        pios = None
                        ret = await self._wait_for_cmd(
                            v.OTGW_CMD_REPORT, v.OTGW_REPORT_GPIO_STATES
                        )
                        if ret:
                            pios = ret[2:]
                            status_otgw = {
                                v.OTGW_GPIO_A_STATE: int(pios[0]),
                                v.OTGW_GPIO_B_STATE: int(pios[1]),
                            }
                            self._update_status(v.OTGW, status_otgw)
                        await asyncio.sleep(interval)
                    except asyncio.CancelledError:
                        status_otgw = {
                            v.OTGW_GPIO_A_STATE: 0,
                            v.OTGW_GPIO_B_STATE: 0,
                        }
                        self._update_status(v.OTGW, status_otgw)
                        self._gpio_task = None
                        break

            self._gpio_task = self.loop.create_task(polling_routine(interval))
        elif not poll and self._gpio_task is not None:
            self._gpio_task.cancel()

    def _update_status(self, part, update):
        """Update part of the status dict and push it to subscribers."""
        if part not in self._protocol.status:
            _LOGGER.error(f"Invalid status part for update: {part}")
            return
        try:
            if isinstance(update, dict):
                self._protocol.status[part].update(update)
                self._protocol._updateq.put_nowait(copy.deepcopy(self._protocol.status))
        except AttributeError:
            _LOGGER.warning(
                "Error sending status update. Are we connected to the gateway?"
            )

    def _update_full_status(self, update):
        """Update the full status dict recursively and push it to subscribers."""
        for part in update.keys():
            if part not in self._protocol.status:
                _LOGGER.error(f"Invalid status part for update: {part}")
                return
        try:
            for part, values in update.items():
                if isinstance(values, dict):
                    self._protocol.status[part].update(values)
            self._protocol._updateq.put_nowait(copy.deepcopy(self._protocol.status))
        except AttributeError:
            _LOGGER.warning(
                "Error sending status update. Are we connected to the gateway?"
            )
