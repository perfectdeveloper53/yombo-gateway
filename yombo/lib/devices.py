# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  For development guides see: `Devices @ Module Development <https://yombo.net/docs/modules/devices/>`_

The devices library is primarily responsible for:
 
* Keeping track of all devices.
* Maintaining device state.
* Routing commands to modules for processing.
* Managing delay commands to send later.

The device (singular) class represents one device. This class has many functions
that help with utilizing the device. When possible, this class should be used for
controlling devices and getting/setting/querying status. The device class maintains
the current known device state.  Any changes to the device state are periodically
saved to the local database.

To send a command to a device is simple.

*Usage**:

.. code-block:: python

   # Three ways to send a command to a device. Going from easiest method, but less assurance of correct command
   # to most assurance.

   # Lets turn on every device this module manages.
   for device in self._Devices:
       self.Devices[device].command(cmd='off')

   # Lets turn off every every device, using a very specific command id.
   for device in self._Devices:
       self.Devices[device].command(cmd='js83j9s913')  # Made up id, but can be same as off

   # Turn off the christmas tree.
   self._Devices.command('christmas tree', 'off')

   # Get devices by device type:
   deviceList = self._Devices.search(device_type='x10_appliance')  # Can search on any device attribute

   # Turn on all x10 lights off (regardless of house / unit code)
   allX10Lamps = self._DeviceTypes.devices_by_device_type('x10_light')
   # Turn off all x10 lamps
   for lamp in allX10Lamps:
       lamp.command('off')

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from __future__ import print_function
try:  # Prefer simplejson if installed, otherwise json will work swell.
    import simplejson as json
except ImportError:
    import json

from hashlib import sha1
import copy
from collections import deque, namedtuple
from time import time
from collections import OrderedDict

# Import 3rd-party libs
import yombo.ext.six as six

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, Deferred, returnValue

# Import Yombo libraries
from yombo.core.exceptions import YomboPinCodeError, YomboDeviceError, YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import random_string, split, global_invoke_all, string_to_number, search_instance, do_search_instance
from yombo.utils.maxdict import MaxDict
from yombo.lib.commands import Command  # used only to determine class type
logger = get_logger('library.devices')


