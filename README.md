[![Build Status](https://travis-ci.org/mvn23/pyotgw.svg?branch=master)](https://travis-ci.org/mvn23/pyotgw)

# pyotgw

A python library to interface with the OpenTherm Gateway

See http://otgw.tclcode.com for the hardware.

This library is written primarily for use with Home Assistant (https://www.home-assistant.io) but can be used for other purposes as well.
Parts of the code have not been thoroughly tested since my thermostat and boiler do not support all OpenTherm features. Feel free to test and contribute where you see fit.

#### Contents
- [Library Reference](#library-reference)
  - [General](#general)
  - [Getting Data](#getting-data)
  - [Methods](#methods)
- [Usage Example](#usage-example)
- [Development](#development)
- [Status Dict Structure](#status-dict-structure)

### Library Reference

#### General
pyotgw exposes its OpenThermGateway class which uses [pyserial-asyncio](https://pyserial-asyncio.readthedocs.io/en/latest/) to connect to the OpenTherm Gateway.
After initialization of the object, `OpenThermGateway.connect()` should be used to establish a connection. The object will maintain the connection in the background, using it to send commands and continuously receive updates. The received information will be cached on the object for instant availability.
The OpenThermGateway object implements a watchdog to monitor the connection for inactivity. During `OpenThermGateway.connect()`, an inactivity timeout can be set for this purpose. Normally, the OpenTherm Gateway will send a message on its serial interface approximately every second. If no messages are received for the duration of the timeout, the watchdog will trigger a reconnection attempt.

#### Getting Data
There are multiple ways to get information from pyotgw. Calling `OpenThermGateway.connect()` will request some initial information from the Gateway and return it in a dict. After this, the OpenThermGateway object exposes quite a few methods which return values that are cached on the object. There is also the option to register a callback with `OpenThermGateway.subscribe()` which will be called when any value changes.

#### Methods

---
##### OpenThermGateway()
The OpenThermGateway constructor takes no arguments and returns an empty OpenThermGateway object.

---
##### OpenThermGateway.add_alternative(_self_, alt, timeout=OTGW_DEFAULT_TIMEOUT)
Add the specified data-ID to the list of alternative commands to send to the boiler instead of a data-ID that is known to be unsupported by the boiler.
Alternative data-IDs will always be sent to the boiler in a Read-Data request message with the data-value set to zero. The table of alternative data-IDs is stored in non-volatile memory so it will persist even if the gateway has been powered off.
This method supports the following arguments:
- __alt__ The alternative data-ID to add. Values from 1 to 255 are allowed.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the ID that was added to the list, or None on failure.

This method is a coroutine.

---
##### OpenThermGateway.add_unknown_id(_self_, unknown_id, timeout=OTGW_DEFAULT_TIMEOUT)
Inform the gateway that the boiler doesn't support the specified data-ID, even if the boiler doesn't indicate that by returning an `unknown-dataID` response.
Using this command allows the gateway to send an alternative data-ID to the boiler instead.
This method supports the following arguments:
- __unknown_id__ The data-ID to mark as unsupported. Values from 1 to 255 are allowed.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the added ID, or None on failure.

This method is a coroutine.

---
##### OpenThermGateway.connect(_self_, port, timeout=5, skip_init=None)
Connect to an OpenTherm Gateway and initializes the parameters obtained from the `PS` and `PR` commands.
If called while connected, reconnect to the gateway.
All optional serial-related arguments default to the OpenTherm Gateway default settings.
This method supports the following arguments:
- __port__ The port/url on which the OpenTherm Gateway can be reached as supported by [pyserial](https://pythonhosted.org/pyserial/url_handlers.html).
- __timeout__ The inactivity timeout in seconds after which the watchdog will trigger a reconnect. Defaults to 5.
- __skip_init__ If set to True, the PS= and PR= commands are skipped and only PS=0 is sent upon the current and future connection attempts. Defaults to None, which keeps the last known setting.

Returns a status dict with all known values.

This method is a coroutine.

---
##### OpenThermGateway.disconnect(_self_)
Disconnect from the OpenTherm Gateway and clean up the object.

This method is a coroutine.

---
##### OpenThermGateway.del_alternative(_self_, alt, timeout=OTGW_DEFAULT_TIMEOUT)
Remove the specified data-ID from the list of alternative commands.
Only one occurrence is deleted. If the data-ID appears multiple times in the list of alternative commands, this command must be repeated to delete all occurrences. The table of alternative data-IDs is stored in non-volatile memory so it will persist even if the gateway has been powered off.
This method supports the following arguments:
- __alt__ The alternative data-ID to remove. Values from 1 to 255 are allowed.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the ID that was removed from the list, or None on failure.

This method is a coroutine.

---
##### OpenThermGateway.del_unknown_id(_self_, unknown_id, timeout=OTGW_DEFAULT_TIMEOUT)
Start forwarding the specified Data-ID to the boiler again.
This command resets the counter used to determine if the specified data-ID is supported by the boiler.
This method supports the following arguments:
- __unknown_id__ The data-ID to mark as supported. Values from 1 to 255 are allowed.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Return the ID that was marked as supported, or None on failure.

This method is a coroutine.

---
##### OpenThermGateway.get_reports(_self_)
Update the OpenThermGateway object with the information from all of the `PR` commands.
This method is also called from `OpenThermGateway.connect()` to populate the status dict with initial values.

Returns the full updated status dict.

This method is a coroutine.

---
##### OpenThermGateway.get_status(_self_)
Update the OpenThermGateway object with the information from the `PS` command.
This method is also called from `OpenThermGateway.connect()` to populate the status dict with initial values.

Returns the full updated status dict.

This method is a coroutine.

---
##### OpenThermGateway.set_ch_enable_bit(_self_, ch_bit, timeout=OTGW_DEFAULT_TIMEOUT)
Set or unset the `Central Heating Enable` bit.
Control the CH enable status bit when overriding the control setpoint. By default the CH enable bit is set after a call to `OpenThermGateway.set_control_setpoint()` with a value other than 0. With this method, the bit can be manipulated.
This method supports the following arguments:
- __ch_bit__ The new value for the `Central Heating Enable` bit. Can be either `0` or `1`.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Return the newly accepted value (`0` or `1`), or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_ch2_enable_bit(_self_, ch_bit, timeout=OTGW_DEFAULT_TIMEOUT)
Set or unset the `Central Heating Enable` bit for heating circuit 2.
Control the CH enable status bit when overriding the control setpoint. By default the CH enable bit is set after a call to `OpenThermGateway.set_control_setpoint()` with a value other than 0. With this method, the bit can be manipulated.
This method supports the following arguments:
- __ch_bit__ The new value for the `Central Heating Enable` bit. Can be either `0` or `1`.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Return the newly accepted value (`0` or `1`), or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_clock(_self_, date=datetime.now(), timeout=OTGW_DEFAULT_TIMEOUT)
Set the clock on the thermostat.
Change the time and day of the week of the thermostat. The gateway will send the specified time and day of the week in response to the next time and date message from the thermostat.
This method supports the following arguments:
- __date__ A datetime object containing the time and day of the week to be sent to the thermostat. Defaults to `datetime.now()`.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the accepted response from the gateway with format `HH:MM/DOW`, where DOW is a single digit: 1=Monday, 7=Sunday, or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_connection_options(_self_, **kwargs)
Set the serial connection parameters before calling connect().
Valid kwargs are 'baudrate', 'bytesize', 'parity' and 'stopbits'.
Returns True on success, False on fail or if already connected.
For more information on the kwargs see the pyserial documentation.

---
##### OpenThermGateway.set_control_setpoint(_self_, setpoint, timeout=OTGW_DEFAULT_TIMEOUT)
Set the control setpoint.
The control setpoint is the target temperature for the water in the central heating system. This method will cause the OpenTherm Gateway to manipulate the control setpoint which is sent to the boiler. Set the control setpoint to `0` to pass along the value specified by the thermostat.
This method supports the following arguments:
- __setpoint__ The new control setpoint.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the newly accepted value, or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_control_setpoint_2(_self_, setpoint, timeout=OTGW_DEFAULT_TIMEOUT)
Set the control setpoint for central heating circuit 2.
The control setpoint is the target temperature for the water in the central heating system. This method will cause the OpenTherm Gateway to manipulate the control setpoint which is sent to the boiler. Set the control setpoint to `0` to pass along the value specified by the thermostat.
This method supports the following arguments:
- __setpoint__ The new control setpoint.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the newly accepted value, or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_dhw_setpoint(_self_, temperature, timeout=OTGW_DEFAULT_TIMEOUT)
Set the domestic hot water setpoint.
The domestic hot water setpoint is the target temperature for the hot water system. Not all boilers support this command.
This method supports the following arguments:
- __temperature__ The new domestic hot water setpoint.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the newly accepted setpoint, or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_gpio_mode(_self_, gpio_id, mode, timeout=OTGW_DEFAULT_TIMEOUT)
Configure the functions of the two GPIO pins of the gateway.
Possible modes are:
- __0.__ No function, default for both ports on a freshly flashed chip.
- __1.__ Ground - A permanently low output (0V). Could be used for a power LED.
- __2.__ Vcc - A permanently high output (5V). Can be used as a short-proof power supply for some external circuitry used by the other GPIO port.
- __3.__ LED E - An additional LED if you want to present more than 4 LED functions.
- __4.__ LED F - An additional LED if you want to present more than 5 LED functions.
- __5.__ Home - Set thermostat to setback temperature when pulled low.
- __6.__ Away - Set thermostat to setback temperature when pulled high.
- __7.__ DS1820 (GPIO port B only) - Data line for a DS18S20 or DS18B20 temperature sensor used to measure the outside temperature. A 4k7 resistor should be connected between GPIO port B and Vcc.

This method supports the following arguments:
- __gpio_id__ The GPIO pin on which the mode is set. Either `A` or `B`.
- __mode__ The requested mode for the GPIO pin. Values from `0` to `7` are supported (`7` only for GPIO `B`).
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the new mode for the specified gpio, or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_hot_water_ovrd(_self_, state, timeout=OTGW_DEFAULT_TIMEOUT)
Control the domestic hot water enable option.
If the boiler has been configured to let the room unit control when to keep a small amount of water preheated, this option can influence that. A state of `0` or `1` will override the domestic hot water option `off` or `on` respectively. Any other single character disables the override and resumes normal operation.
This method supports the following arguments:
- __state__ The requested state for the domestic hot water option.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the accepted value, `A` if the override is disabled or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_led_mode(_self_, led_id, mode, timeout=OTGW_DEFAULT_TIMEOUT)
Set the mode of one of the LEDs.
Configure the functions of the six LEDs (A-F) that can optionally be connected to pins RB3/RB4/RB6/RB7 and the GPIO pins of the PIC.
Possible modes are:
- __R__ Receiving an Opentherm message from the thermostat or boiler
- __X__ Transmitting an Opentherm message to the thermostat or boiler
- __T__ Transmitting or receiving a message on the master interface
- __B__ Transmitting or receiving a message on the slave interface
- __O__ Remote setpoint override is active
- __F__ Flame is on
- __H__ Central heating is on
- __W__ Hot water is on
- __C__ Comfort mode (Domestic Hot Water Enable) is on
- __E__ Transmission error has been detected
- __M__ Boiler requires maintenance
- __P__ Raised power mode active on thermostat interface.

This method supports the following arguments:
- __led_id__ The LED for which the mode is set. Must be a character in the range `A-F`.
- __mode__ The requested state for the LED. Must be one of `R`, `X`, `T`, `B`, `O`, `F`, `H`, `W`, `C`, `E`, `M` or `P`.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the new mode for the specified LED, or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_max_ch_setpoint(_self_, temperature, timeout=OTGW_DEFAULT_TIMEOUT)
Set the maximum central heating water setpoint.
Not all boilers support this option.

This method supports the following arguments:
- __temperature__ The new maximum central heating water setpoint.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the newly accepted setpoint, or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_max_relative_mod(_self_, max_mod, timeout=OTGW_DEFAULT_TIMEOUT)
Set the maximum relative modulation level.
Override the maximum relative modulation from the thermostat. Valid values are 0 through 100. Clear the setting by specifying a non-numeric value.
This method supports the following arguments:
- __temperature__ The new maximum central heating water setpoint.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the newly accepted value, `-` if a previous value was cleared, or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_mode(_self_, mode, timeout=OTGW_DEFAULT_TIMEOUT)
Set the operating mode of the gateway.
The operating mode can be either `gateway` or `monitor` mode. This method can also be used to reset the OpenTherm Gateway.
This method supports the following arguments:
- __mode__ The mode to be set on the gateway. Can be `0` or `OTGW_MODE_MONITOR` for `monitor` mode, `1` or `OTGW_MODE_GATEWAY` for `gateway mode, or `OTGW_MODE_RESET` to reset the gateway.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Return the newly activated mode, or the full renewed status dict after a reset.

This method is a coroutine.

---
##### OpenThermGateway.set_outside_temp(_self_, temp, timeout=OTGW_DEFAULT_TIMEOUT)
Set the outside temperature.
Configure the outside temperature to send to the thermostat. Allowed values are between -40.0 and +64.0, although thermostats may not display the full range. Specify a value above 64 (suggestion: 99) to clear a previously configured value.
This method supports the following arguments:
- __temp__ The outside temperature to provide to the gateway.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the accepted value on success, `-` if a previously configured value has been cleared or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_setback_temp(_self_, sb_temp, timeout=OTGW_DEFAULT_TIMEOUT)
Set the setback temperature.
Configure the setback temperature to use in combination with the GPIO functions `home`(5) and `away`(6).
This method supports the following arguments:
- __sb_temp__ The new setback temperature.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the new setback temperature, or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_target_temp(_self_, temp, temporary=True, timeout=OTGW_DEFAULT_TIMEOUT)
Set the room setpoint.
Configure the thermostat setpoint and specify whether or not it may be overridden by a programmed change.
This method supports the following arguments:
- __temp__ The new room setpoint. Will be formatted to 1 decimal.
- __temporary__ Whether or not the thermostat program may override the room setpoint. Either `True` or `False`. Defaults to `True`.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the newly accepted room setpoint, or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_temp_sensor_function(_self_, func, timeout=v.OTGW_DEFAULT_TIMEOUT):
Set the function of the temperature sensor that can be attached to the gateway.
This method supports the following arguments:
- __func__ The new temperature sensor function. Either `O` for `Outside Air Temperature` or `R` for `Return Water Temperature`.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Returns the newly accepted temperature sensor function or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.set_ventilation(_self_, pct, timeout=OTGW_DEFAULT_TIMEOUT)
Set the ventilation setpoint.
Configure a ventilation setpoint override value (0-100%).
This method supports the following arguments:
- __pct__ The new ventilation setpoint. Must be between `0` and `100`.
- __timeout__ The timeout for the request. Defaults to OTGW_DEFAULT_TIMEOUT (3 seconds).

Return the newly accepted value, or `None` on failure.

This method is a coroutine.

---
##### OpenThermGateway.send_transparent_command(_self_, cmd, state, timeout=OTGW_DEFAULT_TIMEOUT)
Send a transparent command.
Sends custom commands through a transparent interface.
Check https://otgw.tclcode.com/firmware.html for supported commands.
This method supports the following arguments:
- __cmd__ The supported command e.g. `SC` (set time/day).
- __state__ The command argument e.g. `23:59/4` (the current time/day)

Returns the gateway response, which should be equal __state__.

This method is a coroutine.

---
##### OpenThermGateway.subscribe(_self_, coro)
Subscribe to status updates from the Opentherm Gateway.
The subscribed coroutine must have the following signature:
```
async def coro(status)
```
Where `status` will be the full status dict containing the last known information from the OpenTherm Gateway.
This method supports the following arguments:
- __coro__ A coroutine which will be called whenever a status change occurs.

Returns `True` on success, `False` if the coroutine is already subscribed.

---
##### OpenThermGateway.unsubscribe(_self_, coro)
Unsubscribe from status updates from the Opentherm Gateway.
The supplied coroutine must have been subscribed with `OpenThermGateway.subscribe()` before.
This method supports the following arguments:
- __coro__ The coroutine which will be unsubscribed.

Returns `True` on success, `False` if the coroutine was not subscribed before.

---


### Usage Example
```python
import asyncio
from pyotgw import OpenThermGateway

PORT = '/dev/ttyUSB0'


async def print_status(status):
  """Receive and print status."""
  print("Received a status update:\n{}".format(status))


async def connect_and_subscribe():
  """Connect to the OpenTherm Gateway and subscribe to status updates."""

  # Create the object
  gw = OpenThermGateway()

  # Connect to OpenTherm Gateway on PORT
  status = await gw.connect(PORT)
  print("Initial status after connecting:\n{}".format(status))

  # Subscribe to updates from the gateway
  if not gw.subscribe(print_status):
    print("Could not subscribe to status updates.")

  # Keep the event loop alive...
  while True:
    await asyncio.sleep(1)


# Run the connect_and_subscribe coroutine.
try:
  asyncio.run(connect_and_subscribe())
except KeyboardInterrupt:
  print("Exiting")

```

### Development
We use pre-commit to ensure a consistent code style, so `pip install pre_commit` and run
```
pre-commit install
```
in the repository.

### Status Dict Structure
The full possible status dict with some example values looks like below. Note that not all keys will always be present and that the presence of a key does not guarantee that it contains useful information.

```python
{
    vars.BOILER: {
        vars.DATA_CH_PUMP_HOURS: 15010,
        vars.DATA_CH_PUMP_STARTS: 43832,
        vars.DATA_CH_WATER_PRESS: 0.0,
        vars.DATA_CH_WATER_TEMP: 47.2,
        vars.DATA_CH_WATER_TEMP_2: 0.0,
        vars.DATA_CONTROL_SETPOINT: 44.0,
        vars.DATA_CONTROL_SETPOINT_2: 0.0,
        vars.DATA_COOLING_CONTROL: 0,
        vars.DATA_DHW_BURNER_HOURS: 411,
        vars.DATA_DHW_BURNER_STARTS: 34296,
        vars.DATA_DHW_FLOW_RATE: 0.0,
        vars.DATA_DHW_PUMP_HOURS: 250,
        vars.DATA_DHW_PUMP_STARTS: 9424,
        vars.DATA_DHW_SETPOINT: 0.0,
        vars.DATA_DHW_TEMP: 0.0,
        vars.DATA_DHW_TEMP_2: 0.0,
        vars.DATA_EXHAUST_TEMP: 0,
        vars.DATA_MASTER_CH2_ENABLED: 0,
        vars.DATA_MASTER_CH_ENABLED: 1,
        vars.DATA_MASTER_COOLING_ENABLED: 0,
        vars.DATA_MASTER_DHW_ENABLED: 1,
        vars.DATA_MASTER_MEMBERID: 0,
        vars.DATA_MASTER_OTC_ENABLED: 0,
        vars.DATA_MASTER_OT_VERSION: 0.0,
        vars.DATA_MASTER_PRODUCT_TYPE: 0,
        vars.DATA_MASTER_PRODUCT_VERSION: 0,
        vars.DATA_MAX_CH_SETPOINT: 75.0,
        vars.DATA_OEM_DIAG: 0,
        vars.DATA_OUTSIDE_TEMP: 0.0,
        vars.DATA_REL_MOD_LEVEL: 0.0,
        vars.DATA_REMOTE_RW_DHW: 1,
        vars.DATA_REMOTE_RW_MAX_CH: 1,
        vars.DATA_REMOTE_TRANSFER_DHW: 1,
        vars.DATA_REMOTE_TRANSFER_MAX_CH: 1,
        vars.DATA_RETURN_WATER_TEMP: 0.0,
        vars.DATA_ROOM_SETPOINT: 20.0,
        vars.DATA_ROOM_SETPOINT_2: 0.0,
        vars.DATA_ROOM_SETPOINT_OVRD: 20.0,
        vars.DATA_ROOM_TEMP: 19.62,
        vars.DATA_ROVRD_AUTO_PRIO: 0,
        vars.DATA_ROVRD_MAN_PRIO: 1,
        vars.DATA_SLAVE_AIR_PRESS_FAULT: 0,
        vars.DATA_SLAVE_CH2_ACTIVE: 0,
        vars.DATA_SLAVE_CH2_PRESENT: 0,
        vars.DATA_SLAVE_CH_ACTIVE: 1,
        vars.DATA_SLAVE_CH_MAX_SETP: 75,
        vars.DATA_SLAVE_CH_MIN_SETP: 20,
        vars.DATA_SLAVE_CONTROL_TYPE: 1,
        vars.DATA_SLAVE_COOLING_ACTIVE: 0,
        vars.DATA_SLAVE_COOLING_SUPPORTED: 0,
        vars.DATA_SLAVE_DHW_ACTIVE: 0,
        vars.DATA_SLAVE_DHW_CONFIG: 0,
        vars.DATA_SLAVE_DHW_MAX_SETP: 60,
        vars.DATA_SLAVE_DHW_MIN_SETP: 40,
        vars.DATA_SLAVE_DHW_PRESENT: 1,
        vars.DATA_SLAVE_DIAG_IND: 0,
        vars.DATA_SLAVE_FAULT_IND: 0,
        vars.DATA_SLAVE_FLAME_ON: 1,
        vars.DATA_SLAVE_GAS_FAULT: 0,
        vars.DATA_SLAVE_LOW_WATER_PRESS: 0,
        vars.DATA_SLAVE_MASTER_LOW_OFF_PUMP: 0,
        vars.DATA_SLAVE_MAX_CAPACITY: 0,
        vars.DATA_SLAVE_MAX_RELATIVE_MOD: 100.0,
        vars.DATA_SLAVE_MEMBERID: 0,
        vars.DATA_SLAVE_MIN_MOD_LEVEL: 0,
        vars.DATA_SLAVE_OEM_FAULT: 0,
        vars.DATA_SLAVE_OT_VERSION: 0.0,
        vars.DATA_SLAVE_PRODUCT_TYPE: 0,
        vars.DATA_SLAVE_PRODUCT_VERSION: 0,
        vars.DATA_SLAVE_REMOTE_RESET: 0,
        vars.DATA_SLAVE_SERVICE_REQ: 0,
        vars.DATA_SLAVE_WATER_OVERTEMP: 0,
        vars.DATA_SOLAR_COLL_TEMP: 0.0,
        vars.DATA_SOLAR_STORAGE_TEMP: 0.0,
        vars.DATA_TOTAL_BURNER_HOURS: 0,
        vars.DATA_TOTAL_BURNER_STARTS: 0,
    },
    vars.OTGW: {
        vars.OTGW_ABOUT: 'OpenTherm Gateway 4.2.5',
        vars.OTGW_BUILD: '17:59 20-10-2015',
        vars.OTGW_CLOCKMHZ: '4 MHz',
        vars.OTGW_DHW_OVRD: '1',
        vars.OTGW_GPIO_A: 0,
        vars.OTGW_GPIO_A_STATE: 0,
        vars.OTGW_GPIO_B: 0,
        vars.OTGW_GPIO_B_STATE: 0,
        vars.OTGW_IGNORE_TRANSITIONS: 1,
        vars.OTGW_LED_A: 'F',
        vars.OTGW_LED_B: 'X',
        vars.OTGW_LED_C: 'O',
        vars.OTGW_LED_D: 'M',
        vars.OTGW_LED_E: 'P',
        vars.OTGW_LED_F: 'C',
        vars.OTGW_MODE: 'G',
        vars.OTGW_OVRD_HB: 1,
        vars.OTGW_SB_TEMP: 16.0,
        vars.OTGW_SETP_OVRD_MODE: 'T',
        vars.OTGW_SMART_PWR: 'Low power',
        vars.OTGW_THRM_DETECT: 'D',
        vars.OTGW_VREF: 3,
    },
    vars.THERMOSTAT: {
        vars.DATA_CH_PUMP_HOURS: 15010,
        vars.DATA_CH_PUMP_STARTS: 43832,
        vars.DATA_CH_WATER_PRESS: 0.0,
        vars.DATA_CH_WATER_TEMP: 47.2,
        vars.DATA_CH_WATER_TEMP_2: 0.0,
        vars.DATA_CONTROL_SETPOINT: 44.0,
        vars.DATA_CONTROL_SETPOINT_2: 0.0,
        vars.DATA_COOLING_CONTROL: 0,
        vars.DATA_DHW_BURNER_HOURS: 411,
        vars.DATA_DHW_BURNER_STARTS: 34296,
        vars.DATA_DHW_FLOW_RATE: 0.0,
        vars.DATA_DHW_PUMP_HOURS: 250,
        vars.DATA_DHW_PUMP_STARTS: 9424,
        vars.DATA_DHW_SETPOINT: 0.0,
        vars.DATA_DHW_TEMP: 0.0,
        vars.DATA_DHW_TEMP_2: 0.0,
        vars.DATA_EXHAUST_TEMP: 0,
        vars.DATA_MASTER_CH2_ENABLED: 0,
        vars.DATA_MASTER_CH_ENABLED: 1,
        vars.DATA_MASTER_COOLING_ENABLED: 0,
        vars.DATA_MASTER_DHW_ENABLED: 1,
        vars.DATA_MASTER_MEMBERID: 0,
        vars.DATA_MASTER_OTC_ENABLED: 0,
        vars.DATA_MASTER_OT_VERSION: 0.0,
        vars.DATA_MASTER_PRODUCT_TYPE: 0,
        vars.DATA_MASTER_PRODUCT_VERSION: 0,
        vars.DATA_MAX_CH_SETPOINT: 75.0,
        vars.DATA_OEM_DIAG: 0,
        vars.DATA_OUTSIDE_TEMP: 0.0,
        vars.DATA_REL_MOD_LEVEL: 0.0,
        vars.DATA_REMOTE_RW_DHW: 1,
        vars.DATA_REMOTE_RW_MAX_CH: 1,
        vars.DATA_REMOTE_TRANSFER_DHW: 1,
        vars.DATA_REMOTE_TRANSFER_MAX_CH: 1,
        vars.DATA_RETURN_WATER_TEMP: 0.0,
        vars.DATA_ROOM_SETPOINT: 20.0,
        vars.DATA_ROOM_SETPOINT_2: 0.0,
        vars.DATA_ROOM_SETPOINT_OVRD: 20.0,
        vars.DATA_ROOM_TEMP: 19.62,
        vars.DATA_ROVRD_AUTO_PRIO: 0,
        vars.DATA_ROVRD_MAN_PRIO: 1,
        vars.DATA_SLAVE_AIR_PRESS_FAULT: 0,
        vars.DATA_SLAVE_CH2_ACTIVE: 0,
        vars.DATA_SLAVE_CH2_PRESENT: 0,
        vars.DATA_SLAVE_CH_ACTIVE: 1,
        vars.DATA_SLAVE_CH_MAX_SETP: 75,
        vars.DATA_SLAVE_CH_MIN_SETP: 20,
        vars.DATA_SLAVE_CONTROL_TYPE: 1,
        vars.DATA_SLAVE_COOLING_ACTIVE: 0,
        vars.DATA_SLAVE_COOLING_SUPPORTED: 0,
        vars.DATA_SLAVE_DHW_ACTIVE: 0,
        vars.DATA_SLAVE_DHW_CONFIG: 0,
        vars.DATA_SLAVE_DHW_MAX_SETP: 60,
        vars.DATA_SLAVE_DHW_MIN_SETP: 40,
        vars.DATA_SLAVE_DHW_PRESENT: 1,
        vars.DATA_SLAVE_DIAG_IND: 0,
        vars.DATA_SLAVE_FAULT_IND: 0,
        vars.DATA_SLAVE_FLAME_ON: 1,
        vars.DATA_SLAVE_GAS_FAULT: 0,
        vars.DATA_SLAVE_LOW_WATER_PRESS: 0,
        vars.DATA_SLAVE_MASTER_LOW_OFF_PUMP: 0,
        vars.DATA_SLAVE_MAX_CAPACITY: 0,
        vars.DATA_SLAVE_MAX_RELATIVE_MOD: 100.0,
        vars.DATA_SLAVE_MEMBERID: 0,
        vars.DATA_SLAVE_MIN_MOD_LEVEL: 0,
        vars.DATA_SLAVE_OEM_FAULT: 0,
        vars.DATA_SLAVE_OT_VERSION: 0.0,
        vars.DATA_SLAVE_PRODUCT_TYPE: 0,
        vars.DATA_SLAVE_PRODUCT_VERSION: 0,
        vars.DATA_SLAVE_REMOTE_RESET: 0,
        vars.DATA_SLAVE_SERVICE_REQ: 0,
        vars.DATA_SLAVE_WATER_OVERTEMP: 0,
        vars.DATA_SOLAR_COLL_TEMP: 0.0,
        vars.DATA_SOLAR_STORAGE_TEMP: 0.0,
        vars.DATA_TOTAL_BURNER_HOURS: 0,
        vars.DATA_TOTAL_BURNER_STARTS: 0,
    }
}
```
