# cython: embedsignature=True
# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at http://yombo.net
"""
.. rst-class:: floater

.. note::

  For more information see: `Devices @ Projects.yombo.net <https://projects.yombo.net/projects/modules/wiki/Devices>`_

The devices library is primarily responsible for: maintaining device state and
sending commands to devices.

The device (singular) class represents one device.  This class has many functions
that help with utilizing the device.  When possible, this class should be used to
send Yombo Messages for controlling, and getting/setting/querying status. The
device class maintains the current known device state.  Any changes to the device
state are saved to the local database.

To send a command to a device is simple.

*Usage**:

.. code-block:: python

   # Three ways to send a command to a device. Going from easiest method, but less assurance of correct command
   # to most assurance.

   # Lets turn on every device this module manages.
   for item in self._Devices:
       self.Devices[item].do_command(cmd='off')

   # Lets turn off every every device, using a very specific command uuid.
   for item in self._Devices:
       self.Devices[item].do_command(cmd='js83j9s913')  # Made up number, but can be same as off


   # Turn off the christmas tree.
   self._Devices.do_command('christmas tree', 'off')

   # Get devices by device type:
   deviceList = self._DeviceTypes.devices_by_device_type('137ab129da9318')  # This is a function.

   # A simple all x10 lights off (regardless of house / unit code)
   allX10Lamps = self._DeviceTypes.devices_by_device_type('137ab129da9318')
   # Turn off all x10 lamps
   for lamp in allX10Lamps:
       self._Devices.do_command(lamp, 'off')

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from __future__ import print_function

import copy
from collections import deque, namedtuple
from time import time

# Import 3rd-party libs
import yombo.ext.six as six

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.task import LoopingCall
from twisted.internet.defer import inlineCallbacks, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboPinCodeError, YomboDeviceError, YomboFuzzySearchError, YomboWarning
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string, split, global_invoke_all

logger = get_logger('library.devices')


class Devices(YomboLibrary):
    """
    Manages all devices and provides the primary interaction interface. The
    primary functions developers should use are:
        - :func:`get_device` - Get a pointer to all devices.
        - :func:`get_devices_by_device_type` - Get all device for a certain deviceType (UUID or MachineLabel)
        - :func:`search` - Get a pointer to a device, using device_id or device label.
    """

    def __contains__(self, deviceRequested):
        """
        Checks to if a provided device name or device uuid exists.

        Simulate a dictionary when requested with:

            >>> if '137ab129da9318' in self._Devices['137ab129da9318']:  #by uuid

        or:

            >>> if 'living room light' in self._Devices['137ab129da9318']:  #by uuid

        See: :func:`yombo.utils.get_devices` for full usage example.

        :param deviceRequested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get_device(deviceRequested)
            return True
        except:
            return False

    def __getitem__(self, deviceRequested):
        """
        Attempts to find the device requested using a couple of methods.

        Simulate a dictionary when requested with:

            >>> self._Devices['137ab129da9318']  #by uuid

        or:

            >>> self._Devices['living room light']  #by name

        See: :func:`yombo.utils.get_devices` for full usage example.

        :raises YomboDeviceError: Raised when device cannot be found.
        :param deviceRequested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Pointer to array of all devices.
        :rtype: dict
        """
        return self.get_device(deviceRequested)

    def __iter__(self):
        return self._devicesByUUID.__iter__()

    def keys(self):
        return self._devicesByUUID.keys()
    def items(self):
        return self._devicesByUUID.items()
    def iteritems(self):
        return self._devicesByUUID.iteritems()
    def iterkeys(self):
        return self._devicesByUUID.iterkeys()
    def itervalues(self):
        return self._devicesByUUID.itervalues()
    def values(self):
        return self._devicesByUUID.values()
    def has_key(self):
        return self._devicesByUUID.has_key()

    @inlineCallbacks
    def _init_(self):
        """
        Setups up the basic framework. Nothing is loaded in here until the
        Load() stage.
        :param loader: A pointer to the :mod:`yombo.lib.loader`
        library.
        :type loader: Instance of Loader
        """
        self._AutomationLibrary = self._Loader.loadedLibraries['automation']
        self._VoiceCommandsLibrary = self._Loader.loadedLibraries['voicecmds']
        self._LocalDBLibrary = self._Libraries['localdb']

        self._devicesByUUID = FuzzySearch({}, .99)
        self._devicesByName = FuzzySearch({}, .89)
        self._status_updates_to_save = {}
        self._saveStatusLoop = None
        self.run_state = 1

        self.delay_queue = yield self._Libraries['SQLDict'].get(self, 'delay_queue')
        # {'lmnop123', { 'not_before':123, 'max_delay': 100, 'kwargs':**kwargs} }

        self.startup_queue = {}  # Place device commands here until we are ready to process device commands
        # {'abc123-xyz123', { 'not_before':123, 'max_delay': 100, 'kwargs':**kwargs} }
        #
        self.reactors = {} # map device:command request ID's to reactor.
        self.delay_deviceList = {} # list of devices that have pending messages.
        self.processing_commands = False

    def _load_(self):
        self.run_state = 2

    def _start_(self):
        self.run_state = 3

        self.start_deferred = Deferred()
        self.__load_devices()

        self._saveStatusLoop = LoopingCall(self._save_status)
        self._saveStatusLoop.start(120, False)

        if self._Atoms['loader.operation_mode'] == 'run':
            self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming, client_id='devices')
            self.mqtt.subscribe("yombo/devices/+/get")
            self.mqtt.subscribe("yombo/devices/+/cmd")

        return self.start_deferred

    def _started_(self):
        self.run_state = 4
        print("devices: %s" % self._devicesByUUID)

    def _stop_(self):
        """
        We don't do anything, but 'pass' so we don't generate an exception.
        """
        if hasattr(self, '_saveStatusLoop') and self._saveStatusLoop is not None and self._saveStatusLoop.running is True:
            self._saveStatusLoop.stop()

    def _unload_(self):
        """
        Stop periodic loop, save status updates.
        """
        self._save_status()

    def _reload_(self):
        return self.__load_devices()

    def _module_started_(self):
        """
        On start, sends all queued messages. Then, check delayed messages for any messages that were missed. Send
        old messages and prepare future messages to run.
        """
        self.processing_commands = True
        for command, request in self.startup_queue.iteritems():
            self.do_command(request['device_id'], request['command_id'], not_before=request['not_before'],
                    max_delay=request['max_delay'], **request['kwargs'])
        self.startup_queue.clear()


        # Now check to existing delayed messages.  If not too old, send otherwise delete them.  If time is in
        #  future, setup a new reactor to send in future.
        logger.debug("module_started: delayQueue: {delay}", delay=self.delay_queue)
        for request_id in self.delay_queue.keys():
            if request_id in self.reactors:
                logger.debug("Message already scheduled for delivery later. Possible from an automation rule. Skipping.")
                continue
            request = self.delay_queue[request_id]
            if float(request['not_before']) < time(): # if delay message time has past, maybe process it.
                if time() - float(request['not_before']) > float(request['max_delay']):
                    # we're too late, just delete it.
                    del self.delay_queue[request_id]
                    continue
                else:
                    #we're good, lets hydrate the request and send it.
                    self.do_command(request['device_id'], request['command_id'], request['kwargs'])

            else: # Still good, but still in the future. Set them up.
                self.do_command(request['device_id'], request['command_id'], not_before=request['not_before'],
                        max_delay=request['max_delay'], **request['kwargs'])

    def do_command(self, device, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None, **kwargs):
        """
        Forwarder function to the actual device object for processing.

        :param device: Device ID or Label.
        :param cmd: Command ID or Label to send.
        :param pin: A pin to check.
        :param request_id: A request ID for tracking.
        :param delay: How many seconds to delay sending the command.
        :param kwargs: If a command is not sent at the delay sent time, how long can pass before giving up. For example, Yombo Gateway not running.
        :return:
        """
        return self.get_device(device).do_command(device, cmd, pin, not_before, delay, max_delay, **kwargs)

    @inlineCallbacks
    def __load_devices(self):
        """
        Load the devices into memory. Set up various dictionaries to manage
        devices. This also setups all the voice commands for all the devices.

        This also loads all the device routing. This helps messages and modules determine how to route
        commands between command modules and interface modules.
        """
        print("__load_devices")
        devices = yield self._Libraries['LocalDB'].get_devices()
        logger.debug("Loading devices:::: {devices}", devices=devices)
        if len(devices) > 0:
            for record in devices:
                logger.debug("Loading device: {record}", record=record)
                d = yield self.load_device(record)
        self.start_deferred.callback(10)

    def load_device(self, record, test_device=False):  # load ore re-load if there was an update.
        """
        Instantiate (load) a new device. Doesn't update database, must call add_update_delete isntead of this.

        **Hooks called**:

        * _device_loaded_ : Sends kwargs: *id* - The new device id.

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :returns: Pointer to new device. Only used during unittest
        """
        # print("load_device: %s" % record)
        try:
            # todo: refactor voicecommands. Need to be able to update/delete them later.
            self._VoiceCommandsLibrary.add(record["voice_cmd"], "", record["id"], record["voice_cmd_order"])
        except:
            pass
        device_id = record["id"]
        self._devicesByUUID[device_id] = Device(record, self)
        d = self._devicesByUUID[device_id]._init_()
        self._devicesByName[record["label"]] = device_id

        logger.debug("_add_device: {record}", record=record)

        global_invoke_all('_device_loaded_', **{'id': record['id']})  # call hook "devices_add" when adding a new device.
        return d
