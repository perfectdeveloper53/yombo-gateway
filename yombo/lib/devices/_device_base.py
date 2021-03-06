# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/libraries/devices>`_

Base device functions. Should not be directly inherited by other device types, instead
inherit "Device" from _device.py.

This device inherits from _device_attributes.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2018 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from collections import OrderedDict
from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants.commands import (COMMAND_COMPONENT_CALLED_BY, COMMAND_COMPONENT_COMMAND,
    COMMAND_COMPONENT_COMMAND_ID, COMMAND_COMPONENT_DEVICE, COMMAND_COMPONENT_DEVICE_COMMAND,
    COMMAND_COMPONENT_DEVICE_ID, COMMAND_COMPONENT_INPUTS, COMMAND_COMPONENT_PIN,
    COMMAND_COMPONENT_REQUEST_ID, COMMAND_COMPONENT_SOURCE, COMMAND_COMPONENT_SOURCE_GATEWAY_ID,
    COMMAND_COMPONENT_AUTH_ID, COMMAND_COMPONENT_REQUESTING_SOURCE, COMMAND_COMPONENT_REPORTING_SOURCE,
    COMMAND_COMPONENT_ENERGY_TYPE, COMMAND_COMPONENT_ENERGY_USAGE, COMMAND_COMPONENT_HUMAN_MESSAGE,
    COMMAND_COMPONENT_HUMAN_STATUS)
from yombo.core.exceptions import YomboPinCodeError, YomboWarning
from yombo.core.log import get_logger
from yombo.lib.commands import Command  # used only to determine class type
from yombo.utils import (random_string, do_search_instance, dict_merge, dict_diff,
    generate_source_string, data_pickle)
from yombo.utils.hookinvoke import global_invoke_all

# Import local items
# from ._device_attributes import Device_Attributes
from ._device_state import Device_State

logger = get_logger("library.devices.device")


