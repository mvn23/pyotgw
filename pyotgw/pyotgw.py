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
'''
pyotgw is a library to interface with the OpenTherm Gateway.          
'''


import asyncio
import pyotgw.protocol as otgw
import serial
import serial_asyncio

from datetime import datetime
from pyotgw.vars import *

class pyotgw:
    
    def __init__(self):
        '''
        Create a pyotgw object.
        '''
        return
    
    
    async def connect(self, loop, port, baudrate=9600,
                      bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                      stopbits=serial.STOPBITS_ONE, timeout=30):
        '''
        Connect to Opentherm Gateway at @port.
        
        This method is a coroutine
        '''
        transport, protocol = await serial_asyncio.create_serial_connection(
            loop, otgw.protocol, port, baudrate, bytesize, parity, stopbits, timeout)
        self._transport = transport
        self._protocol = protocol
        asyncio.ensure_future(protocol._report())

        
    async def get_room_temp(self):
        '''
        Get the current room temperature.
        
        This method is a coroutine
        '''
        return self._protocol.status.get(DATA_ROOM_TEMP)
    
    
    async def get_target_temp(self):
        '''
        Get the target temperature.
        
        This method is a coroutine
        '''
        if self._protocol.status.get(DATA_ROOM_SETPOINT_OVRD, 0) > 0:
            return self._protocol.status.get(DATA_ROOM_SETPOINT_OVRD)
        return self._protocol.status.get(DATA_ROOM_SETPOINT)
    
    
    async def set_target_temp(self, temp, temporary=True,
                              timeout=OTGW_DEFAULT_TIMEOUT):
        '''
        Set the target temperature.
        kwarg @temporary specifies whether or not the thermostat
            program may override this temperature.
        
        This method is a coroutine
        '''
        cmd = (OTGW_CMD_TARGET_TEMP if temporary
               else OTGW_CMD_TARGET_TEMP_CONST)
        value = '{:2.1f}'.format(temp)
        ret = float(await asyncio.wait_for(
            self._protocol.issue_cmd(cmd, value), timeout))
        self._protocol.status[DATA_ROOM_SETPOINT_OVRD] = (ret if ret > 0
                                                               else None)
        
    
    async def get_outside_temp(self):
        '''
        Returns the outside temperature as known in the gateway.
        
        This method is a coroutine
        '''
        return self._protocol.status.get(DATA_OUTSIDE_TEMP)
    
    
    async def set_outside_temp(self, temp, timeout=OTGW_DEFAULT_TIMEOUT):
        '''
        Provide an outside air temperature to the thermostat.
        Returns the accepted value or None if a previous value has been
        unset (@temp > 64)
        
        This method is a coroutine
        '''
        cmd = OTGW_CMD_OUTSIDE_TEMP
        value = '{:2.1f}'.format(temp)
        ret = float(await asyncio.wait_for(
            self._protocol.issue_cmd(cmd, value), timeout))
        self._protocol.status[DATA_OUTSIDE_TEMP] = (None if ret > 64 else ret)
        return self._protocol.status[DATA_OUTSIDE_TEMP]
    
    
    async def set_clock(self, date=datetime.now(),
                        timeout=OTGW_DEFAULT_TIMEOUT):
        '''
        Set the time and day of week to be sent to the thermostat.
        @date is a :datetime: object which defaults to now()
        Returns the response from the gateway with format HH:MM/DOW,
        where DOW is a single digit: 1=Monday, 7=Sunday.
        
        This method is a coroutine
        '''
        cmd = OTGW_CMD_SET_CLOCK
        value = "{}/{}".format(date.strftime('%H:%M'), date.isoweekday())
        ret = await asyncio.wait_for(self._protocol.issue_cmd(cmd, value),
                                     timeout)
        return ret
        
    
    async def get_hot_water_ovrd(self):
        '''
        Returns the current hot water override mode if set, otherwise
        None.
        
        This method is a coroutine
        '''
        return self._protocol.status.get(OTGW_DHW_OVRD)
    
    
    async def get_status(self):
        '''
        Updates the pyotgw object with the information from the PR and
        PS commands and return the complete status dict.
        
        This method is a coroutine
        '''
        cmd = OTGW_CMD_REPORT
        for value in OTGW_REPORTS.keys():
            ret = await asyncio.wait_for(self._protocol.issue_cmd(cmd, value))
            
            
            #if isinstance(OTGW_REPORTS[value], list):
                
    
    async def set_hot_water_ovrd(self, state, timeout=OTGW_DEFAULT_TIMEOUT):
        '''
        Set the hot water override mode of the gateway.
        @state should be 0 or 1 to enable the override in off or on
        state, or any other single character to disable the override.
        Returns the accepted value or None if the override was
        disabled.
        
        This method is a coroutine
        '''
        cmd = OTGW_CMD_HOT_WATER
        ret = await asyncio.wait_for(self._protocol.issue_cmd(cmd, state),
                                     timeout)
        self._protocol.status[OTGW_DHW_OVRD] = (int(ret) if ret
                                                    in ['0', '1'] else None)
        return self._protocol.status[OTGW_DHW_OVRD]

    
    async def subscribe(self, coro):
        '''
        Subscribe to status updates from the Opentherm Gateway.
        Can only be used after connect()
        @coro is a coroutine which will be called with a single
        argument (status) when a status change occurs.
        
        This method is a coroutine
        '''
        if (coro not in self._protocol._notify
                and self._protocol is not None):
            self._protocol._notify.append(coro)
            return True
        return False
    

    async def unsubscribe(self, coro):
        '''
        Unsubscribe from status updates from the Opentherm Gateway.
        Can only be used after connect()
        @coro is a coroutine which has been subscribed with sunscribe()
        earlier.
        
        This method is a coroutine
        '''
        if coro in self._protocol._notify and self._protocol is not None:
            self._protocol._notify.remove(coro)
            return True
        return False

        
