# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `Commands @ Library Documentation <https://yombo.net/docs/libraries/commands>`_

This library maintains a list of all available commands. The commands (plural) is a wrapper class and contains all
the individual command classes.

The command (singular) class represents one command.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/commands.html>`_
"""
# Import twisted libraries
from twisted.internet.defer import inlineCallbacks, Deferred

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
from yombo.utils import search_instance, do_search_instance, global_invoke_all
from yombo.utils.fuzzysearch import FuzzySearch
from yombo.utils.decorators import cached

logger = get_logger("library.commands")

class Commands(YomboLibrary):
    """
    Manages all commands available for devices.

    All modules already have a predefined reference to this library as
    `self._Commands`. All documentation will reference this use case.
    """
    def __contains__(self, command_requested):
        """
        .. note::

           The command must be enabled to be found using this method.

        Checks to if a provided command id, label, or machine_label exists.

            >>> if "137ab129da9318" in self._Commands:

        or:

            >>> if "living room light" in self._Commands:

        :raises YomboWarning: Raised when request is malformed.
        :param command_requested: The command ID, label, or machine_label to search for.
        :type command_requested: string
        :return: Returns true if exists, otherwise false.
        :rtype: bool
        """
        try:
            self.get(command_requested)
            return True
        except:
            return False

    def __getitem__(self, command_requested):
        """
        .. note::

           The command must be enabled to be found using this method. An alternative,
           but equal function is: :py:meth:`get() <Commands.get>`

        Attempts to find the device requested using a couple of methods.

            >>> off_cmd = self._Commands["137ab129da9318"]  #by id

        or:

            >>> off_cmd = self._Commands["Off"]  #by label & machine_label

        :raises YomboWarning: Raised when request is malformed.
        :raises KeyError: Raised when request is not found.
        :param command_requested: The command ID, label, or machine_label to search for.
        :type command_requested: string
        :return: A pointer to the command instance.
        :rtype: instance
        """
        return self.get(command_requested)

    def __setitem__(self, command_requested, value):
        """
        Sets are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __delitem__(self, command_requested):
        """
        Deletes are not allowed. Raises exception.

        :raises Exception: Always raised.
        """
        raise Exception("Not allowed.")

    def __iter__(self):
        """ iter commands. """
        return self.commands.__iter__()

    def __len__(self):
        """
        Returns an int of the number of commands configured.

        :return: The number of commands configured.
        :rtype: int
        """
        return len(self.commands)

    def __str__(self):
        """
        Returns the name of the library.
        :return: Name of the library
        :rtype: string
        """
        return "Yombo commands library"

    def keys(self):
        """
        Returns the keys (command ID's) that are configured.

        :return: A list of command IDs.
        :rtype: list
        """
        return list(self.commands.keys())

    def items(self):
        """
        Gets a list of tuples representing the commands configured.

        :return: A list of tuples.
        :rtype: list
        """
        return list(self.commands.items())

    def iteritems(self):
        return iter(self.commands.items())

    def iterkeys(self):
        return iter(self.commands.keys())

    def itervalues(self):
        return iter(self.commands.values())

    def values(self):
        return list(self.commands.values())

    def _init_(self, **kwargs):
        """
        Setups up the basic framework.

        """
        self.load_deferred = None  # Prevents loader from moving on past _start_ until we are done.
        self.commands = {}
        self.__yombocommandsByVoice = FuzzySearch(None, .92)
        self.command_search_attributes = ["command_id", "label", "machine_label", "description", "always_load",
            "voice_cmd", "cmd", "status"]

    def _load_(self, **kwargs):
        """
        Loads commands from the database and imports them.
        """
        self._load_commands_from_database()
        self.load_deferred = Deferred()
        return self.load_deferred

    def _stop_(self, **kwargs):
        """
        Cleans up any pending deferreds.
        """
        if self.load_deferred is not None and self.load_deferred.called is False:
            self.load_deferred.callback(1)  # if we don't check for this, we can't stop!

    def _clear_(self, **kwargs):
        """
        Clear all devices. Should only be called by the loader module
        during a reconfiguration event. B{Do not call this function!}
        """
        self.__yombocommandsByVoice.clear()

    def _reload_(self):
        self._load_()

    @inlineCallbacks
    def _load_commands_from_database(self):
        """
        Loads commands from database and sends them to :py:meth:`import_command() <Commands.import_device>`

        This can be triggered either on system startup or when new/updated commands have been saved to the
        database and we need to refresh existing commands.
        """
        commands = yield self._LocalDB.get_commands()
        logger.debug("commands: {commands}", commands=commands)
        for command in commands:
            yield self.import_command(command)
        self.load_deferred.callback(10)

    @inlineCallbacks
    def import_command(self, command, test_command=False):
        """
        Add a new command to memory or update an existing command.

        **Hooks called**:

        * _command_before_load_ : If added, sends command dictionary as "command"
        * _command_before_update_ : If updated, sends command dictionary as "command"
        * _command_loaded_ : If added, send the command instance as "command"
        * _command_updated_ : If updated, send the command instance as "command"

        :param device: A dictionary of items required to either setup a new command or update an existing one.
        :type device: dict
        :param test_command: Used for unit testing.
        :type test_command: bool
        :returns: Pointer to new device. Only used during unittest
        """
        logger.debug("command: {command}", command=command)
        command_id = command["id"]

        yield global_invoke_all("_command_before_import_",
                                called_by=self,
                                command_id=command_id,
                                command=command,
                                )
        if command_id not in self.commands:
            try:
                yield global_invoke_all("_command_before_load_",
                                        called_by=self,
                                        command_id=command_id,
                                        command=command,
                                        )
            except Exception as e:
                pass
            self.commands[command_id] = Command(command)
            try:
                yield global_invoke_all("_command_loaded_",
                                        called_by=self,
                                        command_id=command_id,
                                        command=self.commands[command_id],
                                        )
            except Exception as e:
                pass
        elif command_id in self.commands:
            try:
                yield global_invoke_all("_command_before_update_",
                                        called_by=self,
                                        command_id=command_id,
                                        command=self.commands[command_id],
                                        )
            except Exception as e:
                pass

            self.commands[command_id].update_attributes(command)
            try:
                yield global_invoke_all("_command_updated_",
                                        called_by=self,
                                        command_id=command_id,
                                        command=self.commands[command_id],
                                        )
            except Exception as e:
                pass

        if command["voice_cmd"] is not None:
            self.__yombocommandsByVoice[command["voice_cmd"]] = self.commands[command_id]

        # if test_command:
        #     return self.commands[command_id]

    @cached(30)
    def get(self, command_requested, limiter=None, status=None, command_list=None):
        """
        Looks for commands by it's id, label, and machine_label.

        .. note::

           Modules shouldn't use this function. Use the built in reference to
           find commands:

            >>> self._Commands["sz45q3423"]

        or:

            >>> self._Commands["on"]

        :raises YomboWarning: For invalid requests.
        :raises KeyError: When item requested cannot be found.
        :raises ValueError: When input value is invalid.
        :param command_requested: The command ID, label, and machine_label to search for.
        :type command_requested: string
        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the command to check for.
        :type status: int
        :return: Pointer to requested command.
        :rtype: dict
        """
        if isinstance(command_requested, Command):
            return command_requested
        elif command_requested is None:
            raise KeyError("command_requested is None, so here is None")
        elif isinstance(command_requested, str) is False:
            raise KeyError("command_requested must be command instance or a string.")
        if command_requested in self.commands:
            return self.commands[command_requested]

        if limiter is None:
            limiter = .89

        if limiter > .99999999:
            limiter = .99
        elif limiter < .10:
            limiter = .10

        if command_requested in self.commands:
            item = self.commands[command_requested]
            if status is not None and item.status != status:
                raise KeyError(f"Requested command found, but has invalid status: {item.status}")
            return item
        else:
            attrs = [
                {
                    "field": "command_id",
                    "value": command_requested,
                    "limiter": limiter,
                },
                {
                    "field": "label",
                    "value": command_requested,
                    "limiter": limiter,
                },
                {
                    "field": "machine_label",
                    "value": command_requested,
                    "limiter": limiter,
                }
            ]
            try:
                if command_list is not None:
                    commands = command_list
                else:
                    commands = self.commands
                logger.debug("Get is about to call search...: {command_requested}", command_requested=command_requested)
                found, key, item, ratio, others = do_search_instance(attrs, commands,
                                                                     self.command_search_attributes,
                                                                     limiter=limiter,
                                                                     operation="highest")
                logger.debug("found command by search: {command_id}", command_id=key)
                if found:
                    return item
                else:
                    raise KeyError(f"Command not found: {command_requested}")
            except YomboWarning as e:
                raise KeyError(f"Searched for {command_requested}, but had problems: {e}")

    def search(self, _limiter=None, _operation=None, **kwargs):
        """
        Advanced search, typically should use the :py:meth:`get <yombo.lib.commands.Commands.get>` method.

        :param limiter_override: Default: .89 - A value between .5 and .99. Sets how close of a match it the search should be.
        :type limiter_override: float
        :param status: Deafult: 1 - The status of the command to check for.
        :return:
        """
        return search_instance(kwargs,
                               self.commands,
                               self.command_search_attributes,
                               _limiter,
                               _operation)

    def get_commands_by_voice(self):
        """
        This function shouldn't be used by modules. Internal use only. For modules,
        use: `self._Commands["on"]` to search by name.

        :return: Pointer to array of all devices.
        :rtype: dict
        """
        return self.__yombocommandsByVoice

    def get_local_commands(self):
        """
        Return a dictionary with all the public commands.

        :return: Returns any commands that are not publicly available.
        :rtype: list of objects
        """
        results = {}
        for command_id, command in self.commands.items():
            if command.public <= 1:
                results[command_id] = command
        return results

    def get_public_commands(self):
        """
        Return a dictionary with all the public commands.

        :return:
        """
        results = {}
        for command_id, command in self.commands.items():
            if command.public == 2:
                results[command_id] = command
        return results

    @inlineCallbacks
    def dev_command_add(self, data, **kwargs):
        """
        Used to interact with the Yombo API to add a new command. This doesn't add a new command
        to the local gateway.

        :param data: Fields to send to the Yombo API. See https://yg2.in/api for details.
        :type data: dict
        :param kwargs: Currently unused.
        :return: Results on the success/fail of the add request.
        :rtype: dict
        """
        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't add command: User session missing.",
                    "apimsg": "Couldn't add command: User session missing.",
                    "apimsghtml": "Couldn't add command: User session missing.",
                }
            command_results = yield self._YomboAPI.request("POST", "/v1/command",
                                                           data,
                                                           session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't add command: {e.message}",
                "apimsg": f"Couldn't add command: {e.message}",
                "apimsghtml": f"Couldn't add command: {e.html_message}",
            }

        # print("command edit results: %s" % command_results)

        return {
            "status": "success",
            "msg": "Command added.",
            "data": command_results["data"],
        }

    @inlineCallbacks
    def dev_command_edit(self, command_id, data, **kwargs):
        """
        Used to interact with the Yombo API to edit a command. This doesn't edit the command
        on the local gateway.

        :param data: Fields to send to the Yombo API. See https://yombo.net/API:Commands for details.
        :type data: dict
        :param kwargs: Currently unused.
        :return: Results on the success/fail of the request.
        :rtype: dict
        """
        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't edit command: User session missing.",
                    "apimsg": "Couldn't edit command: User session missing.",
                    "apimsghtml": "Couldn't edit command: User session missing.",
                }
            command_results = yield self._YomboAPI.request("PATCH", f"/v1/command/{command_id}",
                                                           data,
                                                           session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't edit command: {e.message}",
                "apimsg": f"Couldn't edit command: {e.message}",
                "apimsghtml": f"Couldn't edit command: {e.html_message}",
            }

        # print("command edit results: %s" % command_results)

        return {
            "status": "success",
            "msg": "Command edited.",
            "data": command_results["data"],
        }

    @inlineCallbacks
    def dev_command_delete(self, command_id, **kwargs):
        """
        Used to interact with the Yombo API to delete a command. This doesn't delete the command
        on the local gateway.

        :param data: Fields to send to the Yombo API. See https://yombo.net/API:Commands for details.
        :type data: dict
        :param kwargs: Currently unused.
        :return: Results on the success/fail of the request.
        :rtype: dict
        """
        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't delete command: User session missing.",
                    "apimsg": "Couldn't delete command: User session missing.",
                    "apimsghtml": "Couldn't delete command: User session missing.",
                }

            command_results = yield self._YomboAPI.request("DELETE",
                                                           f"/v1/command/{command_id}",
                                                           session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't delete command: {e.message}",
                "apimsg": f"Couldn't delete command: {e.message}",
                "apimsghtml": f"Couldn't delete command: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Command deleted.",
            "data": command_results["data"],
        }

    @inlineCallbacks
    def dev_command_enable(self, command_id, **kwargs):
        """
        Used to interact with the Yombo API to enable a command. This doesn't enable the command
        on the local gateway.

        :param data: Fields to send to the Yombo API. See https://yombo.net/API:Commands for details.
        :type data: dict
        :param kwargs: Currently unused.
        :return: Results on the success/fail of the request.
        :rtype: dict
        """
        api_data = {
            "status": 1,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't enable command: User session missing.",
                    "apimsg": "Couldn't enable command: User session missing.",
                    "apimsghtml": "Couldn't enable command: User session missing.",
                }

            command_results = yield self._YomboAPI.request("PATCH",
                                                           f"/v1/command/{command_id}",
                                                           api_data,
                                                           session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't enable command: {e.message}",
                "apimsg": f"Couldn't enable command: {e.message}",
                "apimsghtml": f"Couldn't enable command: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Command enabled.",
            "data": command_results["data"],
        }

    @inlineCallbacks
    def dev_command_disable(self, command_id, **kwargs):
        """
        Used to interact with the Yombo API to disable a command. This doesn't diable the command
        on the local gateway.

        :param data: Fields to send to the Yombo API. See https://yombo.net/API:Commands for details.
        :type data: dict
        :param kwargs: Currently unused.
        :return: Results on the success/fail of the request.
        :rtype: dict
        """
        api_data = {
            "status": 0,
        }

        try:
            if "session" in kwargs:
                session = kwargs["session"]
            else:
                return {
                    "status": "failed",
                    "msg": "Couldn't disable command: User session missing.",
                    "apimsg": "Couldn't disable command: User session missing.",
                    "apimsghtml": "Couldn't disable command: User session missing.",
                }

            command_results = yield self._YomboAPI.request("PATCH",
                                                           f"/v1/command/{command_id}",
                                                           api_data,
                                                           session=session)
        except YomboWarning as e:
            return {
                "status": "failed",
                "msg": f"Couldn't disable command: {e.message}",
                "apimsg": f"Couldn't disable command: {e.message}",
                "apimsghtml": f"Couldn't disable command: {e.html_message}",
            }

        return {
            "status": "success",
            "msg": "Command disabled.",
            "data": command_results["data"],
        }

    def full_list_commands(self):
        """
        Return a list of dictionaries representing all known commands to this gateway.
        :return:
        """
        items = []
        for command_id, command in self.commands.items():
            items.append(command.asdict())
        return items


class Command:
    """
    A command is represented by this class is is returned to callers of the
    :py:meth:`get() <Commands.get>` or :py:meth:`__getitem__() <Commands.__getitem__>` functions.
    """

    def __init__(self, command):
        """
        Setup the command object using information passed in.

        :param command: A command containing required items to setup.
        :type command: dict
        :return: None
        """
        logger.debug("command info: {command}", command=command)

        self.command_id = command["id"]
        self.cmd = command["machine_label"]
        self.machine_label = self.cmd

        # the below are setup during update_attributes()
        self.label = None
        self.description = None
        self.voice_cmd = None
        self.always_load = None
        self.public = None
        self.status = None
        self.created_at = None
        self.updated_at = None

        self.update_attributes(command)

    def update_attributes(self, command):
        """
        Sets various values from a command dictionary. This can be called when either new or
        when updating.

        :param command: A dictionary containing attributes to update.
        :type command: dict
        :return: None
        """
        self.label = command["label"]
        self.description = command["description"]
        self.voice_cmd = command["voice_cmd"]
        self.always_load = command["always_load"]
        self.public = command["public"]
        self.status = command["status"]
        self.created_at = command["created_at"]
        self.updated_at = command["updated_at"]

    def __str__(self):
        """
        Print a string when printing the class.  This will return the command_id so that
        the command can be identified and referenced easily.

        :return: The command id.
        :rtype: str
        """
        return self.command_id

    def asdict(self):
        """
        Export command variables as a dictionary.
        """
        return {
            "command_id": str(self.command_id),
            "always_load": str(self.always_load),
            "voice_cmd": str(self.voice_cmd),
            "cmd": str(self.cmd),  # AKA machineLabel
            "label": str(self.label),
            "machine_label": str(self.machine_label),
            "description": str(self.description),
            "public": int(self.public),
            "status": int(self.status),
            "created_at": int(self.created_at),
            "updated_at": int(self.updated_at),
        }

    def __repl__(self):
        """
        Export command variables as a dictionary.

        :return: A dictionary that can be used to re-create this instance.
        :rtype: dict
        """
        return {
            "command_id": str(self.command_id),
            "always_load": str(self.always_load),
            "voice_cmd": str(self.voice_cmd),
            "cmd": str(self.cmd),  # AKA machineLabel
            "label": str(self.label),
            "machine_label": str(self.machine_label),
            "description": str(self.description),
            "public": int(self.public),
            "status": int(self.status),
            "created_at": int(self.created_at),
            "updated_at": int(self.updated_at),
        }
