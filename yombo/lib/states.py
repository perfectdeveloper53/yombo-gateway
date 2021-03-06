# This file was created by Yombo for use with Yombo Python gateway automation
# software.  Details can be found at https://yombo.net
"""

.. note::

  * End user documentation: `States @ User Documentation <https://yombo.net/docs/gateway/web_interface/states>`_
  * For developer documentation, see: `States @ Module Development <https://yombo.net/docs/libraries/states>`_

.. seealso::

   * The :doc:`Atoms library </lib/atoms>` is used to store static data about the environment.
   * The :doc:`MQTT library </lib/mqtt>` is used to allow IoT devices to interact with states.
   
The states library is used to collect and provide information about various states that the automation system
can be in or exist around it. For example, it can tell if it's light outside, dawn, dusk, or if it's connected
to the Yombo server. It can provide a list of users connected and what module they are connected through.

Example states: times_dark, weather_raining, alarm_armed, yombo_service_connection

*Usage**:

.. code-block:: python

   try:
     raining = self._States["weather.raining"]
   except:
     raining = None

   if raining is not True:
       # turn on sprinklers

   try:
     jeffIsHome = self._States["is.people.jeff.home"]
   except:
     jeffIsHome = None

   if jeffIsHome == "home":
       # turn on HVAC
   elif jeffIsHome is not None:
       # turn off HVAC
   else:
       # we don't know if Jeff is home or not, leave HVAC alone

   try:
     self._States["weather_is_cloudy"] = True
   except:
     pass  # unable to set state?


.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/states.html>`_
"""
# Import python libraries
from collections import OrderedDict, deque
from copy import deepcopy
import json
from time import time
from functools import partial

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred
from twisted.internet.task import LoopingCall

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning, YomboHookStopProcessing
from yombo.core.log import get_logger
from yombo.core.library import YomboLibrary
from yombo.utils import (pattern_search, is_true_false, random_string, random_int, memory_usage,
                         get_yombo_instance_type)
from yombo.utils.datatypes import coerce_value
from yombo.utils.converters import epoch_to_string
from yombo.utils.hookinvoke import global_invoke_all

logger = get_logger("library.states")


