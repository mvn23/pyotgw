# pyotgw Changelog

### 2.1.1
- Fix boiler side room_setpoint not updating

### 2.1.0
- Add skip_init feature to OpenThermGateway.connect()
- Add test case for skip_init feature

### 2.0.3
- Fix watchdog reconnect logic
- Use deepcopy when submitting status updates to the queue
- Fix tests for watchdog logic

### 2.0.2
- Only log unexpected disconnects

### 2.0.1
- Fix bug in watchdog reconnect logic
- Add test case for watchdog reconnect logic
- Add documentation for OpenThermGateway.set_connection_options() to README.md
- Update usage example in README.md

### 2.0.0
- Add CHANGELOG.md
- Make protocol.disconnect synchronous
- Update pylint config in tox.ini and add pylint to travis
- Remove unimplemented methods from OpenThermGateway class
- Update pre-commit, CI and Travis config
- Drop support for python 3.7
- Rename pyotgw class to OpenThermGateway
- Remove loop argument from OpenThermGateway.connect()
- Remove loop parameters from all classes
- Add CI workflow
- Refactor status management into a StatusManager class (pyotgw/status.py)
- Refactor connection management into a ConnectionManager class (pyotgw/connection.py)
- Refactor connection watchdog into a ConnectionWatchdog class (pyotgw/connection.py)
- Refactor protocol message processing into MessageProcessor (pyotgw/messageprocessor.py)
- Refactor command processing into CommandProcessor (pyotgw/commandprocessor.py)
- Further improve message handling
- Remove licence headers
- Add test suite
- Update pre-commit hooks
- Address pre-commit issues
- Prepare pylint integration
- Support python 3.8-3.10 in pre-commit hooks
- Refactor protocol._process_msg() message parsing
- Refactor protocol.active into a function
- Convert protocol.setup_watchdog() and protocol.set_update_cb() to synchronous functions
- Don't use loop.create_task() for task.cancel() calls
- Change hex values logging to uppercase
- Fix get_reports() firmware versions for commands
- Poll GPIO states only when either GPIO has mode 0 (input)
- Fix attempt_connect() return value
- Handle non-responsive gateway serial connection (fixes #30)
- Increase retry_timeout with every unsuccessful connection attempt up to MAX_RETRY_TIMEOUT
- Remove loop arguments that were deprecated in python 3.8, removed in python 3.10 (fixes #29)
- Small fixes and optimizations

### 1.1b1
- Add features and their documentation for firmware v5.0
- Add support for firmware 5.0 (#27)
- SerialTransport.write() does not return amount of bytes written

### 1.0b2
- Fix for OpenTherm Gateway 4.2.8.1
- Change log level and message for E* messages from the gateway.

### 1.0b1
- Copy DEFAULT_STATUS instead of editing it
- Update README.md

### 1.0b0
- Avoid sending updates twice for related changes to status (#22)
- Separate thermostat, boiler and otgw status (#20)

### 0.6b1
- Improve connection routine
- Cleanup after unfinished connection attempt in disconnect()
- Make SerialTransport.write() non-blocking
- Add debug output to write operations
- Add Python version to setup.py (#15)
- Add Travis to the repository (#14)

### 0.6b0
- Send empty report on connection loss
- Fix debug output for python <3.8
- Add debug logging to watchdog
- Fix commands while not connected.
- Add pre-commit and use several linters to ensure a consistent code style (#12)

### 0.5b1
- Fix iSense quirk handling bug
- Improve disconnect handling, add more debug logging.

### 0.5b0
- Add pyotgw.disconnect() method.

### 0.4b4
- Fix bug during disconnect handling (#7)
- Remove unused import
- Improve log messages
- Add more debug logging
- Flake8 fixes
- Only set status[DATA_ROOM_SETPOINT_OVRD] immediately if no iSense thermostat is detected
- Put copies of status dict in update queue

### 0.4b3
- Work around iSense quirk with MSG_TROVRD (ID 9)
- Make _process_msg async.
- Improve queue emptying - don't try-except QueueEmpty
- Move special message processing from _dissect_msg to _process_msg
- Update expect regex for command processing.
- Fix false clearing of room setpoint override if boiler supports MSG_TROVRD.
- Deal with DecodeErrors on received data.

### 0.4b2
- Update setup.py with new filename for README.md
- Improve connection establishing routine.
- Use a while loop instead of recursion on connect().
- Fix broken reconnect logic (#5)
- Updated documentation
- Renamed pyotgw.send_report() to pyotgw._send_report as it is only used internally.
- Renamed arguments to not-implemented functions.
- Rename README to README.md

### 0.4b1
- Fix 100% CPU issue when able to connect but not receiving data
- Add Lock to _inform_watchdog to prevent losing track of watchdog tasks due to concurrent calls
- Improve handling of PR commands

### 0.4b0
- Improved connection error handling
- Fixed leaked Tasks during reconnect
- Add and remove some debug logging
- Fix callback listeners after reconnect.
- Move reporting system from protocol to pyotgw.
- Handle disconnects and reconnect automatically
- Retry commands up to 3 times
- Change ensure_future to create_task where appropriate
- Some match changes (is to ==)

### 0.3b1.
- Fix a bug where manual action after remote override would not be detected properly by the library.

### 0.3b0
- Ignore 'A' messages as they cause trouble and are there just to keep the thermostat happy.
- Fix bug in set_control_setpoint, now cast correctly.
- Keep the status dict for ourselves, provide copies to clients.
- Improved error handling and messages.
- Streamline status updates
- Fix bug when clearing some variables
- Fix flake findings
- Remove date from status updates
- Fix configuring GPIOs and add polling for their state (no push available).
- Fix reset command.
- Use logging instead of print().
- Fix calling methods/properties before connect().
- Improve command error handling.
- Update import syntax and order.
- Update README
- Various bugfixes.

### 0.2b1
- Move handling of status values updates to dedicated functions
- Rename CH_BURNER vars to BURNER to reflect their actual meaning
- Fix data types for vars (cast to type where needed)

### 0.2b0
- General code cleanup and some rewrites.
- Syntax corrections according flake8.
- Update README
- Fixed a small bug with room setpoint override
- Promoted to beta release
- Updated setup.py with github url
- Renamed license file
- Added docstrings to functions and classes
- Fixed a bug with the Remote Override functionality
- Some fixes and additions
- Implemented more commands, improved loop handling

### 0.1a0
- Initial commit, monitoring support and some commands implemented
