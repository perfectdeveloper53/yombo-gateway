# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * End user documentation: `Devices @ User Documentation <https://yombo.net/docs/gateway/web_interface/devices>`_
  * For library documentation, see: `Devices @ Library Documentation <https://yombo.net/docs/libraries/devices>`_

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

**Usage**:

.. code-block:: python

   # Three ways to send a command to a device. Going from easiest method, but less assurance of correct command
   # to most assurance.

   # Lets turn on every device this module manages.
   for device in self._Devices:
       self.Devices[device].command(cmd="off")

   # Lets turn off every every device, using a very specific command id.
   for device in self._Devices:
       self.Devices[device].command(cmd="js83j9s913")  # Made up id, but can be same as off

   # Turn off the christmas tree.
   self._Devices.command("christmas tree", "off")

   # Get devices by device type:
   deviceList = self._Devices.search(device_type="x10_appliance")  # Can search on any device attribute

   # Turn on all x10 lights off (regardless of house / unit code)
   allX10Lamps = self._DeviceTypes.devices_by_device_type("x10_light")
   # Turn off all x10 lamps
   for lamp in allX10Lamps:
       lamp.command("off")

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2017 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/devices.html>`_
"""
# Import python libraries
from copy import deepcopy
import json
import msgpack
from numbers import Number
import sys
import traceback

from time import time

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred

# Import Yombo libraries
from yombo.constants import ENERGY_NONE, ENERGY_ELECTRIC, ENERGY_GAS, ENERGY_WATER, ENERGY_NOISE, ENERGY_TYPES
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.core.library import YomboLibrary
from yombo.mixins.library_db_model_mixin import LibraryDBModelMixin
from yombo.mixins.library_search_mixin import LibrarySearchMixin
from yombo.core.log import get_logger
from yombo.utils import generate_source_string
from yombo.utils.hookinvoke import global_invoke_all


from ._device import Device

logger = get_logger("library.devices")


class Devices(YomboLibrary, LibraryDBModelMixin, LibrarySearchMixin):
    """
    Manages all devices and provides the primary interaction interface. The
    primary functions developers should use are:

    * :py:meth:`__getitem__ <Devices.__getitem__>` - Get a pointer to a device, using self._Devices as a dictionary of objects.
    * :py:meth:`command <Devices.command>` - Send a command to a device.
    * :py:meth:`search <Devices.search>` - Get a pointer to a device, using device_id or device label.
    """
    devices = {}

    # The following are used by get(), get_advanced(), search(), and search_advanced()
    _class_storage_load_hook_prefix = "device"
    _class_storage_load_db_class = Device
    _class_storage_attribute_name = "devices"
    _class_storage_search_fields = [
        "device_id", "device_type_id", "machine_label", "label", "area_label_lower", "full_label_lower",
        "area_label", "full_label", "description"
    ]
    _class_storage_sort_key = "machine_label"

    @inlineCallbacks
    def _init_(self, **kwargs):
        """
        Sets up basic attributes.
        """
        self.mqtt = None
        self.all_energy_usage = yield self._SQLDict.get(self, "all_energy_usage")
        self.all_energy_usage_calllater = None

        # reactor.callLater(10, self.test_change_device)

    def test_change_device(self):
        print("test change device starting.")
        # print(f"sync enabled: {self._sync_enabled}")
        # device_id = random.choice(list(self.devices))
        print(list(self.devices.keys()))
        device = self.devices['aWpBzyrK0WQUZwgdvmZ4']
        print(f"changing device label: {device.label}")
        device.label = f"{device.label}2"
        print(f"changing device new device label: {device.label}")

    @inlineCallbacks
    def _start_(self, **kwags):
        """
        Loads the devices from the database and loads device commands.

        :param kwags:
        :return:
        """
        yield self._class_storage_load_from_database()

    def _started_(self, **kwargs):
        """
        Sets up the looping call to cleanup device commands. Also, subscribes to
        MQTT topics for IoT interactions.

        :return: 
        """
        if self._Loader.operating_mode == "run":
            self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming,
                                       client_id=f"Yombo-devices-{self.gateway_id}")
            self.mqtt.subscribe("yombo/devices/+/get")

    def _device_state_(self, **kwargs):
        """
        Sets up the callLater to calculate total energy usage.
        Called by send_state when a devices status changes.

        :param kwargs:
        :return:
        """
        if self.all_energy_usage_calllater is not None and self.all_energy_usage_calllater.active():
            return

        self.all_energy_usage_calllater = reactor.callLater(1, self.calculate_energy_usage)

    def calculate_energy_usage(self):
        """
        Iterates thru all the devices and adds up the energy usage across all devices.

        This function is called after a 1 second delay by _device_state_ hook.

        :return:
        """
        usage_types = {
            ENERGY_ELECTRIC: 0,
            ENERGY_GAS: 0,
            ENERGY_WATER: 0,
            ENERGY_NOISE: 0,
        }
        all_energy_usage = {
            "total": deepcopy(usage_types),
        }

        for device_id, device in self.devices.items():
            state_all = device.state_all
            if "_fake_data" in state_all and state_all["_fake_data"] is True:
                continue
            if state_all["energy_type"] not in ENERGY_TYPES or state_all["energy_type"] == "none":
                continue
            energy_usage = state_all["energy_usage"]
            if isinstance(energy_usage, int) or isinstance(energy_usage, float):
                usage = energy_usage
            elif isinstance(energy_usage, Number):
                usage = float(energy_usage)
            else:
                continue
            location_id = self._Locations.get(device.location_id)
            location_label = location_id.machine_label
            if location_label not in all_energy_usage:
                all_energy_usage[location_label] = deepcopy(usage_types)
            all_energy_usage[location_label][state_all["energy_type"]] += usage
            all_energy_usage["total"][state_all["energy_type"]] += usage

        logger.debug("All energy usage: {all_energy_usage}", all_energy_usage=all_energy_usage)

        for location_label, data in all_energy_usage.items():
            if location_label in self.all_energy_usage:
                if ENERGY_ELECTRIC in self.all_energy_usage[location_label] and \
                        all_energy_usage[location_label][ENERGY_ELECTRIC] != \
                        self.all_energy_usage[location_label][ENERGY_ELECTRIC]:
                    # print("EU: setting eletrcic: %s %s" % (location_label, all_energy_usage[location][ENERGY_ELECTRIC]))
                    self._Statistics.datapoint(
                        f"energy.{location_label}.electric",
                        round(all_energy_usage[location_label][ENERGY_ELECTRIC])
                    )
                if ENERGY_GAS in self.all_energy_usage[location_label] and \
                        all_energy_usage[location_label][ENERGY_GAS] != self.all_energy_usage[location_label][ENERGY_GAS]:
                        self._Statistics.datapoint(
                            f"energy.{location_label}.gas",
                            round(all_energy_usage[location_label][ENERGY_GAS], 3)
                        )
                if ENERGY_WATER in self.all_energy_usage[location_label] and \
                        all_energy_usage[location_label][ENERGY_WATER] != self.all_energy_usage[location_label][ENERGY_WATER]:
                        self._Statistics.datapoint(
                            f"energy.{location_label}.water",
                            round(all_energy_usage[location_label][ENERGY_WATER], 3)
                        )
                if ENERGY_NOISE in self.all_energy_usage[location_label] and \
                        all_energy_usage[location_label][ENERGY_NOISE] != self.all_energy_usage[location_label][ENERGY_NOISE]:
                        self._Statistics.datapoint(
                            f"energy.{location_label}.noise",
                            round(all_energy_usage[location_label][ENERGY_NOISE], 1)
                        )
            else:
                self._Statistics.datapoint(
                    f"energy.{location_label}.electric",
                    round(all_energy_usage[location_label][ENERGY_ELECTRIC])
                )
                self._Statistics.datapoint(
                    f"energy.{location_label}.gas",
                    round(all_energy_usage[location_label][ENERGY_GAS], 3)
                )
                self._Statistics.datapoint(
                    f"energy.{location_label}.water",
                    round(all_energy_usage[location_label][ENERGY_WATER], 3)
                )
                self._Statistics.datapoint(
                    f"energy.{location_label}.noise",
                    round(all_energy_usage[location_label][ENERGY_NOISE], 1)
                )
        self.all_energy_usage = deepcopy(all_energy_usage)

    def _class_storage_preprocess_load(self, item, **kwargs):
        new_map = {}
        for key, value in item["energy_map"].items():
            new_map[float(key)] = float(value)
        item["energy_map"] = new_map

    @inlineCallbacks
    def _class_storage_load_db_items_to_memory(self, incoming, source=None, **kwargs):
        device_id = incoming["id"]
        if device_id not in self.devices:
            device_type = self._DeviceTypes[incoming["device_type_id"]]

            if device_type.platform is None or device_type.platform == "":
                device_type.platform = "device"
            class_names = device_type.platform.lower()

            class_names = "".join(class_names.split())  # we don't like spaces
            class_names = class_names.split(",")

            # logger.info("Loading device ({device}), platforms: {platforms}",
            #             device=device,
            #             platforms=class_names)

            klass = None
            for class_name in class_names:
                if class_name in self._DeviceTypes.platforms:
                    klass = self._DeviceTypes.platforms[class_name]
                    break

            if klass is None:
                klass = self._DeviceTypes.platforms["device"]
                logger.warn(
                    "Using base device class for device '{label}' cannot find any of these requested classes:"
                    " {class_names}",
                    label=incoming["label"],
                    class_names=class_names)

            device = yield maybeDeferred(self._generic_class_storage_load_to_memory,
                                         self.devices,
                                         Device,
                                         incoming,
                                         source=source
                                         )

            d = Deferred()
            d.addCallback(lambda ignored: maybeDeferred(self.devices[device_id]._system_init_, incoming, source=source))
            d.addErrback(self._load_node_into_memory_failure, self.devices[device_id])
            d.addCallback(lambda ignored: maybeDeferred(self.devices[device_id]._init_))
            d.addErrback(self._load_node_into_memory_failure, self.devices[device_id])
            d.addCallback(lambda ignored: maybeDeferred(self.devices[device_id]._load_))
            d.addErrback(self._load_node_into_memory_failure, self.devices[device_id])
            d.addCallback(lambda ignored: maybeDeferred(self.devices[device_id]._start_))
            d.addErrback(self._load_node_into_memory_failure, self.devices[device_id])
            d.callback(1)
            yield d
            try:
                global_invoke_all("_device_imported_",
                                  called_by=self,
                                  id=device_id,
                                  device=self.devices[device_id],
                                  )
            except YomboHookStopProcessing as e:
                pass
        else:
            device = yield maybeDeferred(self._generic_class_storage_load_to_memory,
                                         self.devices,
                                         Device,
                                         incoming,
                                         source=source
                                         )
        return device

    def _load_node_into_memory_failure(self, failure, device):
        logger.error("Got failure while creating device instance for '{label}': {failure}", failure=failure,
                     label=device['label'])

    @inlineCallbacks
    def create_child_device(self, existing, label, machine_label, device_type, description=None):
        # create a child device based on a provided device.
        if description is None:
            description = f"Child of: {existing.full_label}"
        new_data = existing.asdict_short()
        device_type_found = self._DeviceTypes.get(device_type)
        new_data.update({
            "device_id": f"{existing.device_id}{machine_label}",
            "id": f"{existing.device_id}{machine_label}",
            "label": f"{existing.label} - {label}",
            "machine_label": f"{existing.machine_label}_{machine_label}",
            "description": description,
            "device_type_id": f"{device_type_found.device_type_id}",
            "statistic_label": f"{existing.statistic_label}.{machine_label}",
            "created_at": time(),
            "updated_at": time(),
            "_fake_data": True,
        })
        new_device = yield self._load_node_into_memory(new_data, source="child")
        new_device.parent = existing
        new_device.parent_id = existing.device_id
        return new_device

    def command(self, device, cmd, **kwargs):
        """
        Tells the device to do a command. This in turn calls the hook _device_command_ so modules can process the
        command if they are supposed to.

        If a pin is required, "pin" must be included as one of the arguments. All kwargs are sent with the
        hook call.

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
        :param delay: How many seconds to delay sending the command. Not to be combined with "not_before"
        :type delay: int or float
        :param not_before: An epoch time when the command should be sent. Not to be combined with "delay".
        :type not_before: int or float
        :param max_delay: How many second after the "delay" or "not_before" can the command be send. This can occur
            if the system was stopped when the command was supposed to be send.
        :type max_delay: int or float
        :param inputs: A list of dictionaries containing the "input_type_id" and any supplied "value".
        :type input: list of dictionaries
        :param kwargs: Any additional named arguments will be sent to the module for processing.
        :type kwargs: named arguments
        :return: The request id.
        :rtype: str
        """
        kwargs["requesting_source"] = generate_source_string()
        return self.get(device).command(cmd, **kwargs)

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
        parts = topic.split("/", 10)
        logger.info("Yombo Devices got this: {topic} : {parts}", topic=topic, parts=parts)
        payload = payload.strip()
        content_type = "string"
        try:
            payload = json.loads(payload)
            content_type = "json"
        except Exception as e:
            try:
                payload = msgpack.loads(payload)
                content_type = "msgpack"
            except Exception as e:
                pass

        try:
            device_label = self.get(parts[2].replace("_", " "))
            device = self.get(device_label)
        except KeyError as e:
            logger.info("Received MQTT request for a device that doesn't exist: {part}", part=parts[2])
            return

        if parts[3] == "get":
            status = device.state_all

            if len(parts) == 5:
                if payload == "all":
                    self.mqtt.publish(f"yombo/devices/{device.machine_label}/status",
                                      json.dumps(device.state_all))
                elif payload in status:
                    self.mqtt.publish(f"yombo/devices/{device.machine_label}/status/{payload}",
                                      str(getattr(payload, status)))
            else:
                self.mqtt.publish(f"yombo/devices/{device.machine_label}/status",
                                  json.dumps(device.state_all))

        elif parts[3] == "cmd":
            try:
                device.command(cmd=parts[4])
            except Exception as e:
                logger.warn("Device received invalid command request for command: {command} Reason: {reason}",
                            command=parts[4], reason=e)

            if len(parts) == 6:
                status = device.state_all
                if parts[4] == "all":
                    self.mqtt.publish(f"yombo/devices/{device.machine_label}/status",
                                      json.dumps(device.state_all))
                elif payload in status:
                    self.mqtt.publish(f"yombo/devices/{device.machine_label}/status/{payload}",
                                      getattr(payload, status))
            else:
                self.mqtt.publish(f"yombo/devices/{device.machine_label}/status",
                                  json.dumps(device.state_all))

    def device_user_access(self, device_id, access_type=None):
        """
        Gets all users that have access to this device.

        :param access_type: If set to "direct", then gets list of users that are specifically added to this device.
            if set to "roles", returns access based on role membership.
        :return:
        """
        device = self.get(device_id)
        return device.device_user_access(access_type)

    def list_devices(self, field=None):
        """
        Return a list of devices, returning the value specified in field.
        
        :param field: A string referencing an attribute of a device.
        :type field: string
        :return: 
        """
        if field is None:
            field = "machine_label"

        if field not in self.device_search_attributes:
            raise YomboWarning(f"Invalid field for device attribute: {field}")

        devices = []
        for device_id, device in self.devices.items():
            devices.append(getattr(device, field))
        return devices

    def full_list_devices(self, gateway_id=None):
        """
        Return a list of dictionaries representing all known devices. Can be restricted to
        a single gateway by supplying a gateway_id, use "local" for the local gateway.

        :param gateway_id: Filter selecting to a specific gateway. Use "local" for the local gateway.
        :type gateway_id: string
        :return:
        """
        if gateway_id == "local":
            gateway_id = self.gateway_id

        devices = []
        for device_id, device in self.devices.items():
            if gateway_id is None or device.gateway_id == gateway_id:
                devices.append(device.asdict())
        return devices

    @inlineCallbacks
    def add_device(self, api_data, source=None, **kwargs):
        """
        Add a new device. This will also make an API request to add device at the server too.

        :param data:
        :param kwargs:
        :return:
        """
        results = None
        # logger.info("Add new device.  Data: {data}", data=data)
        if "gateway_id" not in api_data:
            api_data["gateway_id"] = self.gateway_id

        try:
            for key, value in api_data.items():
                if value == "":
                    api_data[key] = None
                elif key in ["statistic_lifetime", "pin_timeout"]:
                    if api_data[key] is None or (isinstance(value, str) and value.lower() == "none"):
                        del api_data[key]
                    else:
                        api_data[key] = int(value)
        except Exception as e:
            return {
                "status": "failed",
                "msg": "Couldn't add device due to value mismatches.",
                "apimsg": e,
                "apimsghtml": e,
                "device_id": None,
                "data": None,
            }

        try:
            global_invoke_all("_device_before_add_",
                              called_by=self,
                              data=api_data,
                              stoponerror=True,
                              )
        except YomboHookStopProcessing as e:
            raise YomboWarning(f"Adding device was halted by '{e.name}', reason: {e.message}")

        if source != "amqp":
            logger.debug("POSTING device. api data: {api_data}", api_data=api_data)
            try:
                if "session" in kwargs:
                    session = kwargs["session"]
                else:
                    session = None

                if "variable_data" in api_data and len(api_data["variable_data"]) > 0:
                    variable_data = api_data["variable_data"]
                    del api_data["variable_data"]
                else:
                    variable_data = None

                device_results = yield self._YomboAPI.request("POST", "/v1/device",
                                                              api_data,
                                                              session=session)
            except YomboWarning as e:
                return {
                    "status": "failed",
                    f"msg": "Couldn't add device: {e.message}",
                    f"apimsg": f"Couldn't add device: {e.message}",
                    f"apimsghtml": f"Couldn't add device: {e.html_message}",
                }
            logger.info("add new device results: {device_results}", device_results=device_results)
            if variable_data is not None:
                variable_results = yield self.set_device_variables(device_results["data"]["id"],
                                                                   variable_data,
                                                                   "add",
                                                                   source,
                                                                   session=session)
                if variable_results["code"] > 299:
                    results = {
                        "status": "failed",
                        "msg": f"Device saved, but had problems with saving variables: {variable_results['msg']}",
                        "apimsg": variable_results["apimsg"],
                        "apimsghtml": variable_results["apimsghtml"],
                        "device_id": device_results["data"]["id"],
                        "data": device_results["data"],
                    }

            device_id = device_results["data"]["id"]
            new_device = device_results["data"]
            new_device["created"] = new_device["created_at"]
            new_device["updated"] = new_device["updated_at"]
        else:
            device_id = api_data["id"]
            new_device = api_data

        logger.debug("device add results: {device_results}", device_results=device_results)

        new_device = yield self._load_node_into_memory(new_device, source)

        try:
            yield global_invoke_all("_device_added_",
                                    called_by=self,
                                    id=device_id,
                                    device=self.devices[device_id],
                                    )
        except Exception:
            pass

        if results is None:
            return {
                "status": "success",
                "msg": "Device added",
                "apimsg":  "Device added",
                "apimsghtml":  "Device added",
                "device_id": device_id,
                "data": new_device,
            }