class States(YomboLibrary):
    """
    Provides a base API to store common states among libraries and modules.
    """
    MAX_HISTORY = 100
    gateway_id = "local"
    states = {}


    def __contains__(self, state_requested):
        """
        Checks to if a provided state exists.

            >>> if "is.light" in self._States:

        :raises YomboWarning: Raised when request is malformed.
        :param state_requested: The state key to search for.
        :type state_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(state_requested)
            return True
        except Exception as e:
            return False

    def __getitem__(self, state_requested):
        """
        Attempts to find the state requested.

            >>> state_value = self._States["is.light"]  #by id

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param state_requested: The state key to search for.
        :type state_requested: string
        :return: The value assigned to the state.
        :rtype: mixed
        """
        return self.get(state_requested)

    def __setitem__(self, state_requested, value):
        """
        Sets a state.
        
        .. note:: If this is a new state, or you wish to set a human filter for the value, use
           :py:meth:`set <States.set>` method.

            >>> self._States["module.local.name.hi"] = "some value"

        :raises YomboWarning: Raised when request is malformed.
        :param state_requested: The state key to replace the value for.
        :type state_requested: string
        :param value: New value to set.
        :type value: mixed
        """
        return self.set(state_requested, value)

    def __delitem__(self, state_requested):
        """
        Attempts to delete the state.

            >>> del self._States["module.local.name.hi"]

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param state_requested: The state key to search for.
        :type state_requested: string
        :return: The value assigned to the state.
        :rtype: mixed
        """
        return self.delete(state_requested)

    def __iter__(self):
        """ iter states. """
        return self.states[self.gateway_id].__iter__()

    def __len__(self):
        """
        Returns an int of the number of states defined.

        :return: The number of states defined.
        :rtype: int
        """
        return len(self.states[self.gateway_id])


    def keys(self, gateway_id=None):
        """
        Returns the keys of the states that are defined.

        :return: A list of states defined. 
        :rtype: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if gateway_id not in self.states:
            return []
        return list(self.states[gateway_id].keys())

    def items(self, gateway_id=None):
        """
        Gets a list of tuples representing the states defined.

        :return: A list of tuples.
        :rtype: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if gateway_id not in self.states:
            return []
        return list(self.states[gateway_id].items())

    def values(self, gateway_id=None):
        """
        Gets a list of state values
        :return: list
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if gateway_id not in self.states:
            return []
        return list(self.states[gateway_id].values())

    @inlineCallbacks
    def _init_(self, **kwargs):
        self.library_phase = 1
        self.gateway_id = self._Configs.get("core", "gwid", "local", False)
        self.states = {self.gateway_id: {}}
        self.db_save_states_data = deque()
        self.db_save_states_loop = LoopingCall(self.db_save_states)
        self.db_save_states_loop.start(random_int(30, .10), False)
        yield self.load_states()

        # setup cluster state defaults if not set
        try:
            self.get("is.away", gateway_id="cluster")
        except KeyError:
            self.set("is.away", False, gateway_id="cluster")


    def _load_(self, **kwargs):
        self.library_phase = 2

    def _start_(self, **kwargs):
        self.module_phase = 3
        if self._Loader.operating_mode == "run":
            self.mqtt = self._MQTT.new(mqtt_incoming_callback=self.mqtt_incoming,
                                       client_id=f"Yombo-states-{self.gateway_id}")
            self.mqtt.subscribe("yombo/states/+/get")
            self.mqtt.subscribe("yombo/states/+/get/+")
            self.mqtt.subscribe("yombo/states/+/set")
            self.mqtt.subscribe("yombo/states/+/set/+")

    def _started_(self, **kwargs):
        self.library_phase = 4
        self.memory_usage_checker_loop = LoopingCall(self.memory_usage_checker)
        self.memory_usage_checker_loop.start(random_int(600, .10))

    @inlineCallbacks
    def _unload_(self, **kwargs):
        yield self.db_save_states()

    @inlineCallbacks
    def load_states(self):
        states = yield self._LocalDB.get_states()
        for state in states:
            if state["gateway_id"] not in self.states:
                self.states[state["gateway_id"]] = {}
            if state["name"] not in self.states[state["gateway_id"]]:
                self.states[state["gateway_id"]][state["name"]] = {
                    "gateway_id": state["gateway_id"],
                    "value": coerce_value(state["value"], state["value_type"]),
                    "value_human": self.convert_to_human(state["value"], state["value_type"]),
                    "value_type": state["value_type"],
                    "live": state["live"],
                    "created_at": state["created_at"],
                }

    @inlineCallbacks
    def memory_usage_checker(self):
        usage = yield memory_usage()
        self.set("yombo.memory_usage", usage)

    # def __repr__(self):
    #     states = {}
    #     for key, state in self.states.iteritems():
    #         if state["readKey"] is not None:
    #             state["readKey"] = True
    #         if state["writeKey"] is not None:
    #             state["writeKey"] = True
    #         states[key] = state
    #     return states

    def exists(self, key, gateway_id):
        """
        Checks if a given state exists. Returns true or false.

        :param key: Name of state to check.
        :return: If state exists:
        :rtype: Bool
        """
        if gateway_id is None:
            gateway_id = self.gateway_id

        if key in self.states[gateway_id]:
            return True
        return False

    def get_last_update(self, key, gateway_id=None):
        """
        Get the time() the key was created or last updated.

        :param key: Name of state to check.
        :return: Time() of last update
        :rtype: float
        """
        if gateway_id is None:
            gateway_id = self.gateway_id
        if key in self.states[gateway_id]:
            return self.states[gateway_id][key]["created_at"]
        else:
            raise KeyError(f"Cannot get state time: {key} not found")

    def get2(self, key, human=None, full=None, gateway_id=None, set=None, **kwargs):
        """
        Like :py:meth:`get() <get>` below, however, this returns a callable to retrieve the value instead of an actual
        value. The callable can also be used to set the value of the state too. See
        example for usage details.

        **Usage**:

        .. code-block:: python

           some_state = self._States.get2("some_state")
           logger.info("The state or some_state is: {state}", state=some_state()
           # set a new state value for "some_state".
           some_state(set="New label")

        .. versionadded:: 0.13.0

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param key: Name of state to get.
        :type key: string
        :param human: If true, returns a state for human consumption.
        :type human: bool
        :param full: If true, Returns all data about the state. If false, just the value.
        :type full: bool
        :return: Value of state
        """

        if set is not None:
            self.set(key, set, gateway_id=gateway_id, **kwargs)
            return set

        self.get(key, human, full, gateway_id=gateway_id)

        return partial(self.get, key, human, full, gateway_id=gateway_id)

    def get(self, key, human=None, full=None, gateway_id=None, default='eEryLOZESKJf7cqQZv2bFlh04Hrf3NxLazV5KEuvyXFtkgxpq70vWsIz9xwr'):
        """
        Get the value of a given state (key).

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param key: Name of state to get.
        :type key: string
        :param human: If true, returns a state for human consumption.
        :type human: bool
        :param full: If true, Returns all data about the state. If false, just the value.
        :type full: bool
        :param gateway_id: The gateway id to lookup. If 'self', will be converted to local gateway ID.
        :param default: If set, will return a this value if it's not set. Otherwise, will raise KeyError if not set.
        :type default: str
        :return: Value of state
        """
        # logger.debug("states:get: {key} = {value}", key=key)
        if gateway_id is None or gateway_id.lower() == 'self':
            gateway_id = self.gateway_id

        if self._Loader.operating_mode != "run":
            gateway_id = "local"

        self._Statistics.increment("lib.states.get", bucket_size=15, anon=True)
        search_chars = ["#", "+"]
        if any(s in key for s in search_chars):
            if gateway_id not in self.states:
                return {}
            results = pattern_search(key, self.states[gateway_id])
            if len(results) > 1:
                values = {}
                for item in results:
                    if human is True:
                        values[item] = self.states[gateway_id][item]["value_human"]
                    elif full is True:
                        values[item] = self.states[gateway_id][item]
                    else:
                        values[item] = self.states[gateway_id][item]["value"]
                return values
            else:
                raise KeyError("Searched for atoms, none found.")

        # print(f"States get...... gateway_id: {gateway_id}")
        # print(f"States key: {key}")
        # print(self.states)
        if human is True:
            return self.states[gateway_id][key]["value_human"]
        elif full is True:
            return self.states[gateway_id][key]
        else:
            return self.states[gateway_id][key]["value"]

    def get_copy(self, gateway_id=None):
        """
        Returns a copy of the active states.

        :param key: Name of state to check.
        :return: Value of state
        """
        if gateway_id is None:
            return self.states.copy()
        if gateway_id is None:
            gateway_id = self.gateway_id
        if gateway_id in self.states:
            return self.states[gateway_id].copy()
        else:
            return {}

    def get_list(self, gateway_id=None):
        """
        Gets States as a list.

        :return:
        """
        results = []
        for found_gateway_id, states in self.states.items():
            if gateway_id is not None and found_gateway_id == gateway_id:
                continue
            for name, value in states.items():
                state = value.copy()
                state["id"] = name
                results.append(state)
        return results

    @inlineCallbacks
    def set(self, key, value, value_type=None, callback=None, arguments=None, gateway_id=None, source=None):
        """
        Set the value of a given state (key).

        **Hooks called**:

        * _states_set_ : Sends kwargs: *key* - The name of the state being set. *value* - The new value to set.

        :param key: Name of state to set.
        :param value: Value to set state to. Can be string, list, or dictionary.
        :param value_type: If set, allows a human filter to be applied for proper display.
        :param callback: If this a living state, provide a callback to be called to get value. Value will be used
          to set the initial value.
        :param arguments: kwarg (arguments) to send to callback.
        :param gateway_id: Gateway ID this state belongs to, defaults to local gateway.
        :type gateway_id: string
        :param source: Reference to the library or module settings this atom.
        :type source: object
        :return: Value of state
        """
        # logger.debug("Saving state: {key} = {value}", key=key, value=value)
        if gateway_id is None:
            gateway_id = self.gateway_id

        if self._Loader.operating_mode != "run":
            gateway_id = "local"

        search_chars = ["#", "+"]
        if any(s in key for s in search_chars):
            raise YomboWarning("state keys cannot have # or + in them, reserved for searching.")

        if gateway_id not in self.states:
            self.states[gateway_id] = {}

        source_type, source_label = get_yombo_instance_type(source)

        if self._Loader.run_phase[1] >= 6000:
                try:
                    yield global_invoke_all("_states_preset_",
                                            called_by=self,
                                            key=key,
                                            value=value,
                                            value_type=value_type,
                                            gateway_id=gateway_id,
                                            stoponerror=True,
                                            source=source,
                                            source_label=source_label,
                                            )
                except YomboHookStopProcessing as e:
                    logger.warn("Not saving state '{state}'. Resource '{resource}' raised' YomboHookStopProcessing exception.",
                                 state=key, resource=e.by_who)
                    return None

        if key in self.states[gateway_id]:
            is_new = False
            if self.states[gateway_id][key]["value"] == value:
                return
            if hasattr(self, "_Statistics"):
                self._Statistics.increment("lib.states.set.update", bucket_size=60, anon=True)
        else:
            # logger.debug("Saving state: {key} = {value}", key=key, value=value)
            is_new = True
            self.states[gateway_id][key] = {
                "gateway_id": gateway_id,
                "live": False,
            }
            if hasattr(self, "_Statistics"):
                self._Statistics.increment("lib.states.set.new", bucket_size=60, anon=True)

        self.states[gateway_id][key]["source"] = source_label
        self.states[gateway_id][key]["value"] = value
        self.states[gateway_id][key]["created_at"] = int(time())
        self.states[gateway_id][key]["callback"] = callback
        self.states[gateway_id][key]["arguments"] = arguments
        if value_type is None:
            value_type_fixed = "str"
        elif value_type.lower() in ("bool", "boolean"):
            value_type_fixed = "bool"
        elif value_type.lower() in ("str", "string"):
            value_type_fixed = "str"
        elif value_type.lower() in ("int", "integer"):
            value_type_fixed = "int"
        elif value_type.lower() in ("float", "decimal"):
            value_type_fixed = "float"
        else:
            value_type_fixed = value_type
        if is_new is True or value_type_fixed is not None:
            self.states[gateway_id][key]["value_type"] = value_type_fixed
        if is_new is True or callback is not None:
            if callback is None:
                self.states[gateway_id][key]["live"] = False
            else:
                self.states[gateway_id][key]["live"] = True

        self.states[gateway_id][key]["value_human"] = self.convert_to_human(value, value_type)

        if hasattr(self, '_Automation') is False:
            return
        self._Automation.trigger_monitor("state",
                                         key=key,
                                         value=value,
                                         value_type=value_type_fixed,
                                         value_full=self.states[gateway_id][key],
                                         action="set",
                                         gateway_id=gateway_id,
                                         source=source,
                                         source_label=source_label,
                                         )
        # Call any hooks
        if self._Loader.run_phase[1] >= 6000:
            yield global_invoke_all("_states_set_",
                                    called_by=self,
                                    key=key,
                                    value=value,
                                    value_type=value_type,
                                    value_full=self.states[gateway_id][key],
                                    gateway_id=gateway_id,
                                    source=source,
                                    source_label=source_label,
                                    )

        if (gateway_id == self.gateway_id or gateway_id == "cluster") and gateway_id != "local":
            self.db_save_states_data.append([key, deepcopy(self.states[gateway_id][key])])

    @inlineCallbacks
    def db_save_states(self):
        """
        Called periodically and on exit to save states to database.

        :return:
        """
        to_save = deque()

        while True:
            try:
                key, data = self.db_save_states_data.popleft()
                if data["live"] is True:
                    live = 1
                else:
                    live = 0

                od = OrderedDict()
                od["gateway_id"] = data["gateway_id"]
                od["name"] = key
                od["value"] = data["value"]
                od["value_type"] = data["value_type"]
                od["live"] = live
                od["created_at"] = data["created_at"]
                to_save.append(od)
            except IndexError:
                break
        if len(to_save) > 0:
            yield self._LocalDB.save_state_bulk(to_save)

    @inlineCallbacks
    def set_from_gateway_communications(self, key, data, source):
        """
        Used by the gateway coms (mqtt) system to set state values.
        :param key:
        :param data:
        :return:
        """
        gateway_id = data["gateway_id"]
        if gateway_id == self.gateway_id:
            return
        if gateway_id not in self.states:
            self.states[gateway_id] = {}
        source_type, source_label = get_yombo_instance_type(source)

        self.states[data["gateway_id"]][key] = {
            "gateway_id": data["gateway_id"],
            "value": data["value"],
            "value_human": data["value_human"],
            "value_type": data["value_type"],
            "live": False,
            "source": source_label,
            "created_at": data["created_at"],
        }

        self._Automation.trigger_monitor("state",
                                         key=key,
                                         value=data["value"],
                                         value_type=data["value_type"],
                                         value_full=self.states[gateway_id][key],
                                         action="set",
                                         gateway_id=gateway_id,
                                         source=source,
                                         source_label=source_label,
                                         )

        # Call any hooks
        yield global_invoke_all("_states_set_",
                                called_by=self,
                                key=key,
                                value=data["value"],
                                value_type=data["value_type"],
                                value_full=self.states[gateway_id][key],
                                gateway_id=gateway_id,
                                source=source,
                                source_label=source_label,
                                )

    def convert_to_human(self, value, value_type):
        if value_type == "bool":
            results = is_true_false(value)
            if results is not None:
                return results
            else:
                return value

        elif value_type == "epoch":
            return epoch_to_string(value)
        else:
            return value

    @inlineCallbacks
    def get_history(self, key, offset=None, limit=None, gateway_id=None):
        """
        Returns a previous version of the state. Returns a dictionary with "value" and "updated" inside. See
        :py:func:`history_length` to deterine how many entries there are. Max of MAX_HISTORY (currently 100).

        :param key: Name of the state to get.
        :param offset: How far back to go. 0 is current, 1 is previous, etc.
        :param limit: How many records to provide
        :param gateway_id: Gateway ID to get stats for.
        :return:
        """
        if gateway_id is None:
            gateway_id = self.gateway_id

        if offset is None:
            offset = 1
        if limit is None:
            limit = 1
        results = yield self._LocalDB.get_state_history(key, limit, offset, gateway_id=gateway_id)
        if len(results) >= 1:
            return results
        else:
            return

    @inlineCallbacks
    def history_length(self, key):
        """
        Returns how many records a given state (key) has.

        :param key: Name of the state to check.
        :return: How many records there are for a given state.
        :rtype: int
        """
        results = yield self._LocalDB.get_state_count(key)
        return results

    def delete(self, key, gateway_id=None):
        """
        Deletes a status (key).
        KeyError if state not found.

        :raises KeyError: Raised when request is not found.
        :param key: Name of the state to delete.
        :return: None
        :rtype: None
        """
        if gateway_id is None:
            gateway_id = self.gateway_id

        if key in self.states:
            del self.states[gateway_id][key]
        else:
            raise KeyError(f"Cannot delete state: {key} not found")
        return None

    def mqtt_incoming(self, topic, payload, qos, retain):
        """
        Processes incoming MQTT requests. See `MQTT @ Module Development <https://yombo.net/docs/libraries/mqtt>`_

        Examples:

        * /yombo/states/statename/get  - returns a json (preferred)
        * /yombo/states/statename/get abc1234 - returns a json, sends a message ID as a string for tracking
          * A message can only be returned with the above items, cannot be used when requesting a single value.
        * /yombo/states/statename/get/value - returns a string
        * /yombo/states/statename/get/value_type - returns a string
        * /yombo/states/statename/get/value_human - returns a string
        * /yombo/states/statesname/set {"value":"working","value_type":"string"}

        :param topic:
        :param payload:
        :param qos:
        :param retain:
        :return:
        """
        #getting
        #  0       1       2      3      optional payload, one of:
        # yombo/states/statename/get {value (default), value_type, value_human, all (response in json)}

        #setting
        #  0       1       2      3       payload
        # yombo/states/statename/set    new value
        payload = str(payload)

        parts = topic.split("/", 10)
        # print("Yombo States got this: %s / %s" % (topic, parts))
        # requested_state = urllib.unquote(parts[2])
        requested_state = parts[2].replace("$", ".")
        # requested_state = decoded_state.replace("_", " ")
        if len(parts) <= 3 or len(parts) > 5:
            logger.warn("States received an invalid MQTT topic, discarding. Too long or too short. '{topic}'", 
                        topic=topic)
            return

        if  parts[3] not in ("get", "set"):
            # logger.warn("States received an invalid MQTT topic, discarding. Must have either 'set' or 'get'. '%s'" % topic)
            return


        if requested_state not in self.states:
            self.mqtt.publish(f"yombo/states/{parts[2]}/get_response", str("MQTT Error: state not found"))
            return

        state = self.states[self.gateway_id][requested_state]

        if parts[3] == "get":
            request_id = random_string(length=30)

            if len(payload) > 0:
                try:
                    payload = json.loads(payload)
                    if "request_id" in payload:
                        if len(payload["request_id"]) > 100:
                            self.mqtt.publish(f"yombo/states/{parts[2]}/get_response",
                                              str("MQTT Error: request id too long"))
                            return
                except Exception:
                    pass

            if len(parts) == 4 or (len(parts) == 5 and payload == "all"):
                response = {
                    "value": state["value"],
                    "value_type": state["value_type"],
                    "value_human": state["value_human"],
                    "request_id": request_id,
                }
                output = json.dumps(response, separators=(",", ":"))
                self.mqtt.publish(f"yombo/states/{parts[2]}/get_response",
                                  str(output))
                return
            elif len(parts) == 5:

                if payload == "":
                    payload = "value"
                if payload not in ("value", "value_type", "value_human"):
                    logger.warn(
                        f"States received an invalid MQTT get request, invalid request type: '{payload}'")
                    return

                output = ""
                if payload == "value":
                    if isinstance(state["value"], dict) or isinstance(state["value"], list):
                        output = json.dumps(state["value"], separators=(",", ":"))
                    else:
                        output = state["value"]
                elif payload == "value_type":
                    output = state["value_type"]
                elif payload == "value_human":
                    output = state["value_human"]

                    self.mqtt.publish(f"yombo/states/{parts[2]}/get_response/{payload}", str(output))
                return


        elif parts[3] == "set":
            request_id = random_string(length=30)

            try:
                data = json.loads(payload)
                if "request_id" in data:
                    request_id = data["request_id"]

                if "value" not in data:
                    self.mqtt.publish(f"yombo/states/{parts[2]}/set_response",
                                      str(
                                          f"invalid ({request_id}): Payload must contain json with these: value, "
                                          f"value_type, and request_id")
                                      )

                for key in list(data.keys()):
                    if key not in ("value", "value_type", "request_id"):
                        self.mqtt.publish(f"yombo/states/{parts[2]}/set_response",
                                          str(
                                              f"invalid ({request_id}): json contents can only contain value, value_"
                                              f"type and request_id")
                                          )

                if "value_type" not in data:
                    data["value_type"] = None

                self.set(requested_state, data["value"], value_type=data["value_type"], callback=None, arguments=None)
                return
            except Exception:
                self.mqtt.publish(f"yombo/states/{parts[2]}/set_response",
                                  str(
                                      f"invalid ({request_id}): Payload must contain json with these: value, "
                                      f"value_type, and request_id")
                                  )
                return

    ##############################################################################################################
    # Below this demonstrates adding additional scene action types. The following can be used as a simple demo   #
    # showing how to completely add a new scene item control type.                                               #
    ##############################################################################################################

    def _scene_types_list_(self, **kwargs):
        """
        Add an additional scene item control type: states

        :param kwargs:
        :return:
        """
        return [
            {
                "platform": "State",
                "webroutes": f"{self._Atoms.get('app_dir')}/yombo/lib/webinterface/routes/scenes/states.py",
                "add_url": "/scenes/{scene_id}/add_state",
                "note": "Change a state value",
                "render_table_column_callback": self.scene_render_table_column,  # Show summary line in a table.
                "scene_action_update_callback": self.scene_action_update,  # Return a dictionary to store as the item.
                "handle_trigger_callback": self.scene_item_triggered,  # Do item activity
            }
        ]

    def scene_render_table_column(self, scene, action):
        """
        Return a dictionary that will be used to populate some variables for the Jinja2 template for scene action
        rendering.

        :param scene:
        :param action:
        :return:
        """
        return {
            "action_type": f"<strong>State:</strong>{action['name']}<br>"
                           f"<strong>Gateway:</strong>{self._Gateways[action['gateway_id']].label}",
            "attributes": f"<strong>Set Value:</strong><br> {action['value']}",
            "edit_url": f"/scenes/{scene.scene_id}/edit_state/{action['action_id']}",
            "delete_url": f"/scenes/{scene.scene_id}/delete_state/{action['action_id']}",
        }

    def scene_action_update(self, scene, data):
        return {
            "name": data["name"],
            "value": data["value"],
            "value_type": data["value_type"],
            "gateway_id": data["gateway_id"],
            "weight": data["weight"]
        }

    def scene_item_triggered(self, scene, action):
        self.set(action["name"], action["value"], action["value_type"], gateway_id=action["gateway_id"])
        return True