class Device_Base(object):
    """
    The base device contains all the core functions for devices. This calls should only be
    inherited by "Device" class.

    The primary functions developers should use are:
        * :py:meth:`available_commands <Device.available_commands>` - List available commands for a device.
        * :py:meth:`command <Device.command>` - Send a command to a device.
        * :py:meth:`device_command_received <Device.device_command_received>` - Called by any module processing a command.
        * :py:meth:`device_command_pending <Device.device_command_pending>` - When a module needs more time.
        * :py:meth:`device_command_failed <Device.device_command_failed>` - When a module is unable to process a command.
        * :py:meth:`device_command_done <Device.device_command_done>` - When a command has completed..
        * :py:meth:`energy_get_usage <Device.energy_get_usage>` - Get current energy being used by a device.
        * :py:meth:`get_status <Device.get_status>` - Get a latest device status object.
        * :py:meth:`set_status <Device.set_state>` - Set the device status.
    """
    def command(self, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None,
                auth=None, inputs=None, not_after=None, callbacks=None, idempotence=None, **kwargs):
        """
        Tells the device to a command. This in turn calls the hook _device_command_ so modules can process the command
        if they are supposed to.

        If a pin is required, "pin" must be included as one of the arguments. All \\*\\*kwargs are sent with the
        hook call.

        :raises YomboWarning: Raised when:

            - delay or max_delay is not a float or int.

        :raises YomboPinCodeError: Raised when:

            - pin is required but not recieved one.
            - cmd doesn't exist

        :param cmd: Command ID or Label to send.
        :type cmd: str
        :param pin: A pin to check.
        :type pin: str
        :param request_id: Request ID for tracking. If none given, one will be created_at.
        :type request_id: str
        :param not_before: An epoch time when the command should be sent. Not to be combined with "delay".
        :type not_before: int or float
        :param delay: How many seconds to delay sending the command. Not to be combined with "not_before"
        :type delay: int or float
        :param max_delay: How many second after the "delay" or "not_before" can the command be send. This can occur
            if the system was stopped when the command was supposed to be send.
        :type max_delay: int or float
        :param auth: An auth instance (with authmixin).
        :type auth: instance
        :param inputs: A list of dictionaries containing the "input_type_id" and any supplied "value".
        :type inputs: dict
        :param not_after: An epoch time when the command should be discarded.
        :type not_after: int or float
        :param callbacks: A dictionary of callbacks
        :type callbacks: dict
        :param kwargs: Any additional named arguments will be sent to the module for processing.
        :type kwargs: named arguments
        :return: The request id.
        :rtype: str
        """
        logger.debug("device ({label}), comand starting...", label=self.full_label)
        if self.status != 1:
            raise YomboWarning("Device cannot be used, it's not enabled.")

        if self.pin_required == 1:
            if pin is None:
                raise YomboPinCodeError("'pin' is required, but missing.")
            else:
                if self.pin_code != pin:
                    raise YomboPinCodeError("'pin' supplied is incorrect.")
        if self.is_controllable is False:
                raise YomboWarning("This device cannot be controlled. Typically because it's an input type device.")

        if "control_method" not in kwargs:
            kwargs["control_method"] = "direct"
        if self.is_direct_controllable == 0 and kwargs["control_method"] == "direct":
                raise YomboWarning("This device cannot be directly controlled. Set 'control_method'.")

        device_command = {
            "device": self,
            "pin": pin,
            "idempotence": idempotence,
        }

        if isinstance(cmd, Command):
            command = cmd
        else:
            command = self._Parent._Commands.get(cmd)
        if command.machine_label == "toggle":
            command = self.get_toggle_command()
        device_command["command"] = command

        # logger.debug("device::command kwargs: {kwargs}", kwargs=kwargs)
        # logger.debug("device::command requested_by: {requested_by}", requested_by=requested_by)

        # This will raise YomboNoAccess exception if user doesn't have access.
        if auth is None:
            logger.info("Device command received for device {label}, but no user specified."
                        " This will generate errors in future versions.",
                        label=self.full_label)
        else:
            # This validates access. If invalid raises YomboNoAccess.
            self._Parent._Users.has_access(auth, "device", self.device_id, "control")

        if auth is None:  # future versions will fail already...
            device_command["auth_id"] = "Unknown"
        else:
            device_command["auth_id"] = auth.safe_display


        if COMMAND_COMPONENT_REQUESTING_SOURCE in kwargs:
            device_command[COMMAND_COMPONENT_REQUESTING_SOURCE] = kwargs[COMMAND_COMPONENT_REQUESTING_SOURCE]
        else:
            device_command[COMMAND_COMPONENT_REQUESTING_SOURCE] = generate_source_string(gateway_id=self.gateway_id)

        if str(command.command_id) not in self.available_commands():
            logger.warn("Requested command: {command_id}, but only have: {ihave}",
                        command_id=command.command_id, ihave=self.available_commands())
            raise YomboWarning("Invalid command requested for device.", errorno=103)

        cur_time = time()
        device_command["created_at"] = cur_time

        persistent_request_id = kwargs.get("persistent_request_id", None)
        device_command["persistent_request_id"] = persistent_request_id

        if persistent_request_id is not None:  # cancel any previous device requests for this persistent id.
            for search_request_id, search_device_command in self._Parent.device_commands.items():
                if search_device_command.persistent_request_id == persistent_request_id:
                    search_device_command.cancel(message="This device command was superseded by a new persistent request.")

        if request_id is None:
            request_id = random_string(length=14)

        device_command["request_id"] = request_id

        if delay is not None or not_before is not None:  # if we have a delay, make sure we have required items
            if max_delay is None and not_after is None:
                logger.info("max_delay and not_after missing when calling with delay or not_before. Setting to 60 seconds.")
                max_delay = 60
            if max_delay is not None and not_after is not None:
                raise YomboWarning("'max_delay' and 'not_after' cannot be set at the same time.")

            # Determine when to call the command
            if not_before is not None:
                if isinstance(not_before, str):
                    try:
                        not_before = float(not_before)
                    except:
                        raise YomboWarning("'not_before' time should be epoch second in the future as an int, float, or parsable string.")
                # if isinstance(not_before, int) or isinstance(not_before, float):
                if not_before < cur_time:
                    raise YomboWarning(f"'not_before' time should be epoch second in the future, not the past. Got: {not_before}")
                device_command["not_before_at"] = not_before

            elif delay is not None:
                if isinstance(delay, str):
                    try:
                        delay = float(delay)
                    except:
                        raise YomboWarning(f"'delay' time must be an int, float, or parsable string. Got: {delay}")
                # if isinstance(not_before, int) or isinstance(not_before, float):
                if delay < 0:
                    raise YomboWarning("'not_before' time should be epoch second in the future, not the past.")
                device_command["not_before_at"] = cur_time + delay

            # determine how late the command can be run. This happens is the gateway was turned off
            if not_after is not None:
                if isinstance(not_after, str):
                    try:
                        not_after = float(not_after)
                    except:
                        raise YomboWarning("'not_after' time should be epoch second in the future after not_before as an int, float, or parsable string.")
                if isinstance(not_after, int) or isinstance(not_after, float):
                    if not_after < device_command["not_before_at"]:
                        raise YomboWarning("'not_after' must occur after 'not_before (or current time + delay)")
                device_command["not_after_at"] = not_after
            elif max_delay is not None:
                # todo: try to convert if it's not. Make a util helper for this, occurs a lot!
                if isinstance(max_delay, str):
                    try:
                        max_delay = float(max_delay)
                    except:
                        raise YomboWarning("'max_delay' time should be an int, float, or parsable string.")
                if isinstance(max_delay, int) or isinstance(max_delay, float):
                    if max_delay < 0:
                        raise YomboWarning("'max_delay' must be positive only.")
                device_command["not_after_at"] = device_command["not_before_at"] + max_delay

        device_command["params"] = kwargs.get("params", None)
        if inputs is None:
            inputs = {}
        else:
            for input_label, input_value in inputs.items():
                try:
                    inputs[input_label] = self._Parent._DeviceTypes.validate_command_input(self.device_type_id, command.command_id, input_label, input_value)
                except Exception as e:
                    pass
        device_command["inputs"] = inputs
        if callbacks is not None:
            device_command["callbacks"] = callbacks

        self.device_commands.appendleft(request_id)

        # print("command source: %s" % device_command[COMMAND_COMPONENT_REQUESTING_SOURCE])
        # print("command auth_id: %s" % device_command["auth_id"])
        #
        self._Parent._DeviceCommands.add_device_command_by_object(device_command)

        return request_id

    @inlineCallbacks
    def _do_command(self, device_command):
        """
        Performs the actual sending of a device command. This calls the hook "_device_command_". Any modules that
        have implemented this hook can monitor or act on the hook.

        When a device changes state, whatever module changes the state of a device, or is responsible for reporting
        those changes, it *must* call "self._Devices["devicename/deviceid"].set_state()

        **Hooks called**:

        * _devices_command_ : Sends kwargs: *device*, the device object and *command*. This receiver will be
          responsible for obtaining whatever information it needs to complete the action being requested.

        :param device_command: device_command instance with all our required values.
        :return:
        """
        items = {
            COMMAND_COMPONENT_COMMAND: device_command.command,
            COMMAND_COMPONENT_COMMAND_ID: device_command.command.command_id,
            COMMAND_COMPONENT_DEVICE: self,
            COMMAND_COMPONENT_DEVICE_ID: self.device_id,
            COMMAND_COMPONENT_INPUTS: device_command.inputs,
            COMMAND_COMPONENT_REQUEST_ID: device_command.request_id,
            COMMAND_COMPONENT_DEVICE_COMMAND: device_command,
            COMMAND_COMPONENT_CALLED_BY: self,
            COMMAND_COMPONENT_PIN: device_command.pin,
            COMMAND_COMPONENT_SOURCE_GATEWAY_ID: device_command.source_gateway_id,
            COMMAND_COMPONENT_SOURCE: device_command.source,
            COMMAND_COMPONENT_AUTH_ID: device_command.auth_id,
        }
        # logger.debug("calling _device_command_, request_id: {request_id}", request_id=device_command.request_id)
        device_command.set_broadcast()
        results = yield global_invoke_all("_device_command_", **items)
        for component, result in results.items():
            if result is True:
                device_command.set_received(message=f"Received by: {component}")
        self._Parent._Statistics.increment("lib.devices.commands_sent", anon=True)

    def device_command_processing(self, request_id, **kwargs):
        """
        A shortcut to calling device_comamnd_sent and device_command_received together.

        This will trigger two calls of the same hook "_device_command_status_". Once for status
        of "received" and another for "sent".

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_sent(message=message, sent_at=log_time)
            device_command.set_received(message=message, received_at=log_time)
            global_invoke_all("_device_command_status_",
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              source=source,
                              )
        else:
            return

    def device_command_accepted(self, request_id, **kwargs):
        """
        Called by any module that accepts the command for processing.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_accepted(message=message, accepted_at=log_time)
            global_invoke_all("_device_command_status_",
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              source=source,
                              )
        else:
            return

    def device_command_sent(self, request_id, **kwargs):
        """
        Called by any module that has sent the command to an end-point.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_sent(message=message, sent_at=log_time)
            global_invoke_all("_device_command_status_",
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              source=source,
                              )
        else:
            return

    def device_command_received(self, request_id, **kwargs):
        """
        Called by any module that intends to process the command and deliver it to the automation device.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_received(message=message, received_at=log_time)
            global_invoke_all("_device_command_status_",
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              source=source,
                              )
        else:
            return

    def device_command_pending(self, request_id, **kwargs):
        """
        This should only be called if command processing takes more than 1 second to complete. This lets applications,
        users, and everyone else know it's pending. Calling this excessively can cost a lot of local CPU cycles.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_pending(message=message, pending_at=log_time)
            global_invoke_all("_device_command_status_",
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              source=source,
                              )
        else:
            return

    def device_command_failed(self, request_id, **kwargs):
        """
        Should be called when a the command cannot be completed for whatever reason.

        A status can be provided: send a named parameter of "message" with any value.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_failed(message=message, finished_at=log_time)
            if message is not None:
                logger.warn("Device ({label}) command failed: {message}", label=self.label, message=message,
                            state="failed")
            global_invoke_all("_device_command_status_",
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              source=source,
                              )
        else:
            return

    def device_command_cancel(self, request_id, **kwargs):
        """
        Cancel a device command request. Cannot guarentee this will happen. Unable to cancel if status is "done" or
        "failed".

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        log_time = kwargs.get("log_time", None)
        message = kwargs.get("message", None)
        source = kwargs.get("source", None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_canceled(message=message, finished_at=log_time)
            if message is not None:
                logger.debug("Device ({label}) command failed: {message}", label=self.label, message=message)
            global_invoke_all("_device_command_status_",
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              source=source,
                              )
        else:
            return

    def device_delay_expired(self, request_id, **kwargs):
        """
        This is called on system bootup when a device command was set for a delayed execution,
        but the time limit for executing the command has elasped.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        log_time = kwargs.get("log_time", None)
        message = kwargs.get("message", None)
        source = kwargs.get("source", None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_delay_expired(message=message, finished_at=log_time)
            if message is not None:
                logger.debug("Device ({label}) command failed: {message}", label=self.label, message=message)
            global_invoke_all("_device_command_status_",
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              source=source,
                              )
        else:
            return

    def device_command_done(self, request_id, **kwargs):
        """
        Called by any module that has completed processing of a command request.

        A status can be provided: send a named parameter of "message" with any value.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        message = kwargs.get("message", None)
        log_time = kwargs.get("log_time", None)
        source = kwargs.get("source", None)
        if request_id in self._Parent.device_commands:
            device_command = self._Parent.device_commands[request_id]
            device_command.set_finished(message=message, finished_at=log_time)
            global_invoke_all("_device_command_status_",
                              called_by=self,
                              device_command=device_command,
                              status=device_command.status,
                              status_id=device_command.status_id,
                              message=message,
                              source=source,
                              )
        else:
            return

    def energy_translate(self, value, leftMin, leftMax, rightMin, rightMax):
        """
        Calculates the energy consumed based on the energy_map.

        :param value:
        :param leftMin:
        :param leftMax:
        :param rightMin:
        :param rightMax:
        :return:
        """
        # Figure out how "wide" each range is
        leftSpan = leftMax - leftMin
        rightSpan = rightMax - rightMin
        # Convert the left range into a 0-1 range (float)
        valueScaled = float(value - leftMin) / float(leftSpan)
        # Convert the 0-1 range into a value in the right range.
        return rightMin + (valueScaled * rightSpan)

    # def get_status(self, history=0):
    #     """
    #     Gets the history of the device status.
    #
    #     :param history: How far back to go. 0 = prevoius, 1 - the one before that, etc.
    #     :return:
    #     """
    #     return self.status_history[history]

    def get_device_commands(self, history=0):
        """
        Gets the last command information.

        :param history: How far back to go. 0 = previoius, 1 - the one before that, etc.
        :return:
        """
        return self.device_commands[history]

    def set_status_process(self, **kwargs):
        """
        A place for modules to process any status updates. Make any last minute changes before it's saved and
        distributed.

        :param kwargs:
        :return:
        """
        logger.debug("device ({label}), set_status_process kwargs: {kwargs}", label=self.full_label, kwargs=kwargs)
        if len(self.status_history) == 0:
            previous_extra = {}
        else:
            previous_extra = self.status_history[0].machine_state_extra

        if isinstance(previous_extra, dict) is False:
            previous_extra = {}

        # filter out previous invalid status extra values.
        # for extra_key in list(previous_extra.keys()):
        #     if extra_key not in self.MACHINE_STATE_EXTRA_FIELDS:
        #         del previous_extra[extra_key]

        new_extra = kwargs.get("machine_state_extra", {})

        # filter out new invalid status extra values.
        for extra_key in list(new_extra.keys()):
            if extra_key not in self.MACHINE_STATE_EXTRA_FIELDS:
                logger.warn(
                    f"For device '{self.full_label}', the machine status extra field '{extra_key}' was removed"
                    f" on status update. This field is not apart of the approved machine status extra fields. "
                    f"Device type: {self.device_type.label}")
                del new_extra[extra_key]

        for key, value in previous_extra.items():
            if key in new_extra:
                continue
            new_extra[key] = value

        kwargs["machine_state_extra"] = new_extra
        return kwargs

    def generate_human_state(self, machine_state, machine_state_extra):
        return machine_state

    def generate_human_message(self, machine_state, machine_state_extra):
        human_state = self.generate_human_state(machine_state, machine_state_extra)
        return f"{self.area_label} is now {human_state}"

    def set_status_machine_extra(self, **kwargs):
        pass

    def set_state_delayed(self, delay=None, **kwargs):
        """
        Accepts all the arguments of set_status, but delays submitting to set_status. This
        is used by devices that set several attributes separately, but quickly.

        :param kwargs:
        :return:
        """
        if delay is None:
            delay = 0.1
        if kwargs is None:
            raise ImportError("Must supply status arguments...")

        self.state_delayed = dict_merge(self.state_delayed, kwargs)
        if COMMAND_COMPONENT_REPORTING_SOURCE not in self.state_delayed:
            self.state_delayed[COMMAND_COMPONENT_REPORTING_SOURCE] = generate_source_string(gateway_id=self.gateway_id)

        if self.state_delayed_calllater is not None and self.state_delayed_calllater.active():
            self.state_delayed_calllater.cancel()

        self.state_delayed_calllater = reactor.callLater(delay, self.do_set_state_delayed)

    def do_set_state_delayed(self):
        """
        Sends the actual delayed status to set_status(). This was called using a callLater function
        from set_state_delayed().

        :return:
        """
        if "machine_state" not in self.state_delayed:
            self.state_delayed["machine_state"] = self.machine_state
        self.set_state(**self.state_delayed)
        self.state_delayed.clear()

    def set_status(self, **kwargs):
        """
        Usually called by the device's command/logic module to set/update the
        device status. This can also be called externally as needed.

        :raises YomboWarning: Raised when:

            - If no valid status sent in. Errorno: 120
            - If statusExtra was set, but not a dictionary. Errorno: 121
        :param kwargs: Named arguments:

            - human_state *(int or string)* - The new status.
            - human_message *(string)* - A human friendly text message to display.
            - command *(string)* - Command label from the last command.
            - machine_state *(int or string)* - The new status.
            - machine_state_extra *(dict)* - Extra status as a dictionary.
            - silent *(any)* - If defined, will not broadcast a status update message; atypical.

        """
        self.state_delayed = dict_merge(self.state_delayed, kwargs)
        if COMMAND_COMPONENT_REPORTING_SOURCE not in self.state_delayed:
            self.state_delayed[COMMAND_COMPONENT_REPORTING_SOURCE] = generate_source_string(gateway_id=self.gateway_id)

        kwargs_delayed = self.set_state_process(**self.state_delayed)
        kwargs_delayed, status_id = self._set_status(**kwargs_delayed)
        self.state_delayed = {}

        if "silent" not in kwargs_delayed and status_id is not None:
            self.send_status(**kwargs_delayed)

        if self.state_delayed_calllater is not None and self.state_delayed_calllater.active():
            self.state_delayed_calllater.cancel()

    def _set_status(self, **kwargs):
        """
        A private function used to do the work of setting the status.
        :param kwargs: 
        :return: 
        """
        if "machine_state" not in kwargs:
            raise YomboWarning("set_status was called without a real machine_state!", errorno=120)
        # logger.info("_set_status called...: {kwargs}", kwargs=kwargs)
        machine_state = kwargs["machine_state"]
        machine_state_extra = kwargs.get("machine_state_extra", {})
        kwargs["machine_state_extra"] = machine_state_extra

        if machine_state == self.machine_state:
            added, removed, modified, same = dict_diff(machine_state_extra, self.machine_state_extra)
            if len(added) == 0 and len(removed) == 0 and len(modified) == 0:
                logger.info("Was asked to set status for device ({label}), but status matches. Aborting..",
                            label=self.full_label)
                return kwargs, None

        kwargs[COMMAND_COMPONENT_HUMAN_STATUS] = kwargs.get(COMMAND_COMPONENT_HUMAN_STATUS, self.generate_human_state(machine_state, machine_state_extra))
        kwargs[COMMAND_COMPONENT_HUMAN_MESSAGE] = kwargs.get(COMMAND_COMPONENT_HUMAN_MESSAGE, self.generate_human_message(machine_state, machine_state_extra))
        uploaded = kwargs.get("uploaded", 0)
        uploadable = kwargs.get("uploadable", 1)
        set_at = kwargs.get("set_at", time())
        if "gateway_id" not in kwargs:
            kwargs["gateway_id"] = self.gateway_id

        request_id = None
        auth_id = "unknown"
        if COMMAND_COMPONENT_REQUEST_ID in kwargs and kwargs[COMMAND_COMPONENT_REQUEST_ID] in self._Parent.device_commands:
            request_id = kwargs["request_id"]
            auth_id = self._Parent.device_commands[request_id].auth_id
            kwargs[COMMAND_COMPONENT_REQUESTING_SOURCE] = self._Parent.device_commands[request_id].requesting_source
            kwargs[COMMAND_COMPONENT_COMMAND] = self._Parent.device_commands[request_id].command
        else:
            kwargs[COMMAND_COMPONENT_REQUESTING_SOURCE] = None
            kwargs[COMMAND_COMPONENT_COMMAND] = None

        kwargs[COMMAND_COMPONENT_REQUEST_ID] = request_id

        if kwargs[COMMAND_COMPONENT_COMMAND] is None:
            if COMMAND_COMPONENT_COMMAND in kwargs:
                try:
                    kwargs[COMMAND_COMPONENT_COMMAND] = self._Parent._Commands[kwargs[COMMAND_COMPONENT_COMMAND]]
                except KeyError:
                    kwargs[COMMAND_COMPONENT_COMMAND] = None
            else:
                kwargs[COMMAND_COMPONENT_COMMAND] = self.command_from_status(machine_state, machine_state_extra)

        kwargs[COMMAND_COMPONENT_AUTH_ID] = auth_id

        kwargs[COMMAND_COMPONENT_ENERGY_USAGE], kwargs[COMMAND_COMPONENT_ENERGY_TYPE] = \
        energy_usage, energy_type = self.energy_calc(command=kwargs["command"],
                                                     machine_state=machine_state,
                                                     machine_state_extra=machine_state_extra,
                                                     )

        if self.statistic_type not in (None, "", "None", "none"):
            if self.statistic_type.lower() == "datapoint" or self.statistic_type.lower() == "average":
                statistic_label_slug = self.statistic_label_slug
            if self.statistic_type.lower() == "datapoint":
                self._Parent._Statistics.datapoint(f"devices.{statistic_label_slug}", machine_state)
                if self.energy_type not in (None, "", "none", "None"):
                    self._Parent._Statistics.datapoint(f"energy.{statistic_label_slug}", energy_usage)
            elif self.statistic_type.lower() == "average":
                self._Parent._Statistics.averages(f"devices.{statistic_label_slug}",
                                                  machine_state,
                                                  int(self.statistic_bucket_size))
                if self.energy_type not in (None, "", "none", "None"):
                    self._Parent._Statistics.averages(f"energy.{statistic_label_slug}",
                                                      energy_usage,
                                                      int(self.statistic_bucket_size))

        new_status = Device_State(self._Parent, self, {
            "command": kwargs["command"],
            "set_at": set_at,
            "energy_usage": energy_usage,
            "energy_type": energy_type,
            "human_state": kwargs[COMMAND_COMPONENT_HUMAN_STATUS],
            "human_message": kwargs[COMMAND_COMPONENT_HUMAN_MESSAGE],
            "machine_state": machine_state,
            "machine_state_extra": machine_state_extra,
            "gateway_id": kwargs["gateway_id"],
            "auth_id": auth_id,
            "reporting_source": kwargs[COMMAND_COMPONENT_REPORTING_SOURCE],
            "requesting_source": kwargs[COMMAND_COMPONENT_REQUESTING_SOURCE],
            "request_id": kwargs[COMMAND_COMPONENT_REQUEST_ID],
            "uploaded": uploaded,
            "uploadable": uploadable,
            }
        )
        self.status_history.appendleft(new_status)
        self.set_state_machine_extra(**kwargs)

        # Yombo doesn't currently have the capacity to collect these....In the future...
        # if self._security_send_device_states() is True:
        #     request_msg = self._Parent._AMQPYombo.generate_message_request(
        #         exchange_name="ysrv.e.gw_device_status",
        #         source="yombo.gateway.lib.devices.base_device",
        #         destination="yombo.server.device_status",
        #         body={
        #             "status_set_at": datetime.fromtimestamp(time()).strftime("%Y-%m-%d %H:%M:%S.%f"),
        #             "device_id": self.device_id,
        #             "energy_usage": energy_usage,
        #             "energy_type": energy_type,
        #             "human_state": kwargs["human_state"],
        #             "human_message": kwargs["human_message"],
        #             "machine_state": machine_state,
        #             "machine_state_extra": machine_state_extra,
        #             "user_id": user_id,
        #             "user_type": user_type,
        #             "reporting_source": kwargs["reporting_source"],
        #         },
        #         request_type="save_device_status",
        #     )
        #     self._Parent._AMQPYombo.publish(**request_msg)

        return kwargs, new_status["status_id"]

    def set_status_internal(self, status):
        """
        Primarily used by the gateway library to set a device status.

        :param status:
        :return:
        """
        source = status.get("source", None)
        # print("set_status_internal: source: %s" % source)
        device_status = Device_States(self._Parent, self, status, source=source)
        # print("set_status_internal: as dict: %s" % device_status.asdict())
        self.status_history.appendleft(device_status)
        self.send_status(**status)

    def send_status(self, **kwargs):
        """
        Sends current status. Use set_status() to set the status, it will call this method for you.

        Calls the _device_state_ hook to send current device status. Useful if you just want to send a status of
        a device without actually changing the status.

        :param kwargs:
        :return:
        """
        command_id = None
        command_label = None
        command_machine_label = None
        if "command" in kwargs:
            command = kwargs["command"]
            if isinstance(command, str):
                try:
                    command = self._Parent._Commands[command]
                except Exception as e:
                    command = None
        elif "command_id" in kwargs:
            try:
                command = self._Parent._Commands[kwargs["command_id"]]
            except Exception as e:
                command = None
        else:
            command = None

        if command is not None:
            command_id = command.command_id
            command_label = command.label
            command_machine_label = command.machine_label

        try:
            previous_status = self.status_history[1].asdict()
        except Exception as e:
            previous_status = None
        device_type = self._Parent._DeviceTypes[self.device_type_id]

        source = kwargs.get("source", None)

        message = {
            "device": self,
            "command": command,
            "request_id": kwargs.get("request_id", None),
            "gateway_id": kwargs.get("gateway_id", self.gateway_id),
            "source": source,
            "event": {
                "area": self.area,
                "location": self.location,
                "area_label": self.area_label,
                "full_label": self.full_label,
                "device_id": self.device_id,
                "device_label": self.label,
                "device_machine_label": self.machine_label,
                "device_type_id": self.device_type_id,
                "device_type_label": device_type.machine_label,
                "device_type_machine_label": device_type.machine_label,
                "command_id": command_id,
                "command_label": command_label,
                "command_machine_label": command_machine_label,
                "status_current": self.status_history[0].asdict(),
                "status_previous": previous_status,
                "gateway_id": kwargs.get("gateway_id", self.gateway_id),
                "device_features": self.features,  # lowercase version only shows active features.
                "auth_id": kwargs["auth_id"],
                "reporting_source": kwargs["reporting_source"],
            },
        }

        if len(self.status_history) == 1:
            message["previous_status"] = None
        else:
            message["previous_status"] = self.status_history[1]

        self._Automation.trigger_monitor("device",
                                         device=self,
                                         action="set_status")
        global_invoke_all("_device_state_",
                          called_by=self,
                          **message,
                          )

    def device_user_access(self, access_type=None):
        """
        Gets all users that have access to this device.

        :param access_type: If set to "direct", then gets list of users that are specifically added to this device.
            if set to "roles", returns access based on role membership.
        :return:
        """
        if access_type is None:
            access_type = "direct"

        if access_type == "direct":
            permissions = {}
            for email, user in self._Parent._Users.users.items():
                item_permissions = user.item_permissions
                if "device" in item_permissions and self.machine_label in item_permissions["device"]:
                    if email not in permissions:
                        permissions[email] = []
                    for action in item_permissions["device"][self.machine_label]:
                        if action not in permissions[email]:
                            permissions[email].append(action)
            return permissions
        elif access_type == "roles":
            return {}

    def remove_delayed(self):
        """
        Remove any messages that might be set to be called later that
        relates to this device.  Easy, just tell the messages library to 
        do that for us.
        """
        self._Parent._MessageLibrary.device_delay_cancel(self.device_id)

    def delayed_commands(self):
        """
        Get commands that are delayed for this device. This is commands that are set to complete in the
        future, and not pending.
        """
        commands = {}
        for request_id, device_command in self._Parent._DeviceCommands.device_commands.items():
            if device_command.status == "delayed" and device_command.device.device_id == self.device_id:
                commands[request_id] = device_command
        return commands

    def pending_commands(self, criteria=None, limit=None):
        device_commands = self._Parent.device_commands
        results = OrderedDict()
        for id, DC in device_commands.items():
            if criteria is None:
                if DC.device.device_id == self.device_id:
                    if DC.status in ("sent", "received", "pending"):
                        results[id] = DC
            else:
                matches = True
                for key, value in criteria.items():
                    if hasattr(DC, key):
                        test_value = getattr(DC, key)
                        if isinstance(value, list):
                            if test_value not in value:
                                matches = False
                                break
                        else:
                            if test_value != value:
                                matches = False
                                break
                if matches:
                    results[id] = DC

            # if limit is not None and len(results) == limit:
            #     return results
        return results

    def validate_command(self, command_requested):
        available_commands = self.available_commands()
        if command_requested in available_commands:
            return available_commands[command_requested]
        else:
            commands = {}
            for command_id, data in available_commands.items():
                commands[command_id] = data["command"]
            search_attributes = [
                {
                    "field": "command_id",
                    "value": command_requested,
                    "limiter": .96,
                },
                {
                    "field": "machine_label",
                    "value": command_requested,
                    "limiter": .89,
                },
                {
                    "field": "label",
                    "value": command_requested,
                    "limiter": .89,
                },
            ]
            try:
                logger.debug("Get is about to call search...: {command_requested}", command_requested=command_requested)
                results = do_search_instance(search_attributes,
                                             commands,
                                             self._Parent._class_storage_search_fields,
                                             allowed_keys=self._Parent._Commands._class_storage_search_fields,
                                             limiter=.89,
                                             max_results=1)

                if results["was_found"]:
                    return True
                else:
                    return False
            except YomboWarning:
                return False
                # raise KeyError("Searched for %s, but had problems: %s" % (command_requested, e))

    @inlineCallbacks
    def delete(self, session=None):
        """
        Called when the device should delete itself.

        :return: 
        """
        results = yield self._Parent.delete_device(self.device_id, session=session)
        return results

    @inlineCallbacks
    def enable(self, session=None):
        """
        Called when the device should enable itself.

        :return:
        """
        results = yield self._Parent.enable_device(self.device_id, session=session)
        return results

    @inlineCallbacks
    def disable(self, session=None):
        """
        Called when the device should disable itself.

        :return:
        """
        results = yield self._Parent.disable_device(self.device_id, session=session)
        return results

    @inlineCallbacks
    def save(self, source=None, session=None):
        """
        Save this device to the database.

        :return:
        """
        if source is None:
            source = self.source

        if self._Parent.gateway_id != self.gateway_id:
            return {
                "status": "failed",
                "msg": "Can only edit local devices.",
                "device_id": self.device_id
            }

        if self.source != "database":
            return {
                "status": "failed",
                "msg": "Can only edit database loaded devices.",
                "device_id": self.device_id
            }

        if self.is_dirty is False:
            return {
                "status": "success",
                "msg": "Device saved.",
                "device_id": self.device_id
            }

        if source != "amqp":
            api_data = {
                "device_type_id": str(self.device_type_id),
                "machine_label": str(self.machine_label),
                "label": str(self.label),
                "description": str(self.description),
                "location_id": self.location_id,
                "area_id": self.area_id,
                "notes": str(self.notes),
                "pin_code": self.pin_code,
                "pin_required": int(self.pin_required),
                "pin_timeout": self.pin_timeout,
                "statistic_label": str(self.statistic_label),
                "statistic_lifetime": str(self.statistic_lifetime),
                "statistic_type": str(self.statistic_type),
                "statistic_bucket_size": str(self.statistic_bucket_size),
                "energy_type": self.energy_type,
                "energy_tracker_source": self.energy_tracker_source,
                "energy_tracker_device": self.energy_tracker_device,
                "energy_map": self.energy_map,
                "controllable": self.controllable,
                "allow_direct_control": self.allow_direct_control,
                "status": self.status,
                "created_at": int(self.created_at),
                "updated_at": int(self.updated_at),
            }

            if isinstance(self.energy_map, dict):
                api_data["energy_map"] = data_pickle(self.energy_map, "json")

            api_results = yield self._YomboAPI.request("PATCH",
                                                       f"/v1/device/{self.device_id}",
                                                       api_data,
                                                       session=session)
            if api_results["code"] > 299:
                return {
                    "status": "failed",
                    "msg": "Couldn't edit device",
                    "apimsg": api_results["content"]["message"],
                    "apimsghtml": api_results["content"]["html_message"],
                    "device_id": self.device_id,
                }

        yield self._Parent._LocalDB.upsert_device(self)

        return {
            "status": "success",
            "msg": "Device saved.",
            "device_id": self.device_id
        }