class Devices(YomboLibrary):
    """
    Manages all devices and provides the primary interaction interface. The
    primary functions developers should use are:
        * :py:meth:`__getitem__ <Devices.__getitem__>` - Get a pointer to a device, using self._Devices as a dictionary of objects.
        * :py:meth:`command <Devices.command>` - Send a command to a device.
        * :py:meth:`search <Devices.search>` - Get a pointer to a device, using device_id or device label.
    """

    def __contains__(self, device_requested):
        """
        .. note:: The device must be enabled to be found using this method. Use :py:meth:`get <Devices.get>`
           to set status allowed.

        Checks to if a provided device label, device machine label, or device id exists.

            >>> if '137ab129da9318' in self._Devices:  #by id

        or:

            >>> if 'living room light' in self._Devices:  #by label

        :raises YomboWarning: Raised when request is malformed.
        :param device_requested: The device ID or label to search for.
        :type device_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(device_requested)
            return True
        except:
            return False

    def __getitem__(self, device_requested):
        """
        .. note:: The device must be enabled to be found using this method. Use :py:meth:`get <Devices.get>`
           to set status allowed.

        Finds the device requested by device label, device machine label, or device id exists.

            >>> my_light = self._Devices['137ab129da9318']  #by id

        or:

            >>> my_light = self._Devices['living room light']  #by name

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param device_requested: The device ID, machine_label, or label to search for.
        :type device_requested: string
        :return: A pointer to the device type instance.
        :rtype: instance
        """
        return self.get(device_requested)

    def __setitem__(self, device_requested, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        :param device_requested: The atom key to replace the value for.
        :type device_requested: string
        """
        raise Exception("Not allowed.")

    def __delitem__(self, device_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        :param device_requested: 
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter devices. """
        return self.devices.__iter__()

    def __len__(self):
        """
        Returns an int of the number of device configured.
        
        :return: The number of devices configured.
        :rtype: int
        """
        return len(self.devices)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo devices library"

    def keys(self):
        """
        Returns the keys (device ID's) that are configured.
        
        :return: A list of device IDs. 
        :rtype: list
        """
        return self.devices.keys()

    def items(self):
        """
        Gets a list of tuples representing the devices configured.
        
        :return: A list of tuples.
        :rtype: list
        """
        return self.devices.items()

    def iteritems(self):
        return self.devices.iteritems()

    def iterkeys(self):
        return self.devices.iterkeys()

    def itervalues(self):
        return self.devices.itervalues()

    def values(self):
        return self.devices.values()

    def _init_(self):
        """
        Sets up basic attributes.
        """
        self._AutomationLibrary = self._Loader.loadedLibraries['automation']
        self._VoiceCommandsLibrary = self._Loader.loadedLibraries['voicecmds']

        self.load_deferred = None  # Prevents loader from moving on past _load_ until we are done.
        self.devices = {}
        self.device_search_attributes = ['device_id', 'device_type_id', 'machine_label', 'label', 'description',
            'pin_required', 'pin_code', 'pin_timeout', 'voice_cmd', 'voice_cmd_order', 'statistic_label', 'status',
            'created', 'updated', 'updated_srv']

        self.gwid = self._Configs.get("core", "gwid")
        # self._save_status_loop = None

        # used to store delayed queue for restarts. It'll be a bare, dehydrated version.
        # store the above, but after hydration.
        self.delay_queue_active = {}
        self.delay_queue_unique = {}  # allows us to only create delayed commands for unique instances.

        self.startup_queue = {}  # Place device commands here until we are ready to process device commands
        self.processing_commands = False

    def _load_(self):
        """
        Loads devices from the database and imports them.
        :return: 
        """
        self.load_deferred = Deferred()
        self._load_devices_from_database()
        return self.load_deferred

    def _start_(self):
        """
        Tells the system we are in run mode. Also, connects to MQTT broker to listen for device commands.
        :return: 
        """
        if self._Atoms['loader.operation_mode'] == 'run':
            self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming, client_id='devices')
            self.mqtt.subscribe("yombo/devices/+/get")
            self.mqtt.subscribe("yombo/devices/+/cmd")

    def _stop_(self):
        """
        Cleans up any pending deferreds.
        
        :return: 
        """
        if self.load_deferred is not None and self.load_deferred.called is False:
            self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    def _reload_(self):
        return self._load_()

    def _modules_prestarted_(self):
        """
        On start, sends all queued messages. Then, check delayed messages for any messages that were missed. Send
        old messages and prepare future messages to run.
        """
        self.processing_commands = True
        for command, request in self.startup_queue.iteritems():
            self.command(request['device_id'], request['command_id'], not_before=request['not_before'],
                    max_delay=request['max_delay'], **request['kwargs'])
        self.startup_queue.clear()

    # def _statistics_lifetimes_(self, **kwargs):
    #     """
    #     For devices, we track statistics down to the nearest 5 minutes, and keep for 1 year.
    #     """
    #     return {'devices.#': {'size': 300, 'lifetime': 365},
    #             'energy.#': {'size': 300, 'lifetime': 365}}
    #     # we don't keep 6h averages.

    @inlineCallbacks
    def _load_devices_from_database(self):
        """
        Loads devices from database and sends them to :py:meth:`import_device <Devices.import_device>`
        
        This can be triggered either on system startup or when new/updated devices have been saved to the
        database and we need to refresh existing devices.
        """
        devices = yield self._LocalDB.get_devices()
        logger.debug("Loading devices:::: {devices}", devices=devices)
        if len(devices) > 0:
            for record in devices:
                record = record.__dict__
                if record['energy_map'] is not None:
                    record['energy_map'] = json.loads(str(record['energy_map']))
                logger.debug("Loading device: {record}", record=record)
                yield self.import_device(record)
        yield self._load_delay_queue()

    def sorted(self, key=None):
        """
        Returns an OrderedDict, sorted by key.  If key is not set, then default is 'label'.

        :param key: Attribute contained in a device to sort by.
        :type key: str
        :return: All devices, sorted by key.
        :rtype: OrderedDict
        """
        if key is None:
            key = 'label'
        return OrderedDict(sorted(self.devices.iteritems(), key=lambda i: i[1][key]))

    @inlineCallbacks
    def import_device(self, device, test_device=None):  # load ore re-load if there was an update.
        """
        Add a new device to memory or update an existing device.

        **Hooks called**:

        * _device_before_load_ : If added, sends device dictionary as 'device'
        * _device_before_update_ : If updated, sends device dictionary as 'device'
        * _device_loaded_ : If added, send the device instance as 'device'
        * _device_updated_ : If updated, send the device instance as 'device'

        :param device: A dictionary of items required to either setup a new device or update an existing one.
        :type device: dict
        :param test_device: Used for unit testing.
        :type test_device: bool
        :returns: Pointer to new device. Only used during unittest
        """
        if test_device is None:
            test_device = False


        device_id = device["id"]
        if device_id not in self.devices:
            import_state = 'new'
            global_invoke_all('_device_before_load_',
                              **{'device': device})
            self.devices[device_id] = Device(device, self)
        if device_id not in self.devices:
            import_state = 'update'
            global_invoke_all('_device_before_update_',
                              **{'device': device})
            self.devices[device_id].update_attributes(device)

        yield self.devices[device_id]._init_()

        try:
            self._VoiceCommandsLibrary.add_by_string(device["voice_cmd"], None, device["id"],
                                                     device["voice_cmd_order"])
        except YomboWarning:
            logger.debug("Device {label} has an invalid voice_cmd {voice_cmd}", label=device["label"],
                         voice_cmd=device["voice_cmd"])

        # logger.debug("_add_device: {device}", device=device)

        if import_state == 'new':
            global_invoke_all('_device_loaded_',
                          **{'device': self.devices[device_id]})
        elif import_state == 'update':
            global_invoke_all('_device_updated_',
                              **{'device': self.devices[device_id]})
        # if test_device:
        #            returnValue(self.devices[device_id])

    @inlineCallbacks
    def _load_delay_queue(self):
        self.delay_queue_storage = yield self._Libraries['SQLDict'].get(self, 'delay_queue')
        # Now check to existing delayed messages.  If not too old, send otherwise delete them.  If time is in
        # future, setup a new reactor to send in future.
        for request_id in self.delay_queue_storage.keys():
            logger.info("module_started: delayQueue: {delay}", delay=self.delay_queue_storage[request_id])
            if self.delay_queue_storage[request_id]['unique_hash'] is not None:
                self.delay_queue_unique[self.delay_queue_storage[request_id]['unique_hash']] = request_id
            if request_id in self.delay_queue_active:
                logger.debug("Message already scheduled for delivery later. Possible from an automation rule. Skipping.")
                continue
            request = self.delay_queue_storage[request_id]
            # print("loading delayed command: %s" % request)
            if float(request['not_before']) < time(): # if delay message time has past, maybe process it.
                if time() - float(request['not_before']) > float(request['max_delay']):
                    # we're too late, just delete it.
                    del self.delay_queue_storage[request_id]
                    continue
                else:
                    # we're good, lets hydrate the request and send it.
                    self.command(request['device_id'], request['command_id'], request['kwargs'])

            else: # Still good, but still in the future. Set them up.
                self.command(request['device_id'], request['command_id'], not_before=request['not_before'],
                                max_delay=request['max_delay'], **request['kwargs'])
        self.load_deferred.callback(10)

    def command(self, device, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None, requested_by=None, input=None, **kwargs):
        """
        Tells the device to a command. This in turn calls the hook _device_command_ so modules can process the command
        if they are supposed to.

        If a pin is required, "pin" must be included as one of the arguments. All **kwargs are sent with the
        hook call.

        :raises YomboDeviceError: Raised when:

            - cmd doesn't exist
            - delay or max_delay is not a float or int.

        :raises YomboPinCodeError: Raised when:

            - pin is required but not recieved one.

        :param device: Device ID, machine_label, or Label.
        :type device: str
        :param cmd: Command ID, machine_label, or Label to send.
        :type cmd: str
        :param pin: A pin to check.
        :type pin: str
        :param request_id: Request ID for tracking. If none given, one will be created.
        :type request_id: str
        :param delay: How many seconds to delay sending the command. Not to be combined with 'not_before'
        :type delay: int or float
        :param not_before: An epoch time when the command should be sent. Not to be combined with 'delay'.
        :type not_before: int or float
        :param max_delay: How many second after the 'delay' or 'not_before' can the command be send. This can occur
            if the system was stopped when the command was supposed to be send.
        :type max_delay: int or float
        :param inputs: A list of dictionaries containing the 'input_type_id' and any supplied 'value'.
        :type input: list of dictionaries
        :param kwargs: Any additional named arguments will be sent to the module for processing.
        :type kwargs: named arguments
        :return: The request id.
        :rtype: str
        """
        return self.get(device).command(cmd, pin, request_id, not_before, delay, max_delay, **kwargs)

    def mqtt_incoming(self, topic, payload, qos, retain):
        """
        Processing any incoming MQTT messages we have subscribed to. This allows IoT type connections
        from various external sources.

        * yombo/devices/DEVICEID|DEVICEMACHINELABEL/get Value - Get some attribute
          * Value = state, human, machine, extra
        * yombo/devices/DEVICEID|DEVICEMACHINELABEL/cmd/CMDID|CMDMACHINELABEL Options - Send a command
          * Options - Either a string for a single variable, or json for multiple variables

        Examples: /yombo/devices/get/christmas_tree/cmd/on

        :param topic:
        :param payload:
        :param qos:
        :param retain:
        :return:
        """
        #  0       1       2       3        4
        # yombo/devices/DEVICEID/get|cmd/option
        parts = topic.split('/', 10)
        logger.debug("Yombo Devices got this: {topic} / {parts}", topic=topic, parts=parts)

        try:
            device_label = self.get(parts[2].replace("_", " "))
            device = self.get(device_label)
        except YomboDeviceError, e:
            logger.info("Received MQTT request for a device that doesn't exist: %s" % parts[2])
            return
        if parts[3] == 'get':
            status = device.status_history[0]

            if payload == '' or payload == 'all':
                self.mqtt.publish('yombo/devices/%s/status' % device.machine_label, json.dumps(device.status_history[0]))
            elif payload == 'human':
                self.mqtt.publish('yombo/devices/%s/status/human' % device.machine_label, str(status.human_status))
            elif payload == 'machine':
                self.mqtt.publish('yombo/devices/%s/status/machine' % device.machine_label, str(status.machine_status))
            elif payload == 'extra':
                self.mqtt.publish('yombo/devices/%s/status/extra' % device.machine_label, str(status.machine_status_extra))
            elif payload == 'last':
                self.mqtt.publish('yombo/devices/%s/status/last' % device.machine_label, str(status.set_time))
            elif payload == 'requested_by':
                self.mqtt.publish('yombo/devices/%s/status/requested_by' % device.machine_label, str(status.requested_by))
        elif parts[3] == 'cmd':
            try:
                device.command(cmd=parts[4], reported_by='yombo.gateway.lib.devices.mqtt_incoming')

            except Exception as e:
                logger.warn("Device received invalid command request for command: %s  Reason: %s" % (parts[4], e))

            if len(parts) > 5:
                status = device.status_history[0]
                if payload == '' or payload == 'all':
                    self.mqtt.publish('yombo/devices/%s/None' % device.machine_label,
                                      json.dumps(device.status_history[0]))
                elif parts[5] == 'human':
                    self.mqtt.publish('yombo/devices/%s/status/human' % device.machine_label, str(status.human_status))
                elif parts[5] == 'machine':
                    self.mqtt.publish('yombo/devices/%s/status/machine' % device.machine_label, str(status.machine_status))
                elif parts[5] == 'extra':
                    self.mqtt.publish('yombo/devices/%s/status/extra' % device.lmachine_label, str(status.machine_status_extra))
                elif parts[5] == 'last':
                    self.mqtt.publish('yombo/devices/%s/status/last' % device.machine_label, str(status.set_time))
                elif parts[5] == 'requested_by':
                    self.mqtt.publish('yombo/devices/%s/status/requested_by' % device.machine_label, str(status.requested_by))

    def list_devices(self, field=None):
        """
        Return a list of devices, returning the value specified in field.
        
        :param field: A string referencing an attribute of a device.
        :type field: string
        :return: 
        """
        if field is None:
            field = 'machine_label'

        if field not in self.device_search_attributes:
            raise YomboWarning('Invalid field for device attribute: %s' % field)

        devices = []
        for device_id, device in self.devices.iteritems():
            devices.append(getattr(device, field))
        return devices

    def get(self, device_requested, limiter=None, status=None):
        """
        Performs the actual search.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find devices:
           
            >>> self._Devices['8w3h4sa']
        
        or:
        
            >>> self._Devices['porch light']

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :param device_requested: The device ID, machine_label, or device label to search for.
        :type device_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the device to check for.
        :type status: int
        :return: Pointer to requested device.
        :rtype: dict
        """
        # logger.debug("looking for: {device_requested}", device_requested=device_requested)
        if limiter is None:
            limiter = .89

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10

        if device_requested in self.devices:
            item = self.devices[device_requested]
            if status is not None and item.status != status:
                raise KeyError("Requested device found, but has invalid status: %s" % item.status)
            return item
        else:
            attrs = [
                {
                    'field': 'device_id',
                    'value': device_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'machine_label',
                    'value': device_requested,
                    'limiter': limiter,
                },
                {
                    'field': 'label',
                    'value': device_requested,
                    'limiter': limiter,
                }
            ]
            try:
                # logger.debug("Get is about to call search...: %s" % device_requested)
                found, key, item, ratio, others = do_search_instance(attrs, self.devices,
                                                                     self.device_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                # logger.debug("found device by search: {device_id}", device_id=key)
                if found:
                    return self.devices[key]
                else:
                    raise KeyError("Device not found: %s" % device_requested)
            except YomboWarning, e:
                raise KeyError('Searched for %s, but had problems: %s' % (device_requested, e))

    def search(self, _limiter=None, _operation=None, **kwargs):
        """
        Search for devices based on attributes for all devices.
        
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the device to check for.
        :return: 
        """
        return search_instance(kwargs,
                               self.devices,
                               self.device_search_attributes,
                               _limiter,
                               _operation)

    @inlineCallbacks
    def add_device(self, data, **kwargs):
        """
        Add a new device. This will also make an API request to add device at the server too.

        :param data:
        :param kwargs:
        :return:
        """
        logger.debug("Add new device.  Data: {data}", data=data)
        api_data = {
            'gateway_id': self.gwid,
        }

        try:
            for key in data.keys():
                if data[key] == "":
                    data[key] = None
                elif key in ['statistic_lifetime', 'pin_timeout']:
                    if data[key] is None or (isinstance(data[key], str) and data[key].lower() == "none"):
                        del data[key]
                    else:
                        data[key] = int(data[key])
        except Exception as e:
            results = {
                'status': 'failed',
                'msg': "Couldn't add device",
                'apimsg': e,
                'apimsghtml': e,
                'device_id': '',
            }
            returnValue(results)

        for key, value in data.iteritems():
            if key == 'energy_map':
                api_data['energy_map'] = json.dumps(data['energy_map'], separators=(',',':'))
            else:
                api_data[key] = data[key]

        # print("apidata: %s" % api_data)
        try:
            global_invoke_all('_device_before_add_', **{'called_by': self, 'device': data})
        except YomboHookStopProcessing as e:
            raise YomboWarning("Adding device was halted by '%s', reason: %s" % (e.name, e.message))

        if 'device_id' not in api_data:
            logger.debug("POSTING device. api data: {api_data}", api_data=api_data)
            device_results = yield self._YomboAPI.request('POST', '/v1/device', api_data)
            logger.debug("add new device results: {device_results}", device_results=device_results)
        else:
            logger.debug("PATCHING device. api data: {api_data}", api_data=api_data)
            del api_data['gateway_id']
            del api_data['device_type_id']
            device_results = yield self._YomboAPI.request('PATCH', '/v1/device/%s' % data['device_id'], api_data)
            logger.debug("edit device results: {device_results}", device_results=device_results)

        if device_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't add device",
                'apimsg': device_results['content']['message'],
                'apimsghtml': device_results['content']['html_message'],
                'device_id': '',
            }
            returnValue(results)

        if 'variable_data' in data:
            # print("data['variable_data']: %s", data['variable_data'])
            variable_results = yield self.set_device_variables(device_results['data']['id'], data['variable_data'])
            # print("variable_results: %s" % variable_results)
            if variable_results['code'] > 299:
                results = {
                    'status': 'failed',
                    'msg': "Device saved, but had problems with saving variables: %s" % variable_results['msg'],
                    'apimsg': variable_results['apimsg'],
                    'apimsghtml': variable_results['apimsghtml'],
                    'device_id': device_results['data']['id'],
                }
                returnValue(results)

        logger.debug("device edit results: {device_results}", device_results=device_results)
        results = {
            'status': 'success',
            'msg': "Device added.",
            'device_id': device_results['data']['id']
        }
        returnValue(results)

    #todo: convert to use a deferred semaphore
    @inlineCallbacks
    def set_device_variables(self, device_id, variables):
        # print("set variables: %s" % variables)
        for field_id, data in variables.iteritems():
            # print("devices.set_device_variables.data: %s" % data)
            for data_id, value in data.iteritems():
                if value == "":
                    continue
                if data_id.startswith('new_'):
                    post_data = {
                        'gateway_id': self.gwid,
                        'field_id': field_id,
                        'relation_id': device_id,
                        'relation_type': 'device',
                        'data_weight': 0,
                        'data': value,
                    }
                    # print("Posting new variable: %s" % post_data)
                    var_data_results = yield self._YomboAPI.request('POST', '/v1/variable/data', post_data)
                    if var_data_results['code'] > 299:
                        results = {
                            'status': 'failed',
                            'msg': "Couldn't add device variables",
                            'apimsg': var_data_results['content']['message'],
                            'apimsghtml': var_data_results['content']['html_message'],
                            'device_id': device_id
                        }
                        returnValue(results)
                else:
                    post_data = {
                        'data_weight': 0,
                        'data': value,
                    }
                    # print("PATCHing variable: %s" % post_data)
                    var_data_results = yield self._YomboAPI.request(
                        'PATCH',
                        '/v1/variable/data/%s' % data_id,
                        post_data
                    )
                    # print("var_data_results: %s" % var_data_results)
                    if var_data_results['code'] > 299:
                        results = {
                            'status': 'failed',
                            'msg': "Couldn't add device variables",
                            'apimsg': var_data_results['content']['message'],
                            'apimsghtml': var_data_results['content']['html_message'],
                            'device_id': device_id
                        }
                        returnValue(results)
        # print("var_data_results: %s" % var_data_results)
        returnValue({
            'status': 'success',
            'code': var_data_results['code'],
            'msg': "Device added.",
            'variable_id': var_data_results['data']['id']
        })

    @inlineCallbacks
    def delete_device(self, device_id):
        """
        So sad to delete, but life goes one. This will delete a device by calling the API to request the device be
        deleted.

        :param device_id: Device ID to delete. Will call API
        :type device_id: string
        :returns: Pointer to new device. Only used during unittest
        """
        if device_id not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to delete.", 300, 'delete_device', 'Devices')

        device_results = yield self._YomboAPI.request('DELETE', '/v1/device/%s' % device_id)
        # print("deleted device: %s" % device_results)
        if device_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't delete device",
                'apimsg': device_results['content']['message'],
                'apimsghtml': device_results['content']['html_message'],
                'device_id': device_id,
            }
            returnValue(results)

        self.devices[device_id].delete()

        results = {
            'status': 'success',
            'msg': "Device deleted.",
            'device_id': device_id
        }
        returnValue(results)

    @inlineCallbacks
    def edit_device(self, device_id, data, **kwargs):
        """
        Edit device settings. Accepts a list of items to change. This will also make an API request to update
        the server too.

        :param device_id: The device to edit
        :param data: a dict of items to update.
        :param kwargs:
        :return:
        """
        if device_id not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to delete.", 300, 'edit_device', 'Devices')

        device = self.devices[device_id]

        try:
            for key in data.keys():
                if data[key] == "":
                    data[key] = None
                elif key in ['statistic_lifetime', 'pin_timeout']:
                    if data[key] is None or (isinstance(data[key], str) and data[key].lower() == "none"):
                        del data[key]
                    else:
                        data[key] = int(data[key])
        except Exception as e:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit device",
                'apimsg': e,
                'apimsghtml': e,
                'device_id': '',
            }
            returnValue(results)

        api_data = {}
        for key, value in data.iteritems():
            # print("key (%s) is of type: %s" % (key, type(value)))
            if isinstance(value, str) and len(value) > 0 and hasattr(device, key):
                if key == 'energy_map':
                    api_data['energy_map'] = json.dumps(value, separators=(',',':'))
                    # print("energy map json: %s" % json.dumps(value, separators=(',',':')))
                else:
                    api_data[key] = value

        # print("send this data to api: %s" % api_data)
        device_results = yield self._YomboAPI.request('PATCH', '/v1/device/%s' % device_id, api_data)
        # print("got this data from api: %s" % device_results)
        if device_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't edit device",
                'apimsg': device_results['content']['message'],
                'apimsghtml': device_results['content']['html_message'],
                'device_id': device_id,
            }
            returnValue(results)

        if 'variable_data' in data:
            variable_results = yield self.set_device_variables(device_results['data']['id'], data['variable_data'])
            if variable_results['code'] > 299:
                results = {
                    'status': 'failed',
                    'msg': "Device saved, but had problems with saving variables: %s" % variable_results['msg'],
                    'apimsg': variable_results['apimsg'],
                    'apimsghtml': variable_results['apimsghtml'],
                    'device_id': device_id,
                }
                returnValue(results)

        device.update_attributes(data)

        results = {
            'status': 'success',
            'msg': "Device edited.",
            'device_id': device_results['data']['id']
        }
        global_invoke_all('devices_edit', **{'id': device_id})  # call hook "devices_delete" when deleting a device.
        returnValue(results)

    @inlineCallbacks
    def enable_device(self, device_id):
        """
        Enables a given device id.

        :param device_id:
        :return:
        """
        if device_id not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to delete.", 300, 'enable_device', 'Devices')

        api_data = {
            'status': 1,
        }

        device_results = yield self._YomboAPI.request('PATCH', '/v1/device/%s' % device_id, api_data)
        if device_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable device",
                'apimsg': device_results['content']['message'],
                'apimsghtml': device_results['content']['html_message'],
                'device_id': device_id,
            }
            returnValue(results)

        self.devices[device_id].enable()

        results = {
            'status': 'success',
            'msg': "Device disabled.",
            'device_id': device_results['data']['id']
        }
        global_invoke_all('devices_disabled', **{'id': device_id})  # call hook "devices_delete" when deleting a device.
        returnValue(results)

    @inlineCallbacks
    def disable_device(self, device_id):
        """
        Disables a given device id.

        :param device_id:
        :return:
        """
        if device_id not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to delete.", 300, 'disable_device', 'Devices')

        api_data = {
            'status': 0,
        }

        device_results = yield self._YomboAPI.request('PATCH', '/v1/device/%s' % device_id, api_data)
        if device_results['code'] > 299:
            results = {
                'status': 'failed',
                'msg': "Couldn't disable device",
                'apimsg': device_results['content']['message'],
                'apimsghtml': device_results['content']['html_message'],
                'device_id': device_id,
            }
            returnValue(results)

        self.devices[device_id].disable()

        results = {
            'status': 'success',
            'msg': "Device disabled.",
            'device_id': device_results['data']['id']
        }
        global_invoke_all('devices_disabled', **{'id': device_id})  # call hook "devices_delete" when deleting a device.
        returnValue(results)

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
        if record['device_id'] not in self.devices:
            raise YomboWarning("device_id doesn't exist. Nothing to do.", 300, 'update_device', 'Devices')
            # self.devices[record['device_id']].update(record)


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

    def _automation_source_list_(self, **kwargs):
        """
        Adds 'devices' to the list of source platforms (triggers)as a platform for rule sources (triggers).

        :param kwargs: None
        :return:
        """
        return [
            { 'platform': 'devices',
              'platform_description': 'Allows devices to be used as triggers for rules or macros.',
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
                device = self.get(portion['source']['device'], .89)
                portion['source']['device_pointers'] = device
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
        self._AutomationLibrary.triggers_add(rule['rule_id'], 'devices', rule['trigger']['source']['device_pointers'].device_id)

    def devices_get_value_callback(self, rule, portion, **kwargs):
        """
        A callback to the value for platform "states". We simply just do a get based on key_name.

        :param rule: The potential rule being added.
        :param portion: Dictionary containg everything in the portion of rule being fired. Includes source, filter, etc.
        :return:
        """
        return portion['source']['device_pointers'].machine_status

    def _automation_action_list_(self, **kwargs):
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
              'do_action_callback': self.devices_do_action_callback,  # function to be called to perform an action
              'get_available_items_callback': self.devices_get_available_devices_callback,  # get a value
              'get_available_options_for_item_callback': self.devices_get_device_options_callback,  # get a value
              }
         ]

    def devices_get_available_devices_callback(self, **kwargs):

        # iterate enabled devices
        # for each device, list available commands (device type commnads)
        # for each command, list any additional inputs (device type command inputs)

        devices = []
        for device_id, device in self.devices.iteritems():
            devices.append({
                'id': device.device_id,
                'machine_label': device.machine_label,
            })
        return devices

    def devices_get_device_options_callback(self, **kwargs):
        device_id = kwargs['id']
        return self.get(device_id).available_commands()

    def devices_validate_action_callback(self, rule, action, **kwargs):
        """
        A callback to check if a provided action is valid before being added as a possible action.

        :param rule: The potential rule being added.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        if 'command' not in action:
            raise YomboWarning("For platform 'devices' as an 'action', must have 'comand' and can be either command uuid or command label.",
                               103, 'devices_validate_action_callback', 'lib.devices')

        if 'device' in action:
            try:
                devices_text = split(action['device'])
                devices = []
                for device_text in devices_text:
                    devices.append(self.get(action['device']))
                action['device_pointers'] = devices
                return action
            except Exception, e:
                raise YomboWarning("Error while searching for device, could not be found: %s  Rason: %s" % (action['device'], e),
                               104, 'devices_validate_action_callback', 'lib.devices')
        else:
            raise YomboWarning("For platform 'devices' as an 'action', must have 'device' and can be either device ID, device machine_label, or device label.",
                               105, 'devices_validate_action_callback', 'lib.devices')

    def devices_do_action_callback(self, rule, action, options=None, **kwargs):
        """
        A callback to perform an action.

        :param rule: The complete rule being fired.
        :param action: The action portion of the rule.
        :param kwargs: None
        :return:
        """
        if options is None:
            options = {}
        logger.debug("firing device rule: {rule}", rule=rule)
        logger.debug("rule options: {options}", options=options)
        for device in action['device_pointers']:
            delay = None
            if 'delay' in options and options['delay'] is not None:
                logger.debug("setting up a delayed command for {seconds} seconds in the future.", seconds=options['delay'])
                delay=options['delay']

                if 'max_delay' in options:
                    max_delay=options['max_delay']
                else:
                    max_delay=60  # allow up to 60 seconds to pass...
            else:
                delay = None
                max_delay = None

            unique_hash = sha1('automation' + rule['name'] + action['command'] + device.machine_label).hexdigest()
            device.command(cmd=action['command'], delay=delay, max_delay=max_delay, **{'unique_hash': unique_hash})


class Device(object):
    """
    A class to manage a single device. This clas contains various attributes about the
    device as well as several functions. For exaqmple, a command be easily sent using the
    :py:meth:`command <Device.command>` function.


    The primary functions developers should use are:
        * :py:meth:`available_commands <Device.available_commands>` - List available commands for a device.
        * :py:meth:`command <Device.command>` - Send a command to a device.
        * :py:meth:`device_command_received <Device.device_command_received>` - Called by any module processing a command.
        * :py:meth:`device_command_pending <Device.device_command_pending>` - When a module needs more time.
        * :py:meth:`device_command_failed <Device.device_command_failed>` - When a module is unable to process a command.
        * :py:meth:`device_command_done <Device.device_command_done>` - When a command has completed..
        * :py:meth:`energy_get_usage <Device.energy_get_usage>` - Get current energy being used by a device.
        * :py:meth:`get_status <Device.get_status>` - Get a named tuple containing the device status.
        * :py:meth:`set_status <Device.set_status>` - Set the device status.
        * :py:meth:`get_status <Device.get_status>` - Get a named tuple containing the device status.
        * :py:meth:`get_status <Device.get_status>` - Get a named tuple containing the device status.
    """
    def __str__(self):
        """
        Print a string when printing the class.  This will return the device_id so that
        the device can be identified and referenced easily.
        """
        return self.device_id

    ## <start dict emulation>
    def __getitem__(self, key):
        return self.__dict__[key]

    def __repr__(self):
        return repr(self.__dict__)

    def __len__(self):
        return len(self.__dict__)

    def has_key(self, k):
        return self.__dict__.has_key(k)

    def keys(self):
        return self.__dict__.keys()

    def values(self):
        return self.__dict__.values()

    def items(self):
        return self.__dict__.items()

    def __cmp__(self, dict):
        return cmp(self.__dict__, dict)

    def __contains__(self, item):
        return item in self.__dict__

    def __iter__(self):
        return iter(self.__dict__)
    ##  <end dict emulation>

    def __init__(self, device, _DevicesLibrary, test_device=None):
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
        self._FullName = 'yombo.gateway.lib.Devices.Device'
        self._Name = 'Devices.Device'
        self._DevicesLibrary = _DevicesLibrary
        # logger.debug("New device - info: {device}", device=device)

        self.StatusTuple = namedtuple('Status', "device_id, set_time, energy_usage, human_status, human_message, machine_status, machine_status_extra, requested_by, reported_by, uploaded, uploadable")
        self.Command = namedtuple('Command', "time, cmduuid, requested_by")

        self.do_command_requests = MaxDict(300, {})
        self.call_before_command = []
        self.call_after_command = []

        self.device_id = device["id"]
        if test_device is None:
            self.test_device = False
        else:
            self.test_device = test_device

        self.last_command = deque({}, 30)
        self.status_history = deque({}, 30)
        self.device_variables = {}
        self.energy_type = None
        self.energy_map = None

        self.device_is_new = True
        self.update_attributes(device)

    @inlineCallbacks
    def _init_(self):
        """
        Performs items that require deferreds.

        :return:
        """
        # print("getting device variables for: %s" % self.device_id)
        self.device_variables = yield self._DevicesLibrary._Variables.get_variable_fields_data(
            data_relation_type='device',
            data_relation_id=self.device_id
        )
        yield self._DevicesLibrary._DeviceTypes.ensure_loaded(self.device_type_id)

        if self.test_device is False and self.device_is_new is True:
            self.device_is_new = False
            yield self.load_history(35)

    def update_attributes(self, device):
        """
        Sets various values from a device dictionary. This can be called when either new or
        when updating.
        
        :param device: 
        :return: 
        """
        if 'device_type_id' in device:
            self.device_type_id = device["device_type_id"]
        if 'machine_label' in device:
            self.machine_label = device["machine_label"]
        if 'label' in device:
            self.label = device["label"]
        if 'description' in device:
            self.description = device["description"]
        if 'pin_required' in device:
            self.pin_required = int(device["pin_required"])
        if 'pin_code' in device:
            self.pin_code = device["pin_code"]
        if 'pin_timeout' in device:
            try:
                self.pin_timeout = int(device["pin_timeout"])
            except:
                self.pin_timeout = None
        if 'voice_cmd' in device:
            self.voice_cmd = device["voice_cmd"]
        if 'voice_cmd_order' in device:
            self.voice_cmd_order = device["voice_cmd_order"]
        if 'statistic_label' in device:
            self.statistic_label = device["statistic_label"]  # 'myhome.groundfloor.kitchen'
        if 'statistic_lifetime' in device:
            self.statistic_lifetime = device["statistic_lifetime"]  # 'myhome.groundfloor.kitchen'
        if 'status' in device:
            self.status = int(device["status"])
        if 'created' in device:
            self.created = int(device["created"])
        if 'updated' in device:
            self.updated = int(device["updated"])
        if 'updated_srv' in device:
            self.updated_srv = int(device["updated_srv"])
        if 'energy_tracker_device' in device:
            self.energy_tracker_device = device['energy_tracker_device']
        if 'energy_tracker_source' in device:
            self.energy_tracker_source = device['energy_tracker_source']

        if 'energy_type' in device:
            self.energy_type = device['energy_type']

        if 'energy_map' in device:
            if device['energy_map'] is not None:
                # create an energy map from a dictionary
                energy_map_final = {}
                for percent, rate in device['energy_map'].iteritems():
                    energy_map_final[string_to_number(percent)] = string_to_number(rate)
                energy_map_final = OrderedDict(sorted(energy_map_final.items(), key=lambda (x, y): float(x)))
                self.energy_map = energy_map_final
            else:
                self.energy_map = None

        if self.device_is_new is True:
            global_invoke_all('_device_updated_', **{'device': self})

        # if 'variable_data' in device:
            # print("device.update_attributes: new: %s: " % device['variable_data'])
            # print("device.update_attributes: existing %s: " % self.device_variables)


    def available_commands(self):
        """
        Returns available commands for the current device.
        :return: 
        """
        return self._DevicesLibrary._DeviceTypes.device_type_commands(self.device_type_id)

    def dump(self):
        """
        Export device variables as a dictionary.
        """
        return {'device_id': str(self.device_id),
                'device_type_id': str(self.device_type_id),
                'machine_label': str(self.machine_label),
                'label': str(self.label),
                'description': str(self.description),
                'statistic_label': str(self.statistic_label),
                'statistic_lifetime': str(self.statistic_lifetime),
                'pin_code': "********",
                'pin_required':  int(self.pin_required),
                'pin_timeout': int(self.pin_timeout),
                'voice_cmd': str(self.voice_cmd),
                'voice_cmd_order': str(self.voice_cmd_order),
                'created': int(self.created),
                'updated': int(self.updated),
                'status_history': copy.copy(self.status_history),
               }

    def command(self, cmd, pin=None, request_id=None, not_before=None, delay=None, max_delay=None, requested_by=None, inputs=None, **kwargs):
        """
        Tells the device to a command. This in turn calls the hook _device_command_ so modules can process the command
        if they are supposed to.

        If a pin is required, "pin" must be included as one of the arguments. All **kwargs are sent with the
        hook call.

        :raises YomboDeviceError: Raised when:

            - cmd doesn't exist
            - delay or max_delay is not a float or int.

        :raises YomboPinCodeError: Raised when:

            - pin is required but not recieved one.

        :param cmd: Command ID or Label to send.
        :type cmd: str
        :param pin: A pin to check.
        :type pin: str
        :param request_id: Request ID for tracking. If none given, one will be created.
        :type request_id: str
        :param delay: How many seconds to delay sending the command. Not to be combined with 'not_before'
        :type delay: int or float
        :param not_before: An epoch time when the command should be sent. Not to be combined with 'delay'.
        :type not_before: int or float
        :param max_delay: How many second after the 'delay' or 'not_before' can the command be send. This can occur
            if the system was stopped when the command was supposed to be send.
        :type max_delay: int or float
        :param inputs: A list of dictionaries containing the 'input_type_id' and any supplied 'value'.
        :type input: list of dictionaries
        :param kwargs: Any additional named arguments will be sent to the module for processing.
        :type kwargs: named arguments
        :return: The request id.
        :rtype: str
        """
        if self.status != 1:
            raise YomboWarning("Device cannot be used, it's not enabled.")

        if isinstance(cmd, Command):
            cmdobj = cmd
        else:
            cmdobj = self._DevicesLibrary._Commands.get(cmd)

        # logger.debug("device::command kwargs: {kwargs}", kwargs=kwargs)
        # logger.debug("device::command requested_by: {requested_by}", requested_by=requested_by)
        if requested_by is None:  # soon, this will cause an error!
            requested_by = {
                    'user_id': 'Unknown',
                    'component': 'Unknown',
                    'gateway': 'Unknown'
            }

        if self.pin_required == 1:
                if pin is None:
                    raise YomboPinCodeError("'pin' is required, but missing.")
                else:
                    if self.pin_code != pin:
                        raise YomboPinCodeError("'pin' supplied is incorrect.")


        # print("cmdobj is: %s" % cmdobj)

#        if self.validate_command(cmdobj) is not True:
        if str(cmdobj.command_id) not in self.available_commands():
            logger.warn("Requested command: {cmduuid}, but only have: {ihave}",
                        cmduuid=cmdobj.command_id, ihave=self.available_commands())
            raise YomboDeviceError("Invalid command requested for device.", errorno=103)

        cur_time = time()
        # print("in device command: request_id: %s" % request_id)
        # print("in device command: kwargs: %s" % kwargs)
        # print("in device command: self._DevicesLibrary.delay_queue_unique: %s" % self._DevicesLibrary.delay_queue_unique)

        if 'unique_hash' in kwargs:
            unique_hash = kwargs['unique_hash']
            del kwargs['unique_hash']
        else:
            unique_hash = None
        if unique_hash in self._DevicesLibrary.delay_queue_unique:
            request_id = self._DevicesLibrary.delay_queue_unique[unique_hash]
        elif request_id is None:
            request_id = random_string(length=16)        # print("in device command: rquest_id 2: %s" % request_id)

        self.do_command_requests[request_id] = Device_Request(
            {
                'request_id': request_id,  # not as redundant as you may think!
                'sent_time': None,
                'command': cmdobj,
                'history': [],  # contains any notes about the status. Errors, etc.
                'inputs': inputs,
                'requested_by': requested_by,
            },
            self
        )

        if delay is not None or not_before is not None:  # if we have a delay, make sure we have required items
            if max_delay is None:
                    raise YomboDeviceError("'max_delay' Is required when delay or not_before is set!")
            if isinstance(max_delay, six.integer_types) or isinstance(max_delay, float):
                if max_delay < 0:
                    raise YomboDeviceError("'max_delay' should be positive only.")

        if not_before is not None:
            if isinstance(not_before, six.integer_types) or isinstance(not_before, float):
                if not_before < cur_time:
                    raise YomboDeviceError("'not_before' time should be epoch second in the future, not the past.")

                when = not_before - time()
                if request_id not in self._DevicesLibrary.delay_queue_storage:  # condition incase it's a reload
                    self._DevicesLibrary.delay_queue_storage[request_id] = {
                        'command_id': cmdobj.command_id,
                        'device_id': self.device_id,
                        'not_before': not_before,
                        'max_delay': max_delay,
                        'unique_hash': unique_hash,
                        'request_id': request_id,
                        'inputs': inputs,
                        'kwargs': kwargs,
                    }
                self._DevicesLibrary.delay_queue_active[request_id] = {
                    'command': cmdobj,
                    'device': self,
                    'not_before': not_before,
                    'max_delay': max_delay,
                    'unique_hash': unique_hash,
                    'kwargs': kwargs,
                    'request_id': request_id,
                    'inputs': inputs,
                    'reactor': None,
                }
                self._DevicesLibrary.delay_queue_active[request_id]['reactor'] = reactor.callLater(when, self.do_command_delayed, request_id)
                self.do_command_requests[request_id].set_status('delayed')
            else:
                raise YomboDeviceError("not_before' must be a float or int.")

        elif delay is not None:
            # print("delay = %s" % delay)
            if isinstance(delay, six.integer_types) or isinstance(delay, float):
                if delay < 0:
                    raise YomboDeviceError("'delay' should be positive only.")

                when = time() + delay
                if request_id not in self._DevicesLibrary.delay_queue_storage:  # condition incase it's a reload
                    self._DevicesLibrary.delay_queue_storage[request_id] = {
                        'command_id': cmdobj.command_id,
                        'device_id': self.device_id,
                        'not_before': when,
                        'max_delay': max_delay,
                        'unique_hash': unique_hash,
                        'kwargs': kwargs,
                        'inputs': inputs,
                        'request_id': request_id,
                    }
                self._DevicesLibrary.delay_queue_active[request_id] = {
                    'command': cmdobj,
                    'device': self,
                    'not_before': when,
                    'max_delay': max_delay,
                    'unique_hash': unique_hash,
                    'kwargs': kwargs,
                    'request_id': request_id,
                    'inputs': inputs,
                    'reactor': None,
                }
                self._DevicesLibrary.delay_queue_active[request_id]['reactor'] = reactor.callLater(delay, self.do_command_delayed, request_id)
                self.do_command_requests[request_id].set_status('delayed')
            else:
                raise YomboDeviceError("'not_before' must be a float or int.")

        else:
            kwargs['request_id'] = request_id
            self.do_command_hook(cmdobj, **kwargs)
        return request_id

    @inlineCallbacks
    def do_command_delayed(self, request_id):
        self.do_command_requests[request_id].set_sent_time()
        request = self._DevicesLibrary.delay_queue_active[request_id]
        # request['kwargs']['request_id'] = request_id
        request['kwargs']['request_id'] = request_id
        yield self.do_command_hook(request['command'], **request['kwargs'])
        del self._DevicesLibrary.delay_queue_storage[request_id]
        del self._DevicesLibrary.delay_queue_active[request_id]

    def do_command_hook(self, cmdobj, **kwargs):
        """
        Performs the actual sending of a device command. This calls the hook "_device_command_". Any modules that
        have implemented this hook can monitor or act on the hook.

        When a device changes state, whatever module changes the state of a device, or is responsible for reporting
        those changes, it *must* call "self._Devices['devicename/deviceid'].set_state()

        **Hooks called**:

        * _devices_command_ : Sends kwargs: *device*, the device object and *command*. This receiver will be
          responsible for obtaining whatever information it needs to complete the action being requested.

        :param request_id:
        :param cmdobj:
        :param kwargs:
        :return:
        """
        kwargs['command'] = cmdobj
        kwargs['device'] = self
        self.do_command_requests[kwargs['request_id']].set_sent_time()
        global_invoke_all('_device_command_', called_by=self, **kwargs)
        self._DevicesLibrary._Statistics.increment("lib.devices.commands_sent", anon=True)

    def device_command_received(self, request_id, **kwargs):
        """
        Called by any module that intends to process the command and deliver it to the automation device.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        self.do_command_requests[request_id].set_received_time()
        if 'message' in kwargs:
            self.do_command_requests[request_id].set_message(kwargs['message'])
        global_invoke_all('_device_command_status_', called_by=self, request=self.do_command_requests[request_id])

    def device_command_pending(self, request_id, **kwargs):
        """
        This should only be called if command processing takes more than 1 second to complete. This lets applications,
        users, and everyone else know it's pending. Calling this excessively can cost a lot of local CPU cycles.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        self.do_command_requests[request_id].set_pending_time()
        if 'message' in kwargs:
            self.do_command_requests[request_id].set_message(kwargs['message'])
        global_invoke_all('_device_command_status_', called_by=self, request=self.do_command_requests[request_id])

    def device_command_failed(self, request_id, **kwargs):
        """
        Should be called when a the command cannot be completed for whatever reason.

        A status can be provided: send a named parameter of 'message' with any value.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        self.do_command_requests[request_id].set_failed_time()
        if 'message' in kwargs:
            logger.warn('Device ({label}) command failed: {message}', label=self.label, message=kwargs['message'])
            self.do_command_requests[request_id].set_message(kwargs['message'])
        # print("self.do_command_requests[request_id]: %s" % self.do_command_requests[request_id])
        global_invoke_all('_device_command_status_', called_by=self, request=self.do_command_requests[request_id])

    def device_command_done(self, request_id, **kwargs):
        """
        Called by any module that has completed processing of a command request.

        A status can be provided: send a named parameter of 'message' with any value.

        :param request_id: The request_id provided by the _device_command_ hook.
        :return:
        """
        self.do_command_requests[request_id].set_finished_time()
        if 'message' in kwargs:
            self.do_command_requests[request_id].set_message(kwargs['message'])
        global_invoke_all('_device_command_status_', called_by=self, request=self.do_command_requests[request_id])

    def get_request(self, request_id):
        """
        Returns a request instance for a provide request_id.

        :raises KeyError: When an invalid request_id is requested.        
        :param request_id: A request id returned from a 'command()' call. 
        :return: Device_Request instance
        """
        return self.do_command_requests[request_id]

    def energy_get_usage(self, machine_status=None, **kwargs):
        """
        Determine the current energy usage.  Currently only supports energy maps. Returns a dictionary
        containing "energy_type" and "value".

        :param machine_status: Provide a status to base the calculation from. Otherwise, will use current device status.
        :type machine_status: int or float
        :return:
        """
        if machine_status is None:
            machine_status = self.status_history[0]['machine_status']

        if self.energy_tracker_source == 'calc':
            results = {
                'energy_type': self.energy_type,
                'value': self.energy_calc(machine_status),
            }
            return results
        return 0

    def energy_calc(self, machine_status, **kwargs):
        """
        Returns the energy being used based on a percentage the device is on.  Inspired by:
        http://stackoverflow.com/questions/1969240/mapping-a-range-of-values-to-another

        :param machine_status:
        :param map:
        :return:
        """
        # map = {
        #     0: 1,
        #     0.5: 100,
        #     1: 400,
        # }

        if self.energy_map == None:
            return 0   # if no map is found, we always return 0

        items = self.energy_map.items()
        for i in range(0, len(self.energy_map)-1):
            if items[i][0] <= machine_status <= items[i+1][0]:
                # print "translate(key, items[counter][0], items[counter+1][0], items[counter][1], items[counter+1][1])"
                # print "%s, %s, %s, %s, %s" % (key, items[counter][0], items[counter+1][0], items[counter][1], items[counter+1][1])
                return self.energy_translate(machine_status, items[i][0], items[i+1][0], items[i][1], items[i+1][1])
        raise KeyError("Cannot find map value for: %s  Must be between 0 and 1" % machine_status)

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
        # Figure out how 'wide' each range is
        leftSpan = leftMax - leftMin
        rightSpan = rightMax - rightMin
        # Convert the left range into a 0-1 range (float)
        valueScaled = float(value - leftMin) / float(leftSpan)
        # Convert the 0-1 range into a value in the right range.
        return rightMin + (valueScaled * rightSpan)

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
        :param kwargs: Named arguments:

            - human_status *(int or string)* - The new status.
            - human_message *(string)* - A human friendly text message to display.
            - machine_status *(int or string)* - The new status.
            - machine_status_extra *(dict)* - Extra status as a dictionary.
            - request_id *(string)* - Request ID that this should correspond to.
            - requested_by *(string)* - A dictionary containing user_id, component, and gateway.
            - silent *(any)* - If defined, will not broadcast a status update
              message; atypical.
        """
        # logger.debug("set_status called...: {kwargs}", kwargs=kwargs)
        self._set_status(**kwargs)
        if 'silent' not in kwargs:
            self.send_status(**kwargs)

    def _set_status(self, **kwargs):
        """
        A private function used to do the work of setting the status.
        :param kwargs: 
        :return: 
        """
        machine_status = None
        if 'machine_status' not in kwargs:
            raise YomboDeviceError("set_status was called without a real machine_status!", errorno=120)

        human_status = kwargs.get('human_status', machine_status)
        human_message = kwargs.get('human_message', machine_status)
        machine_status = kwargs['machine_status']
        machine_status_extra = kwargs.get('machine_status_extra', '')
        energy_usage = self.energy_get_usage(machine_status)
        uploaded = kwargs.get('uploaded', 0)
        uploadable = kwargs.get('uploadable', 0)
        set_time = time()

        requested_by = {
            'user_id': 'Unknown',
            'component': 'Unknown',
            'gateway': 'Unknown'
        }

        if "requested_by" in kwargs:
            requested_by = kwargs['requested_by']
            if isinstance(requested_by, dict) is False:
                kwargs['requested_by'] = requested_by
            else:
                if 'user_id' not in requested_by:
                    requested_by['user_id'] = 'Unknown'
                if 'component' not in requested_by:
                    requested_by['component'] = 'Unknown'
                if 'gateway' not in requested_by:
                    requested_by['gateway'] = 'Unknown'

        if "request_id" in kwargs and kwargs['request_id'] in self.do_command_requests:
            requested_by = self.do_command_requests[kwargs['request_id']].requested_by
            kwargs['command'] = self.do_command_requests[kwargs['request_id']].command

        kwargs['requested_by'] = requested_by

        reported_by = kwargs.get('reported_by', 'Unknown')
        kwargs['reported_by'] = reported_by

        if self.statistic_label is not None and self.statistic_label != "":
            self._DevicesLibrary._Statistics.datapoint("devices.%s" % self.statistic_label, machine_status)
            self._DevicesLibrary._Statistics.datapoint("energy.%s" % self.statistic_label, energy_usage)
        new_status = self.StatusTuple(self.device_id, set_time, energy_usage, human_status, human_message, machine_status, machine_status_extra, requested_by, reported_by, uploaded, uploadable)
        self.status_history.appendleft(new_status)
        if self.test_device is False:
            self._DevicesLibrary._LocalDB.save_device_status(**new_status.__dict__)
        self._DevicesLibrary.check_trigger(self.device_id, new_status)

        message = {
            'device_id': self.device_id,
            'device_machine_label': self.machine_label,
            'device_label': self.label,
            'machine_status': machine_status,
            'human_message': human_message,
            'human_status': human_status,
            'time': set_time,
            'requested_by': requested_by,
            'reported_by': reported_by,
        }

        if 'command' in kwargs:
            command_machine_label = kwargs['command'].machine_label
            message['command_machine_label'] = kwargs['command'].machine_label
            message['command_label'] = kwargs['command'].label
            message['command_id'] = kwargs['command'].command_id
        else:
            command_machine_label = machine_status

        self._DevicesLibrary.mqtt.publish("yombo/devices/%s/status" % self.machine_label, json.dumps(message), 1)

    def send_status(self, **kwargs):
        """
        Sends current status. Use set_status() to set the status, it will call this method for you.

        Calls the _device_status_ hook to send current device status. Useful if you just want to send a status of
        a device without actually changing the status.

        :param kwargs:
        :return:
        """

        message = {
            'device': self,
        }

        if 'command' in kwargs:
            message['command'] = kwargs['command']
        else:
            message['command'] = None

        if len(self.status_history) == 1:
            message['status'] = self.status_history[0]
            message['previous_status'] = None
        else:
            message['status'] = self.status_history[0]
            message['previous_status'] = self.status_history[1]

        global_invoke_all('_device_status_', called_by=self, **message)

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

    @inlineCallbacks
    def load_history(self, limit=None):
        """
        Loads device history into the device instance. This method gets the data from the db and adds a callback
        to _do_load_history to actually set the values.

        :param limit: int - How many history items should be loaded. Default: 35
        :return:
        """
        if limit is None:
            limit = False

        records =  yield self._DevicesLibrary._Libraries['LocalDB'].get_device_status(id=self.device_id, limit=limit)
        if len(records) == 0:
            requested_by = {
                'user_id': 'Unknown',
                'component': 'Unknown',
                'gateway': 'Unknown'
            }
            self.status_history.append(self.StatusTuple(self.device_id, int(time()), 0, 'Unknown', 'Unknown status for device', None, {}, requested_by, 'Unknown', 0, 1))
        else:
            for record in records:
                self.status_history.appendleft(self.StatusTuple(record['device_id'], record['set_time'], record['energy_usage'], record['human_status'], record['human_message'], record['machine_status'],record['machine_status_extra'], record['requested_by'], record['reported_by'], record['uploaded'], record['uploadable']))
#                              self.StatusTuple = namedtuple('Status',  "device_id,           set_time,          energy_usage,           human_status,           human_message,           machine_status,          machine_status_extra,           requested_by,           reported_by,           uploaded,           uploadable")

        #logger.debug("Device load history: {device_id} - {status_history}", device_id=self.device_id, status_history=self.status_history)

    def validate_command(self, command_requested):
        available_commands = self.available_commands()
        if command_requested in available_commands:
            return available_commands[command_requested]
        else:
            attrs = [
                {
                    'field': 'command_id',
                    'value': command_requested,
                    'limiter': .96,
                },
                {
                    'field': 'label',
                    'value': command_requested,
                    'limiter': .89,
                },
                {
                    'field': 'machine_label',
                    'value': command_requested,
                    'limiter': .89,
                }
            ]
            try:
                logger.debug("Get is about to call search...: %s" % command_requested)
                found, key, item, ratio, others = do_search_instance(attrs, available_commands,
                                                                     self._DevicesLibrary._Commands.command_search_attributes,
                                                                     limiter=.89,
                                                                     operation="highest")
                logger.debug("found command by search: {command_id}", command_id=key)
                if found:
                    return True
                else:
                    return False
            except YomboWarning, e:
                return False
                # raise KeyError('Searched for %s, but had problems: %s' % (command_requested, e))


    # def update(self, record):
    #
    #     # check if device_type_id changes.
    #     if 'device_type_id' in record:
    #         if record['device_type_id'] != self.device_type_id:
    #             self.device_type_id = record['device_type_id']
    #
    #     # global_invoke_all('_devices_update_', **{'id': record['id']})  # call hook "device_update" when adding a new device.

    def delete(self):
        """
        Called when the device should delete itself.
        
        :return: 
        """
        # print("deleting device.....")
        self._DevicesLibrary._LocalDB.set_device_status(self.device_id, 2)
        global_invoke_all('_device_deleted_', **{'device': self})  # call hook "devices_delete" when deleting a device.
        self.status = 2

    def enable(self):
        """
        Called when the device should delete itself.

        :return:
        """
        self._DevicesLibrary._LocalDB.set_device_status(self.device_id, 1)
        global_invoke_all('_device_enabled_', **{'device': self})  # call hook "devices_delete" when deleting a device.
        self.status = 1

    def disable(self):
        """
        Called when the device should delete itself.

        :return:
        """
        self._DevicesLibrary._LocalDB.set_device_status(self.device_id, 0)
        global_invoke_all('_device_disabled_', **{'device': self})  # call hook "devices_delete" when deleting a device.
        self.status = 0

class Device_Request:
    """
    A class that manages requests for a given device. This class is instantiated by the
    device class. Librarys and modules can use this instance to get the details of a given
    request.
    """
    def __init__(self, request, device):
        """
        Get the instance setup.
        
        :param request: Basic details about the request to get started.
        :param Device: A pointer to the device instance.
        """
        self.device = device
        self.request_id = request['request_id']
        self.sent_time = request['sent_time']
        self.command = request['command']
        self.history = request['history']
        self.requested_by = request['requested_by']
        self.status = None
        self.sent_time = None
        self.received_time = None
        self.pending_time = None
        self.finished_time = None
        self.message = None
        self.set_status('new')

    def set_sent_time(self, sent_time=None):
        if sent_time is None:
            sent_time = time()
        self.sent_time = sent_time
        self.status = 'sent'
        self.history.append((sent_time, 'sent'))

    def set_received_time(self, finished_time=None):
        if finished_time is None:
            finished_time = time()
        self.finished_time = finished_time
        self.status = 'failed'
        self.history.append((finished_time, 'failed'))

    def set_pending_time(self, pending_time=None):
        if pending_time is None:
            pending_time = time()
        self.pending_time = pending_time
        self.status = 'pending'
        self.history.append((pending_time, 'pending'))

    def set_finished_time(self, finished_time=None):
        if finished_time is None:
            finished_time = time()
        self.finished_time = finished_time
        self.status = 'done'
        self.history.append((finished_time, 'done'))

    def set_failed_time(self, finished_time=None):
        if finished_time is None:
            finished_time = time()
        self.finished_time = finished_time
        self.status = 'failed'
        self.history.append((finished_time, 'failed'))

    def set_status(self, status):
        self.status = status
        self.history.append((time(), status))

    def set_message(self, message):
        self.message = message
        self.history.append((time(), message))
