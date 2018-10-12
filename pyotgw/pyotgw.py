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
import pyotgw.protocol as otgw
import serial
import serial_asyncio

from datetime import datetime
from pyotgw.vars import *


class pyotgw:

    def __init__(self):
        """Create a pyotgw object."""
        return

    async def connect(self, loop, port, baudrate=9600,
                      bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                      stopbits=serial.STOPBITS_ONE, timeout=30):
        """
        Connect to Opentherm Gateway at @port.
        Initialize the parameters obtained from the PS= and PR=
        commands and returns the status dict with the obtained values.

        This method is a coroutine
        """
        transport, protocol = await serial_asyncio.create_serial_connection(
            loop, otgw.protocol, port, baudrate, bytesize, parity,
            stopbits, timeout)
        self._transport = transport
        self._protocol = protocol
        self.loop = loop
        await self.get_reports()
        await self.get_status()
        asyncio.ensure_future(protocol._report(), loop=self.loop)
        return self._protocol.status

    def get_room_temp(self):
        """
        Get the current room temperature.
        """
        return self._protocol.status.get(DATA_ROOM_TEMP)

    def get_target_temp(self):
        """
        Get the target temperature.
        """
        temp_ovrd = self._protocol.status.get(DATA_ROOM_SETPOINT_OVRD)
        if temp_ovrd:
            return temp_ovrd
        return self._protocol.status.get(DATA_ROOM_SETPOINT)

    async def set_target_temp(self, temp, temporary=True,
                              timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Set the thermostat setpoint and return the newly accepted
        value.
        kwarg @temporary specifies whether or not the thermostat
            program may override this temperature.

        This method is a coroutine
        """
        cmd = (OTGW_CMD_TARGET_TEMP if temporary
               else OTGW_CMD_TARGET_TEMP_CONST)
        value = '{:2.1f}'.format(temp)
        ret = await self._wait_for_cmd(cmd, value, timeout)
        if ret is None:
            return
        ret = float(ret)
        if ret == 0:
            self._protocol.status[OTGW_SETP_OVRD_MODE] = (
                OTGW_SETP_OVRD_DISABLED
            )
            self._protocol.status[DATA_ROOM_SETPOINT_OVRD] = None
            return ret
        if ret > 0:
            if temporary:
                ovrd_mode = OTGW_SETP_OVRD_TEMPORARY
            else:
                ovrd_mode = OTGW_SETP_OVRD_PERMANENT
            self._protocol.status[OTGW_SETP_OVRD_MODE] = ovrd_mode
            self._protocol.status[DATA_ROOM_SETPOINT_OVRD] = ret
            return ret

    def get_outside_temp(self):
        """
        Return the outside temperature as known in the gateway.
        """
        return self._protocol.status.get(DATA_OUTSIDE_TEMP)

    async def set_outside_temp(self, temp, timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Configure the outside temperature to send to the thermostat.
        Allowed values are between -40.0 and +64.0, although
        thermostats may not display the full range. Specify a value
        above 64 (suggestion: 99) to clear a previously configured
        value.
        Return the accepted value on success or None on failure.

        This method is a coroutine
        """
        cmd = OTGW_CMD_OUTSIDE_TEMP
        if temp < -40:
            return None
        value = '{:2.1f}'.format(temp)
        ret = await self._wait_for_cmd(cmd, value, timeout)
        if ret is None:
            return
        ret = float(ret)
        self._protocol.status[DATA_OUTSIDE_TEMP] = (None if ret > 64 else ret)
        return ret

    async def set_clock(self, date=datetime.now(),
                        timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Change the time and day of the week of the thermostat. The
        gateway will send the specified time and day of the week in
        response to the next time and date message from the thermostat.
        @date is a :datetime: object which defaults to now()
        Return the response from the gateway with format HH:MM/DOW,
        where DOW is a single digit: 1=Monday, 7=Sunday.

        This method is a coroutine
        """
        cmd = OTGW_CMD_SET_CLOCK
        value = "{}/{}".format(date.strftime('%H:%M'), date.isoweekday())
        return await self._wait_for_cmd(cmd, value, timeout)

    def get_hot_water_ovrd(self):
        """
        Return the current hot water override mode if set, otherwise
        None.
        """
        return self._protocol.status.get(OTGW_DHW_OVRD)

    async def get_reports(self):
        """
        Update the pyotgw object with the information from all of the
        PR commands and return the updated status dict.

        This method is a coroutine
        """
        cmd = OTGW_CMD_REPORT
        reports = {}
        for value in OTGW_REPORTS.keys():
            ret = await self._wait_for_cmd(cmd, value)
            if ret is None:
                continue
            reports[value] = ret[2:]
        ovrd_mode = str.upper(reports[OTGW_REPORT_SETPOINT_OVRD][0])
        status = {
            OTGW_ABOUT: reports[OTGW_REPORT_ABOUT],
            OTGW_BUILD: reports[OTGW_REPORT_BUILDDATE],
            OTGW_CLOCKMHZ: reports[OTGW_REPORT_CLOCKMHZ],
            OTGW_GPIO_A: int(reports[OTGW_REPORT_GPIO_FUNCS][0]),
            OTGW_GPIO_B: int(reports[OTGW_REPORT_GPIO_FUNCS][1]),
            OTGW_GPIO_A_STATE: int(reports[OTGW_REPORT_GPIO_STATES][0]),
            OTGW_GPIO_B_STATE: int(reports[OTGW_REPORT_GPIO_STATES][1]),
            OTGW_LED_A: reports[OTGW_REPORT_LED_FUNCS][0],
            OTGW_LED_B: reports[OTGW_REPORT_LED_FUNCS][1],
            OTGW_LED_C: reports[OTGW_REPORT_LED_FUNCS][2],
            OTGW_LED_D: reports[OTGW_REPORT_LED_FUNCS][3],
            OTGW_LED_E: reports[OTGW_REPORT_LED_FUNCS][4],
            OTGW_LED_F: reports[OTGW_REPORT_LED_FUNCS][5],
            OTGW_MODE: reports[OTGW_REPORT_GW_MODE],
            OTGW_SETP_OVRD_MODE: ovrd_mode,
            OTGW_SMART_PWR: reports[OTGW_REPORT_SMART_PWR],
            OTGW_THRM_DETECT: reports[OTGW_REPORT_THERMOSTAT_DETECT],
            OTGW_SB_TEMP: float(reports[OTGW_REPORT_SETBACK_TEMP]),
            OTGW_IGNORE_TRANSITIONS: int(reports[OTGW_REPORT_TWEAKS][0]),
            OTGW_OVRD_HB: int(reports[OTGW_REPORT_TWEAKS][1]),
            OTGW_VREF: int(reports[OTGW_REPORT_VREF]),
            OTGW_DHW_OVRD: reports[OTGW_REPORT_DHW_SETTING]
        }
        if (ovrd_mode != OTGW_SETP_OVRD_DISABLED and
                reports[OTGW_REPORT_SETPOINT_OVRD]):
            status[DATA_ROOM_SETPOINT_OVRD] = float(
                reports[OTGW_REPORT_SETPOINT_OVRD][1:])
        self._protocol.status.update(status)
        return self._protocol.status

    async def get_status(self):
        """
        Update the pyotgw object with the information from the PS
        command and return the updated status dict.

        This method is a coroutine
        """
        cmd = OTGW_CMD_SUMMARY
        ret = await self._wait_for_cmd(cmd, 1)
        # Return to 'reporting' mode
        asyncio.ensure_future(self._protocol.issue_cmd(cmd, 0),
                              loop=self.loop)
        fields = ret[1].split(',')
        device_status = fields[0].split('/')
        master_status = device_status[0]
        slave_status = device_status[1]
        remote_params = fields[2].split('/')
        capmodlimits = fields[4].split('/')
        dhw_setp_bounds = fields[13].split('/')
        ch_setp_bounds = fields[14].split('/')
        status = {
            DATA_MASTER_CH_ENABLED: int(master_status[7]),
            DATA_MASTER_DHW_ENABLED: int(master_status[6]),
            DATA_MASTER_COOLING_ENABLED: int(master_status[5]),
            DATA_MASTER_OTC_ENABLED: int(master_status[4]),
            DATA_MASTER_CH2_ENABLED: int(master_status[3]),
            DATA_SLAVE_FAULT_IND: int(slave_status[7]),
            DATA_SLAVE_CH_ACTIVE: int(slave_status[6]),
            DATA_SLAVE_DHW_ACTIVE: int(slave_status[5]),
            DATA_SLAVE_FLAME_ON: int(slave_status[4]),
            DATA_SLAVE_COOLING_ACTIVE: int(slave_status[3]),
            DATA_SLAVE_CH2_ACTIVE: int(slave_status[2]),
            DATA_SLAVE_DIAG_IND: int(slave_status[1]),
            DATA_CONTROL_SETPOINT: float(fields[1]),
            DATA_REMOTE_TRANSFER_DHW: int(remote_params[0][7]),
            DATA_REMOTE_TRANSFER_MAX_CH: int(remote_params[0][6]),
            DATA_REMOTE_RW_DHW: int(remote_params[1][7]),
            DATA_REMOTE_RW_MAX_CH: int(remote_params[1][6]),
            DATA_SLAVE_MAX_RELATIVE_MOD: float(fields[3]),
            DATA_SLAVE_MAX_CAPACITY: int(capmodlimits[0]),
            DATA_SLAVE_MIN_MOD_LEVEL: int(capmodlimits[1]),
            DATA_ROOM_SETPOINT: float(fields[5]),
            DATA_REL_MOD_LEVEL: float(fields[6]),
            DATA_CH_WATER_PRESS: float(fields[7]),
            DATA_ROOM_TEMP: float(fields[8]),
            DATA_CH_WATER_TEMP: float(fields[9]),
            DATA_DHW_TEMP: float(fields[10]),
            DATA_OUTSIDE_TEMP: float(fields[11]),
            DATA_RETURN_WATER_TEMP: float(fields[12]),
            DATA_SLAVE_DHW_MAX_SETP: int(dhw_setp_bounds[0]),
            DATA_SLAVE_DHW_MIN_SETP: int(dhw_setp_bounds[1]),
            DATA_SLAVE_CH_MAX_SETP: int(ch_setp_bounds[0]),
            DATA_SLAVE_CH_MIN_SETP: int(ch_setp_bounds[1]),
            DATA_DHW_SETPOINT: float(fields[15]),
            DATA_MAX_CH_SETPOINT: float(fields[16]),
            DATA_TOTAL_BURNER_STARTS: int(fields[17]),
            DATA_CH_PUMP_STARTS: int(fields[18]),
            DATA_DHW_PUMP_STARTS: int(fields[19]),
            DATA_DHW_BURNER_STARTS: int(fields[20]),
            DATA_TOTAL_BURNER_HOURS: int(fields[21]),
            DATA_CH_PUMP_HOURS: int(fields[22]),
            DATA_DHW_PUMP_HOURS: int(fields[23]),
            DATA_DHW_BURNER_HOURS: int(fields[24])
        }
        self._protocol.status.update(status)
        return self._protocol.status

    async def set_hot_water_ovrd(self, state, timeout=OTGW_DEFAULT_TIMEOUT):
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
        cmd = OTGW_CMD_HOT_WATER
        ret = await self._wait_for_cmd(cmd, state, timeout)
        if ret is 'A':
            self._protocol.status[OTGW_DHW_OVRD] = None
        elif ret in ['0', '1']:
            self._protocol.status[OTGW_DHW_OVRD] = int(ret)
        return ret

    def get_mode(self):
        """
        Return the last known gateway operating mode. Return "G" for
        Gateway mode or "M" for Monitor mode.
        """
        return self._protocol.status[OTGW_MODE]

    async def set_mode(self, mode, timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Set the operating mode to either "Gateway" mode (:mode: =
        OTGW_MODE_GATEWAY or 1) or "Monitor" mode (:mode: =
        OTGW_MODE_MONITOR or 0), or use this method to reset the device
        (:mode: = OTGW_MODE_RESET).
        Return the newly activated mode, or the full renewed status
        dict after a reset.

        This method is a coroutine
        """
        cmd = OTGW_CMD_MODE
        ret = await self._wait_for_cmd(cmd, mode, timeout)
        if mode is OTGW_MODE_RESET:
            self._protocol.status = {}
            await self.get_reports()
            await self.get_status()
            return self._protocol.status
        self._protocol.status[OTGW_MODE] = ret
        return ret

    def get_led_mode(self, led_id):
        """
        Return the led mode for led :led_id:.
        @led_id Character in range A-F
        """
        return self._protocol.status.get("OTGW_LED_{}".format(led_id))

    async def set_led_mode(self, led_id, mode, timeout=OTGW_DEFAULT_TIMEOUT):
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
            cmd = globals().get("OTGW_CMD_LED_{}".format(led_id))
            ret = await self._wait_for_cmd(cmd, mode, timeout)
            if ret is None:
                return
            var = globals().get("OTGW_LED_{}".format(led_id))
            self._protocol.status[var] = ret
            return ret

    def get_gpio_mode(self, gpio_id):
        """
        Return the gpio mode for gpio :gpio_id:.
        @gpio_id Character A or B.
        """
        return self._protocol.status.get("OTGW_GPIO_{}".format(gpio_id))

    async def set_gpio_mode(self, gpio_id, mode, timeout=OTGW_DEFAULT_TIMEOUT):
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
            cmd = globals().get("OTGW_CMD_GPIO_{}".format(gpio_id))
            ret = await self._wait_for_cmd(cmd, mode, timeout)
            if ret is None:
                return
            ret = int(ret)
            var = globals().get("OTGW_GPIO_{}_STATE".format(gpio_id))
            self._protocol.status[var] = ret
            return ret

    def get_setback_temp(self):
        """
        Return the last known setback temperature from the device.
        """
        return self._protocol.status[OTGW_SB_TEMP]

    async def set_setback_temp(self, sb_temp, timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Configure the setback temperature to use in combination with
        GPIO functions HOME (5) and AWAY (6).
        Return the new setback temperature, or None on failure.

        This method is a coroutine
        """
        cmd = OTGW_CMD_SETBACK
        ret = await self._wait_for_cmd(cmd, sb_temp, timeout)
        if ret is None:
            return
        ret = float(ret)
        self._protocol.status[OTGW_SB_TEMP] = ret
        return ret

    async def add_alternative(self, alt, timeout=OTGW_DEFAULT_TIMEOUT):
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
        cmd = OTGW_CMD_ADD_ALT
        alt = int(alt)
        if alt < 1 or alt > 255:
            return None
        ret = await self._wait_for_cmd(cmd, alt, timeout)
        if ret is not None:
            return int(ret)

    async def del_alternative(self, alt, timeout=OTGW_DEFAULT_TIMEOUT):
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
        cmd = OTGW_CMD_DEL_ALT
        alt = int(alt)
        if alt < 1 or alt > 255:
            return None
        ret = await self._wait_for_cmd(cmd, alt, timeout)
        if ret is not None:
            return int(ret)

    async def add_unknown_id(self, unknown_id, timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Inform the gateway that the boiler doesn't support the
        specified Data-ID, even if the boiler doesn't indicate that
        by returning an Unknown-DataId response. Using this command
        allows the gateway to send an alternative Data-ID to the boiler
        instead.
        Return the added ID, or None on failure.

        This method is a coroutine
        """
        cmd = OTGW_CMD_UNKNOWN_ID
        unknown_id = int(unknown_id)
        if unknown_id < 1 or unknown_id > 255:
            return None
        ret = await self._wait_for_cmd(cmd, unknown_id, timeout)
        if ret is not None:
            return int(ret)

    async def del_unknown_id(self, unknown_id, timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Start forwarding the specified Data-ID to the boiler again.
        This command resets the counter used to determine if the
        specified Data-ID is supported by the boiler.
        Return the ID that was removed, or None on failure.

        This method is a coroutine
        """
        cmd = OTGW_CMD_KNOWN_ID
        unknown_id = int(unknown_id)
        if unknown_id < 1 or unknown_id > 255:
            return None
        ret = await self._wait_for_cmd(cmd, unknown_id, timeout)
        if ret is not None:
            return int(ret)

    async def prio_message(self, data_id, timeout=OTGW_DEFAULT_TIMEOUT):
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

    async def set_response(self, data_id, data, timeout=OTGW_DEFAULT_TIMEOUT):
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

    async def clear_response(self, data_id, timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Clear a previously configured response to send back to the
        thermostat for :data_id:.
        Return the data ID for which the response was cleared, or None
        on failure.

        This method is a coroutine
        """
        # TODO: implement this
        return

    async def set_max_ch_setpoint(self, temperature,
                                  timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Set the maximum central heating setpoint. This command is only
        available with boilers that support this function.
        Return the newly accepted setpoint, or None on failure.

        This method is a coroutine
        """
        cmd = OTGW_CMD_SET_MAX
        ret = await self._wait_for_cmd(cmd, temperature, timeout)
        if ret is None:
            return
        ret = float(ret)
        self._protocol.status[DATA_MAX_CH_SETPOINT] = ret
        return ret

    async def set_dhw_setpoint(self, temperature,
                                   timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Set the domestic hot water setpoint. This command is only
        available with boilers that support this function.
        Return the newly accepted setpoint, or None on failure.

        This method is a coroutine
        """
        cmd = OTGW_CMD_SET_WATER
        ret = await self._wait_for_cmd(cmd, temperature, timeout)
        if ret is None:
            return
        ret = float(ret)
        self._protocol.status[DATA_DHW_SETPOINT] = ret
        return ret

    async def set_max_relative_mod(self, max_mod,
                                   timeout=OTGW_DEFAULT_TIMEOUT):
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
        cmd = OTGW_CMD_MAX_MOD
        ret = await self._wait_for_cmd(cmd, max_mod, timeout)
        if ret not in ['-', None]:
            ret = int(ret)
            self._protocol.status[DATA_SLAVE_MAX_RELATIVE_MOD] = ret
        return ret

    async def set_control_setpoint(self, setpoint,
                                   timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Manipulate the control setpoint being sent to the boiler. Set
        to 0 to pass along the value specified by the thermostat.
        Return the newly accepted value, or None on failure.

        This method is a coroutine
        """
        cmd = OTGW_CMD_CONTROL_SETPOINT
        ret = await self._wait_for_cmd(cmd, setpoint, timeout)
        if ret is None:
            return
        ret = int(ret)
        self._protocol.status[DATA_CONTROL_SETPOINT] = ret
        return ret

    async def set_ch_enable_bit(self, ch_bit, timeout=OTGW_DEFAULT_TIMEOUT):
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
        cmd = OTGW_CMD_CONTROL_HEATING
        ret = await self._wait_for_cmd(cmd, ch_bit, timeout)
        if ret is None:
            return
        ret = int(ret)
        self._protocol.status[DATA_MASTER_CH_ENABLED] = ret
        return ret

    async def set_ventilation(self, pct, timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Configure a ventilation setpoint override value (0-100%).
        Return the newly accepted value, or None on failure.
        @pct :int: Must be between 0 and 100.

        This method is a coroutine
        """
        if not 0 <= pct <= 100:
            return None
        cmd = OTGW_CMD_MAX_MOD
        ret = await self._wait_for_cmd(cmd, pct, timeout)
        if ret is None:
            return
        ret = int(ret)
        self._protocol.status[DATA_COOLING_CONTROL] = ret
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
        if self._protocol is not None and coro not in self._protocol._notify:
            self._protocol._notify.append(coro)
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
        if self._protocol is not None and coro in self._protocol._notify:
            self._protocol._notify.remove(coro)
            return True
        return False

    async def _wait_for_cmd(self, cmd, value, timeout=OTGW_DEFAULT_TIMEOUT):
        """
        Wrap @cmd in applicable asyncio call.

        This method is a coroutine.
        """
        return await asyncio.wait_for(self._protocol.issue_cmd(cmd, value),
                                      timeout,
                                      loop=self.loop)