#        if test_device:
#            returnValue(self._devicesByUUID[device_id])

    def enable_device(self, device_id):
        """
        Enables a given device id.

        :param device_id:
        :return:
        """
        if device_id not in self._devicesByUUID:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'enable_device', 'Devices')
        # self._devicesByUUID[device_id].enable()

    def disable_device(self, device_id):
        """
        Disables a given device id.

        :param device_id:
        :return:
        """
        if device_id not in self._devicesByUUID:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'disable_device', 'Devices')
        # self._devicesByUUID[device_id].disable()

    def delete_device(self, device_id):
        """
        Deletes a given device id.

        Behind the scenes, it just updates the database status record

        :param device_id:
        :return:
        """
        if device_id not in self._devicesByUUID:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'delete_device', 'Devices')
        # self._devicesByUUID[device_id].delete()

    def update_device(self, record, test_device=False):
        """
        Add a new device. Record must contain:

        id, uri, label, notes, description, gateway_id, device_type_id, voice_cmd, voice_cmd_order,
        Voice_cmd_src, pin_code, pin_timeout, created, updated, device_class

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :returns: Pointer to new device. Only used during unittest
        """
        logger.debug("update_device: {record}", record=record)
        if record['device_id'] not in self._devicesByUUID:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'delete_device', 'Devices')
        # self._devicesByUUID[record['device_id']].update(record)

    def delete_device(self, device_id, testDevice=False):
        """
        Delete a device. Not so fun, but life is goes on.

        id, uri, label, notes, description, gateway_id, device_type_id, voice_cmd, voice_cmd_order,
        Voice_cmd_src, pin_code, pin_timeout, created, updated, device_class

        :param record: Row of items from the SQLite3 database.
        :type record: dict
        :returns: Pointer to new device. Only used during unittest
        """
        logger.debug("delete_device: {device_id}", device_id=device_id)
        if device_id not in self._devicesByUUID:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'delete_device', 'Devices')
        # self._devicesByUUID[device_id].delete()

#        global_invoke_all('devices_delete', **{'id': record['id']})  # call hook "devices_add" when adding a new device.

    def gotException(self, failure):
       print("Exception: %r" % failure)
       return 100  # squash exception, use 0 as value for next stage

    def mqtt_incoming(self, topic, payload, qos, retain):
        """
        Processes incoming MQTT requests. It understands:

        * yombo/devices/DEVICEID|DEVICEMACHINELABEL/get Value - Get some attribute
          * Value = state, human, machine, extra
        * yombo/devices/DEVICEID|DEVICEMACHINELABEL/cmd/CMDID|CMDMACHINELABEL Options - Send a command
          * Options - Either a string for a single variable, or json for multiple variables

        Examples: /yombo/devices/get/christmas_tree/cmd on

        :param topic:
        :param payload:
        :param qos:
        :param retain:
        :return:
        """
        #  0       1       2       3        4
        # yombo/devices/DEVICEID/get|cmd/option
        parts = topic.split('/', 10)
        print("Yombo Devices got this: %s / %s" % (topic, parts))


        try:
            device = self.get_device(parts[2].replace("_", " "))
        except YomboDeviceError, e:
            logger.info("Received MQTT request for a device that doesn't exist")
            return

#Status = namedtuple('Status', "device_id, set_time, device_state, human_status, machine_status, machine_status_extra, source, uploaded, uploadable")

        if parts[3] == 'get':
            status = device.get_status()
            if payload == 'state':
                self.mqtt.publish('yombo/devices/%s/state/state' % device.label.replace(" ", "_"), str(status.device_state))
            elif payload == 'human':
                self.mqtt.publish('yombo/devices/%s/state/human' % device.label.replace(" ", "_"), str(status.human_status))
            elif payload == 'machine':
                self.mqtt.publish('yombo/devices/%s/state/machine' % device.label.replace(" ", "_"), str(status.machine_status))
            elif payload == 'extra':
                self.mqtt.publish('yombo/devices/%s/state/extra' % device.label.replace(" ", "_"), str(status.machine_status_extra))
            elif payload == 'last':
                self.mqtt.publish('yombo/devices/%s/state/last' % device.label.replace(" ", "_"), str(status.set_time))
            elif payload == 'source':
                self.mqtt.publish('yombo/devices/%s/state/source' % device.label.replace(" ", "_"), str(status.source))
        elif parts[3] == 'cmd':
            msg = device.get_message(self, cmd=parts[4])
            msg.send()
            if len(parts) > 5:
                status = device.get_status()
                if parts[5] == 'state':
                    self.mqtt.publish('yombo/devices/%s/state/state' % device.label.replace(" ", "_"), str(status.device_state))
                elif parts[5] == 'human':
                    self.mqtt.publish('yombo/devices/%s/state/human' % device.label.replace(" ", "_"), str(status.human_status))
                elif parts[5] == 'machine':
                    self.mqtt.publish('yombo/devices/%s/state/machine' % device.label.replace(" ", "_"), str(status.machine_status))
                elif parts[5] == 'extra':
                    self.mqtt.publish('yombo/devices/%s/state/extra' % device.label.replace(" ", "_"), str(status.machine_status_extra))
                elif parts[5] == 'last':
                    self.mqtt.publish('yombo/devices/%s/state/last' % device.label.replace(" ", "_"), str(status.set_time))
                elif parts[5] == 'source':
                    self.mqtt.publish('yombo/devices/%s/state/source' % device.label.replace(" ", "_"), str(status.source))

    def _save_status(self):
        """
        Function that does actual work. Saves items in the self._toStaveStatus
        queue to the SQLite database.
        """
        if len(self._status_updates_to_save) == 0:
            return

        logger.info("Saving device status to disk.")
        for key in self._status_updates_to_save.keys():
            ss = self._status_updates_to_save[key]
            self._LocalDBLibrary.save_device_status(**ss.__dict__)
            del self._status_updates_to_save[key]

    def _clear_(self):
        """
        Clear all devices. Should only be called by the loader module
        during a reconfiguration event. **Do not call this function!**
        """
        self._save_status()
        self._devicesByUUID.clear()
        self._devicesByName.clear()
        self._devicesByDeviceTypeByUUID.clear()

    def list_devices(self):
        return list(self._devicesByName.keys())

    def get_device(self, device_requested, limiter_override=.99):
        """
        Performs the actual device search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find commands: `self._Devices['8w3h4sa']`

        See: :func:`yombo.core.helpers.get_device` for full usage example.

        :raises YomboDeviceError: Raised when device cannot be found.
        :param device_requested: The device UUID or device label to search for.
        :type deviceRequested: string
        :return: Pointer to array of all devices.
        :rtype: dict
        """
        logger.debug("looking for: {device_id}", device_id=device_requested)
        if device_requested in self._devicesByUUID:
            logger.debug("found by device id! {device_id}", device_id=device_requested)
            return self._devicesByUUID.search2(device_requested, limiter_override)
        else:
            try:
                requestedUUID = self._devicesByName[device_requested]
                logger.debug("found by device name! {device_id}", device_id=device_requested)
                return self._devicesByUUID[requestedUUID]
            except YomboFuzzySearchError, e:
                raise YomboDeviceError('Searched for %s, but no good matches found.' % e.searchFor, searchFor=e.searchFor, key=e.key, value=e.value, ratio=e.ratio, others=e.others)

    ##############################################################################################################
    # The remaining functions implement automation hooks. These should not be called by anything other than the  #
    # automation library!                                                                                        #
    ##############################################################################################################
    def check_trigger(self, device_id, new_status):
        """
        Called by the devices.set function when a device changes state. It just sends this to the automation
        library for checking and firing any rules as needed.

        True - Rules fired, fale - no rules fired.
        :param device_id: Device ID
        :type device_id: str
        :param new_status: New device state
        :type new_status: str
        """
        self._AutomationLibrary.triggers_check('devices', device_id, new_status)

    def Devices_automation_source_list(self, **kwargs):
        """
        Adds 'devices' to the list of source platforms (triggers)as a platform for rule sources (triggers).

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'devices',
              'validate_source_callback': self.devices_validate_source_callback,  # function to call to validate a trigger
              'add_trigger_callback': self.devices_add_trigger_callback,  # function to call to add a trigger
              'get_value_callback': self.devices_get_value_callback,  # get a value
            }
         ]

    def devices_validate_source_callback(self, rule, portion, **kwargs):
        """
        Used to check a rule's source for 'devices'. It makes sure rule source is valid before being added.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the rule being checked. Includes source, filter, etc.
        :return: None. Raises YomboWarning if invalid.
        """
        if 'platform' not in portion['source']:
            raise YomboWarning("'platform' must be in 'source' section.")

        if 'device' in portion['source']:
            try:
#                print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  00011"
                device = self.get_device(portion['source']['device'], .89)
#                print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  00022"
                portion['source']['device_pointer'] = device
#                print "$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$  00033"
                return portion
            except Exception, e:
                raise YomboWarning("Error while searching for device, could not be found: %s" % portion['source']['device'],
                                   101, 'devices_validate_source_callback', 'lib.devices')
        else:
            raise YomboWarning("For platform 'devices' as a 'source', must have 'device' and can be either device ID or device label.  Source:%s" % portion,
                               102, 'devices_validate_source_callback', 'lib.devices')

    def devices_add_trigger_callback(self, rule, **kwargs):
        """
        Called to add a trigger.  We simply use the automation library for the heavy lifting.

        :param rule: The potential rule being added.
        :param kwargs: None
        :return:
        """
        self._AutomationLibrary.triggers_add(rule['rule_id'], 'devices', rule['trigger']['source']['device_pointer'].device_id)

    def devices_get_value_callback(self, rule, portion, **kwargs):
        """
        A callback to the value for platform "states". We simply just do a get based on key_name.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """

        return portion['source']['device_pointer'].machine_status

    def Devices_automation_action_list(self, **kwargs):
        """
        hook_automation_action_list called by the automation library to list possible actions this module can
        perform.

        This implementation allows autoamtion rules set easily set Atom values.

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'devices',
              'validate_action_callback': self.devices_validate_action_callback,  # function to call to validate an action is possible.
              'do_action_callback': self.devices_do_action_callback  # function to be called to perform an action
            }
         ]

    def devices_validate_action_callback(self, rule, action, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action.

        :param rule: The potential rule being added.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
#        print "devices - kwargs: %s" % action
        if 'command' not in action:
            raise YomboWarning("For platform 'devices' as an 'action', must have 'comand' and can be either command uuid or command label.",
                               103, 'devices_validate_action_callback', 'lib.devices')

        if 'device' in action:
            try:
                devices_text = split(action['device'])
                devices = []
                for device_text in devices_text:
                    devices.append(self.get_device(action['device']))
                action['device_pointer'] = devices
                return action
            except:
                raise YomboWarning("Error while searching for device, could not be found: %s" % action['device'],
                               104, 'devices_validate_action_callback', 'lib.devices')
        else:
            raise YomboWarning("For platform 'devices' as an 'action', must have 'device' and can be either device ID or device label.",
                               105, 'devices_validate_action_callback', 'lib.devices')

    def devices_do_action_callback(self, rule, action, options={}, **kwargs):
        """
        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
#        logger.error("firing device rule: {rule}", rule=rule)
#        logger.error("rule options: {options}", options=options)
        for device in action['device_pointer']:
            # print "the_message = device.get_message(self, cmd=%s)" % action['command']
            the_message = device.get_message(self, cmd=action['command'])
            # print "the-message = %s" % the_message
            if 'delay' in options and options['delay'] is not None:
                logger.debug("setting up a delayed command for {seconds} seconds in the future.", seconds=options['delay'])
                the_message.set_delay(delay=options['delay'])
    #        print "the_message: %s" % the_message
            the_message.send()
#            try:
#            except Exception,e :
#                print "got exception: %s" % e


class Device:
    """
    A class to manage a single device.  This clas contains various attributes
    about a device and can perform function on behalf of a device.  Can easily
    send a Yombo :ref:`Message` using a device instance.

    The self.status attribute stores the last 30 states the device has been in.

    Device: An item which was specified by a user or module that can be
    controlled and/or queried for status.  Examples include a lamp
    module, curtains, Plex client, rain sensor, etc.
    """
    def __init__(self, device, _DevicesLibrary, testDevice=False):
        """
        :param device: *(list)* - A device as passed in from the devices class. This is a
            dictionary with various device attributes.
        :ivar callBeforeChange: *(list)* - A list of functions to call before this device has it's status
            changed. (Not implemented.)
        :ivar callAfterChange: *(list)* - A list of functions to call after this device has it's status
            changed. (Not implemented.)
        :ivar device_id: *(string)* - The UUID of the device.
        :type device_id: string
        :ivar device_type_id: *(string)* - The device type UUID of the device.
        :ivar label: *(string)* - Device label as defined by the user.
        :ivar description: *(string)* - Device description as defined by the user.
        :ivar enabled: *(bool)* - If the device is enabled - can send/receive command and/or
            status updates.
        :ivar pin_required: *(bool)* - If a pin is required to access this device.
        :ivar pin_code: *(string)* - The device pin number.
            system to deliver commands and status update requests.
        :ivar created: *(int)* - When the device was created; in seconds since EPOCH.
        :ivar updated: *(int)* - When the device was last updated; in seconds since EPOCH.
        :ivar last_command: *(dict)* - A dictionary of up to the last 30 command messages.
        :ivar status_history: *(dict)* - A dictionary of strings for current and up to the last 30 status values.
        :ivar device_variables: *(dict)* - The device variables as defined by various modules, with
            values entered by the user.
        :ivar available_commands: *(list)* - A list of command_id's that are valid for this device.
        """
        logger.debug("New device - info: {device}", device=device)

        self.Status = namedtuple('Status', "device_id, set_time, device_state, human_status, machine_status, machine_status_extra, source, uploaded, uploadable")
        self.Command = namedtuple('Command', "time, cmduuid, source")

        self.call_before_command = []
        self.call_after_command = []

        self.device_id = device["id"]
        self.device_type_id = device["device_type_id"]
        self.label = device["label"]
        self.description = device["description"]
        self.enabled = int(device["status"])  # status from database means enabled or not.
        self.pin_required = int(device["pin_required"])
        self.pin_code = device["pin_code"]
        self.pin_timeout = int(device["pin_timeout"])
        self.voice_cmd = device["voice_cmd"]
        self.voice_cmd_order = device["voice_cmd_order"]
        self.created = int(device["created"])
        self.updated = int(device["updated"])
        self.updated_srv = int(device["updated_srv"])

        self.last_command = deque({}, 30)
        self.status_history = deque({}, 30)
        self._DevicesLibrary = _DevicesLibrary
        self.testDevice = testDevice
        self.available_commands = []
        self.device_variables = {'asdf':'qwer'}
        self.device_route = {}  # Destination module to send commands to
        self._helpers = {}  # Helper class provided by route module that can provide additional features.
        self._CommandsLibrary = self._DevicesLibrary._Libraries['commands']

        # this registers the device's device type so others know what kind of device this is.
        self._registered_device_type = self._DevicesLibrary._DeviceTypes.add_registered_device(self)

        if device['status'] == 1:
            self.enabled = True
        else:
            self.enabled = False

    def __str__(self):
        """
        Print a string when printing the class.  This will return the device_id so that
        the device can be identified and referenced easily.
        """
        return self.device_id

    def _init_(self):
        """
        Performs items that required deferreds.
        :return:
        """
        def set_commands(commands):
            for command in commands:
                self.available_commands.append(str(command.command_id))

        def set_variables(vars):
            # print("GOT DEVICE VARS!!!!! %s" % vars)
            self.device_variables = vars

        def gotException(failure):
           print("Exception : %r" % failure)
           return 100  # squash exception, use 0 as value for next stage

        # d = self._DevicesLibrary._Libraries['localdb'].get_commands_for_device_type(self.device_type_id)
        # d.addCallback(set_commands)
        # d.addErrback(gotException)
        # d.addCallback(lambda ignored: self._DevicesLibrary._Libraries['localdb'].get_variables('device', self.device_id))

        d = self._DevicesLibrary._Libraries['localdb'].get_variables('device', self.device_id)
        d.addErrback(gotException)
        d.addCallback(set_variables)
        d.addErrback(gotException)

        if self.testDevice is False:
            d.addCallback(lambda ignored: self.load_history(35))
        return d

    def dump(self):
        """
        Export device variables as a dictionary.
        """
        return {'device_id': str(self.device_id),
                'device_type_id': str(self.device_type_id),
                'label': str(self.label),
                'description': str(self.description),
                'enabled': int(self.enabled),
                'pin_code': "********",
                'pin_required':  int(self.pin_required),
                'pin_timeout': int(self.pin_timeout),
                'voice_cmd': str(self.voice_cmd),
                'voice_cmd_order': str(self.voice_cmd_order),
                'created': int(self.created),
                'updated': int(self.updated),
                'status_history': copy.copy(self.status_history),
               }

    def do_command(self, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None, **kwargs):
        """
        Do a command. Will call _do_command_ hook so modules can process the request.

        If a pin is required, "pin" must be included as one of the arguments. All **kwargs are sent with the
        hook call.

        :raises YomboDeviceError: Raised when:

            - cmd doesn't exist
            - delay or max_delay is not a float or int.

        :raises YomboPinCodeError: Raised when:

            - pin is required but not recieved one.

        :param cmd: Command ID or Label to send.
        :param pin: A pin to check.
        :param request_id: Request ID for tracking.
        :param delay: How many seconds to delay sending the command.
        :param kwargs: If a command is not sent at the delay sent time, how long can pass before giving up. For example, Yombo Gateway not running.
        :return:
        """
        if self.pin_required == 1:
                if pin is None:
                    raise YomboPinCodeError("'pin' is required, but missing.")
                else:
                    if self.pin_code != pin:
                        raise YomboPinCodeError("'pin' supplied is incorrect.")

        logger.debug("device kwargs: {kwargs}", kwargs=kwargs)

        if isinstance(cmd, Device):
            cmdobj = cmd
        else:
            cmdobj = self._CommandsLibrary.get_command(cmd)

        print("cmdobj is: %s" % cmdobj)

#        if self.validate_command(cmdobj) is not True:
        if str(cmdobj.command_id) not in self.available_commands:
            logger.warn("Requested command: {cmduuid}, but only have: {ihave}",
                        cmduuid=cmdobj.command_id, ihave=self.available_commands)
            raise YomboDeviceError("Invalid command requested for device.", errorno=103)

        cur_time = time()
        if request_id is None:
            request_id = random_string(length=16)
        kwargs['request_id'] = request_id

        if max_delay is not None:
            if six.integer_types(max_delay) or isinstance(max_delay, float):
                if max_delay < 0:
                    raise YomboDeviceError("'max_delay' should be positive only.")

        if not_before is not None:
            if six.integer_types(not_before) or isinstance(not_before, float):
                if not_before < cur_time:
                    raise YomboDeviceError("'not_before' time should be epoch second in the future, not the past.")

                # self.delay_queue = yield self._Libraries['SQLDict'].get(self, 'delay_queue')
                # {'lmnop123', { 'not_before':123, 'max_delay': 100, 'kwargs':**kwargs} }

                when = not_before - time()
                self._DevicesLibrary.delay_queue[request_id] = {
                        'command': cmdobj.command_id,
                        'not_before': when,
                        'max_delay': max_delay,
                        'kwargs': kwargs,
                    }
                self._DevicesLibrary.reactors[request_id] = reactor.callLater(when, self.do_command_delayed, request_id)
            else:
                raise YomboDeviceError("not_before' must be a float or int.")

        elif delay is not None:
            if six.integer_types(delay) or isinstance(delay, float):
                if delay < 0:
                    raise YomboDeviceError("'delay' should be positive only.")

                # {'lmnop123', { 'not_before':123, 'max_delay': 100, 'kwargs':**kwargs} }

                when = time() + delay
                self._DevicesLibrary.delay_queue[request_id] = {
                        'command': cmdobj.command_id,
                        'not_before': when,
                        'max_delay': max_delay,
                        'kwargs': kwargs,
                    }
                self._DevicesLibrary.reactors[request_id] = reactor.callLater(when, self.do_command_delayed, request_id)
            else:
                raise YomboDeviceError("'not_before' must be a float or int.")

        else:
            self.do_command_hook(cmdobj, kwargs)
        return request_id

    def do_command_delayed(self, request_id):

        request = self._DevicesLibrary.delay_queue[request_id]
        cmdobj = self._CommandsLibrary.get_command(request['command'])
        self.do_command_hook(cmdobj, request['kwargs'])
        del self._DevicesLibrary.delay_queue[request_id]

    def do_command_hook(self, cmdobj, kwargs):
        """
        Performs the actual sending of a device command. It does this through the hook system. This allows any module
        to setup any monitoring, or perfom the actual action.

        When a device changes state, whatever module changes the state of a device, or is responsible for reporting
        those changes, it *must* call "self._Devices['devicename/deviceid'].set_state()

        **Hooks called**:

        * _devices_command_ : Sends kwargs: *device*, the device object and *command*. This receiver will be
          responsible for obtaining whatever information it needs to complete the action being requested.

        :param cmdobj:
        :param kwargs:
        :return:
        """
        kwargs['command'] = cmdobj
        kwargs['device'] = self
        global_invoke_all('_device_command_', **kwargs)

    def get_status(self, history=0):
        """
        Gets the history of the device status.

        :param history: How far back to go. 0 = previoius, 1 - the one before that, etc.
        :return:
        """
        return self.status_history[history]

    def set_status(self, **kwargs):
        """
        Usually called by the device's command/logic module to set/update the
        device status. This can also be called externally as needed.

        :raises YomboDeviceError: Raised when:

            - If no valid status sent in. Errorno: 120
            - If statusExtra was set, but not a dictionary. Errorno: 121
            - If payload was set, but not a dictionary. Errorno: 122
        :param kwargs: key/value dictionary with the following keys-

            - device_state *(float)* - Soemthing that can be used to graph. on = 1, off =0. Lamp at 50% = 0.5
            - human_status *(int or string)* - The new status.
            - machine_status *(int or string)* - The new status.
            - machine_status_extra *(dict)* - Extra status as a dictionary.
            - source *(string)* - The source module or library name creating the status.
            - silent *(any)* - If defined, will not broadcast a status update
              message; atypical.
            - payload *(dict)* - a dict to be appended to the payload portion of the
              status message.
        """
        logger.debug("set_status called...: {kwargs}", kwargs=kwargs)
        self._set_status(**kwargs)
        if 'silent' not in kwargs:
            self.send_status(**kwargs)

    def _set_status(self, **kwargs):
        logger.debug("_set_status called...")
        machine_status = None
        if 'machine_status' not in kwargs:
            raise YomboDeviceError("set_status was called without a real machine_status!", errorno=120)

        device_state = kwargs.get('device_state', 0)
        human_status = kwargs.get('human_status', machine_status)
        machine_status = kwargs['machine_status']
        machine_status_extra = kwargs.get('machine_status_extra', '')
        source = kwargs.get('source', 'unknown')
        uploaded = kwargs.get('uploaded', 0)
        uploadable = kwargs.get('uploadable', 0)
        set_time = time()

        new_status = self.Status(self.device_id, set_time, device_state, human_status, machine_status, machine_status_extra, source, uploaded, uploadable)
        self.status_history.appendleft(new_status)
        if self.testDevice is False:
            self._DevicesLibrary._status_updates_to_save[random_string(length=12)] = new_status
            if len(self._DevicesLibrary._status_updates_to_save) > 120:
                self._DevicesLibrary._save_status()
        self._DevicesLibrary.check_trigger(self.device_id, new_status)

    def send_status(self, **kwargs):
        """
        Tell the message system to broadcast the current status of a device. This
        is typically only called internally when a device status changes. Shouldn't
        need to call this from a module. Just send a command to the device and
        this function will be called automatically as needed.

        :param kwargs:
        :return:
        """
        logger.debug("send_status called...")
        if 'dest' in kwargs:
            dest = kwargs['dest']
        else:
            dest = 'yombo.gateway.all'
        if 'src' in kwargs:
            src = kwargs['src']
        else:
            src = 'yombo.gateway.core.device'
        if 'payloadAddon' in kwargs:
            payloadAddon = kwargs['payloadAddon']
        else:
            payloadAddon = {}

        payload = {"deviceobj" : self,
                   "status" : self.status_history[0],
                   "previous_status" : self.status_history[1],
                  }
        try:
            payload.update(payloadAddon)
        except:
            pass
        self._DevicesLibrary._Statistics.increment("lib.devices.status_change", anon=True)
        msg = {
               'msgOrigin'     : src,
               'msgDestination': dest,
               'msgType'       : "status",
               'msgStatus'     : "new",
               'msgStatusExtra': "",
               'uuidtype'      : "APDS",
               'payload'       : payload,
              }
        message = Message(**msg)
        message.send()

    def remove_delayed(self):
        """
        Remove any messages that might be set to be called later that
        relates to this device.  Easy, just tell the messages library to 
        do that for us.
        """
        self._DevicesLibrary._MessageLibrary.device_delay_cancel(self.device_id)

    def get_delayed(self):
        """
        List messages that are to be sent at a later time.
        """
        self._DevicesLibrary._MessageLibrary.device_delay_list(self.device_id)

    def load_history(self, howmany=35):
        """
        Loads device history into the device instance. This method gets the data from the db and adds a callback
        to _do_load_history to actually set the values.

        :param howmany:
        :return:
        """
        d =  self._DevicesLibrary._Libraries['LocalDB'].get_device_status(id=self.device_id, limit=howmany)
        d.addCallback(self._do_load_history)
        return d

    def _do_load_history(self, records):
        if len(records) == 0:
            self.status_history.append(self.Status(self.device_id, 0, 0, 'NA', 'NA', {}, '', 0, 0))
        else:
            for record in records:
                self.status_history.appendleft(self.Status(record['device_id'], record['set_time'], record['device_state'], record['human_status'], record['machine_status'],record['machine_status_extra'], record['source'], record['uploaded'], record['uploadable']))
#                              self.Status = namedtuple('Status',  "device_id,           set_time,           device_state,           human_status,           machine_status,                             machine_status_extra,             source,           uploaded,           uploadable")

        #logger.debug("Device load history: {device_id} - {status_history}", device_id=self.device_id, status_history=self.status_history)

    def validate_command(self, command_id):
#        print "checking cmdavail for %s, looking for '%s': %s" % (self.label, command_id, self.available_commands)
        if str(command_id) in self.available_commands:
            return True
        else:
            return False

    def update(self, record):
                # try:
        #     # todo: refactor voicecommands. Need to be able to update/delete them later.
        #     self._VoiceCommandsLibrary.add(record["voice_cmd"], "", record["id"], record["voice_cmd_order"])
        # except:
        #     pass

        if 'label' in record:
            self._DevicesLibrary._devicesByName[record['label']] = self._devicesByName.pop(record["label"])  # Update label searching
            self.label = record['label']

        # check if device_type_id changes.
        if 'device_type_id' in record:
            if record['device_type_id'] != self.device_type_id:
                del self._DevicesLibrary._DeviceTypes. _devicesByDeviceTypeByUUID[self.device_type_id][self.device_id]
                self.device_type_id = record['device_type_id']
                self._DevicesLibrary._devicesByDeviceTypeByUUID[self.device_type_id][self.device_id]

        # global_invoke_all('_devices_update_', **{'id': record['id']})  # call hook "device_update" when adding a new device.
