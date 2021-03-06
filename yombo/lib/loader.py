# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
.. note::

  * For library documentation, see: `Loader @ Library Documentation <https://yombo.net/docs/libraries/loader>`_

Responsible for importing, starting, and stopping all libraries and modules.

Starts libraries and modules (components) in the following phases.  These
phases are first completed for libraries.  After "start" phase has completed
then modules startup in the same method.

#. Import all components
#. Call "init" for all components

   * Get the component ready, but not do any actual work yet.
   * Components can now see a full list of components there were imported.
  
#. Call "load" for all components
#. Call "start" for all components

Stops components in the following phases. Modules first, then libraries.

#. Call "stop" for all components
#. Call "unload" for all components

.. warning::

  Module developers and users should not access any of these functions
  or variables.  This is listed here for completeness. Use a :ref:`framework_utils`
  function to get what is needed.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2012-2018 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/loader.html>`_
"""
# Import python libraries
import asyncio
from collections import Callable
import os.path
from packaging.requirements import Requirement as pkg_requirement
from random import randint
from re import search as ReSearch
from subprocess import check_output
import traceback

# Import twisted libraries
from twisted.internet import reactor
from twisted.internet.defer import inlineCallbacks, maybeDeferred, Deferred
from twisted.web import client
from functools import reduce
client._HTTP11ClientFactory.noisy = False

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboCritical, YomboWarning, YomboHookStopProcessing
from yombo.classes.fuzzysearch import FuzzySearch
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger
import yombo.utils

logger = get_logger("library.loader")

HARD_LOAD = {}
HARD_LOAD["Events"] = {"operating_mode": "all"}
HARD_LOAD["Calllater"] = {"operating_mode": "all"}
HARD_LOAD["Cache"] = {"operating_mode": "all"}
HARD_LOAD["Validate"] = {"operating_mode": "all"}
HARD_LOAD["Locations"] = {"operating_mode": "all"}
HARD_LOAD["Requests"] = {"operating_mode": "all"}
HARD_LOAD["Template"] = {"operating_mode": "all"}
HARD_LOAD["Queue"] = {"operating_mode": "all"}
HARD_LOAD["Notifications"] = {"operating_mode": "all"}
HARD_LOAD["LocalDB"] = {"operating_mode": "all"}
HARD_LOAD["SQLDict"] = {"operating_mode": "all"}
HARD_LOAD["GPG"] = {"operating_mode": "all"}
HARD_LOAD["Configuration"] = {"operating_mode": "all"}
HARD_LOAD["YomboAPI"] = {"operating_mode": "all"}
HARD_LOAD["Startup"] = {"operating_mode": "all"}
HARD_LOAD["Localize"] = {"operating_mode": "all"}
HARD_LOAD["Hash"] = {"operating_mode": "all"}
HARD_LOAD["HashIDS"] = {"operating_mode": "all"}
HARD_LOAD["Discovery"] = {"operating_mode": "all"}
HARD_LOAD["Atoms"] = {"operating_mode": "all"}
HARD_LOAD["States"] = {"operating_mode": "all"}
HARD_LOAD["Statistics"] = {"operating_mode": "all"}
HARD_LOAD["AMQP"] = {"operating_mode": "run"}
HARD_LOAD["CronTab"] = {"operating_mode": "all"}
HARD_LOAD["Times"] = {"operating_mode": "all"}
HARD_LOAD["Commands"] = {"operating_mode": "all"}
HARD_LOAD["VariableData"] = {"operating_mode": "all"}
HARD_LOAD["VariableFields"] = {"operating_mode": "all"}
HARD_LOAD["VariableGroups"] = {"operating_mode": "all"}
HARD_LOAD["DeviceCommandInputs"] = {"operating_mode": "all"}
HARD_LOAD["DeviceTypeCommands"] = {"operating_mode": "all"}
HARD_LOAD["DeviceTypes"] = {"operating_mode": "all"}
HARD_LOAD["InputTypes"] = {"operating_mode": "all"}
HARD_LOAD["ModuleDeviceTypes"] = {"operating_mode": "all"}
HARD_LOAD["Modules"] = {"operating_mode": "all"}
HARD_LOAD["Devices"] = {"operating_mode": "all"}
HARD_LOAD["DeviceCommands"] = {"operating_mode": "all"}
HARD_LOAD["SystemDataHandler"] = {"operating_mode": "run"}
HARD_LOAD["AMQPYombo"] = {"operating_mode": "run"}
HARD_LOAD["Gateways"] = {"operating_mode": "all"}
HARD_LOAD["GatewayCommunications"] = {"operating_mode": "all"}
HARD_LOAD["DownloadModules"] = {"operating_mode": "run"}
HARD_LOAD["Nodes"] = {"operating_mode": "all"}
HARD_LOAD["MQTT"] = {"operating_mode": "run"}
HARD_LOAD["SSLCerts"] = {"operating_mode": "all"}
HARD_LOAD["WebSessions"] = {"operating_mode": "all"}
HARD_LOAD["WebInterface"] = {"operating_mode": "all"}
HARD_LOAD["Tasks"] = {"operating_mode": "all"}
HARD_LOAD["Automation"] = {"operating_mode": "all"}
HARD_LOAD["Scenes"] = {"operating_mode": "all"}
HARD_LOAD["Users"] = {"operating_mode": "all"}
HARD_LOAD["AuthKeys"] = {"operating_mode": "all"}
HARD_LOAD["Intents"] = {"operating_mode": "all"}
HARD_LOAD["Storage"] = {"operating_mode": "all"}

HARD_UNLOAD = {}
HARD_UNLOAD["Users"] = {"operating_mode": "all"}
HARD_UNLOAD["Gateways"] = {"operating_mode": "all"}
HARD_UNLOAD["GatewayCommunications"] = {"operating_mode": "all"}
HARD_UNLOAD["SSLCerts"] = {"operating_mode": "all"}
HARD_UNLOAD["Scenes"] = {"operating_mode": "all"}
HARD_UNLOAD["Automation"] = {"operating_mode": "all"}
HARD_UNLOAD["Tasks"] = {"operating_mode": "all"}
HARD_UNLOAD["Localize"] = {"operating_mode": "all"}
HARD_UNLOAD["Startup"] = {"operating_mode": "all"}
HARD_UNLOAD["YomboAPI"] = {"operating_mode": "all"}
HARD_UNLOAD["GPG"] = {"operating_mode": "all"}
HARD_UNLOAD["CronTab"] = {"operating_mode": "all"}
HARD_UNLOAD["Times"] = {"operating_mode": "all"}
HARD_UNLOAD["Commands"] = {"operating_mode": "all"}
HARD_UNLOAD["DeviceTypes"] = {"operating_mode": "all"}
HARD_UNLOAD["DeviceCommandInputs"] = {"operating_mode": "all"}
HARD_UNLOAD["DeviceTypeCommands"] = {"operating_mode": "all"}
HARD_UNLOAD["InputTypes"] = {"operating_mode": "all"}
HARD_UNLOAD["Devices"] = {"operating_mode": "all"}
HARD_UNLOAD["Locations"] = {"operating_mode": "all"}
HARD_UNLOAD["Nodes"] = {"operating_mode": "all"}
HARD_UNLOAD["Atoms"] = {"operating_mode": "all"}
HARD_UNLOAD["States"] = {"operating_mode": "all"}
HARD_UNLOAD["WebInterface"] = {"operating_mode": "all"}
HARD_UNLOAD["AuthKeys"] = {"operating_mode": "all"}
HARD_UNLOAD["WebSessions"] = {"operating_mode": "all"}
HARD_UNLOAD["Devices"] = {"operating_mode": "all"}
HARD_UNLOAD["DeviceCommands"] = {"operating_mode": "all"}
HARD_UNLOAD["AMQPYombo"] = {"operating_mode": "run"}
HARD_UNLOAD["Configuration"] = {"operating_mode": "all"}
HARD_UNLOAD["Statistics"] = {"operating_mode": "all"}
HARD_UNLOAD["Modules"] = {"operating_mode": "all"}
HARD_UNLOAD["MQTT"] = {"operating_mode": "run"}
HARD_UNLOAD["SQLDict"] = {"operating_mode": "all"}
HARD_UNLOAD["AMQP"] = {"operating_mode": "run"}
HARD_UNLOAD["Modules"] = {"operating_mode": "all"}
HARD_UNLOAD["VariableData"] = {"operating_mode": "all"}
HARD_UNLOAD["VariableFields"] = {"operating_mode": "all"}
HARD_UNLOAD["VariableGroups"] = {"operating_mode": "all"}
HARD_UNLOAD["DownloadModules"] = {"operating_mode": "run"}
HARD_UNLOAD["Queue"] = {"operating_mode": "all"}
HARD_UNLOAD["Events"] = {"operating_mode": "all"}
HARD_UNLOAD["LocalDB"] = {"operating_mode": "all"}

RUN_PHASE = {
    "system_init": 0,
    "system_start": 10,
    "libraries_import": 500,
    "libraries_init": 1000,
    "modules_import": 1500,
    "libraries_load": 2000,
    "modules_pre_init": 2500,
    "modules_init": 3000,
    "libraries_start": 3500,
    "libraries_started": 4000,
    "modules_preload": 4500,
    "modules_load": 5000,
    "modules_prestart": 5500,
    "modules_start": 6000,
    "modules_started": 6500,
    "system_loaded": 7000,
    "gateway_running": 10000,
    "shutdown": 15000,
    "modules_stop": 15500,
    "modules_unload": 16000,
    "libraries_stop": 16500,
    "libraries_unload": 17000,
}


class Loader(YomboLibrary):
    """
    Responsible for loading libraries, and then delegating loading modules to
    the modules library.

    Libraries are never reloaded, however, during a reconfiguration,
    modules are unloaded, and then reloaded after configurations are done
    being downloaded.
    """
    @property
    def gateway_id(self):
        if self._Loader.operating_mode != "run":
            return "local"
        return self._Configs.configs["core"]["gwid"]["value"]  # Shortcut to get the gateway_id directly

    @gateway_id.setter
    def gateway_id(self, val):
        return

    @property
    def is_master(self):
        if self._Loader.operating_mode != "run":
            return 1
        return self._Configs.configs["core"]["is_master"]["value"]  # Shortcut to get the gateway_id directly

    @is_master.setter
    def is_master(self, val):
        return

    @property
    def master_gateway_id(self):
        if self._Loader.operating_mode != "run":
            return "local"
        return self._Configs.configs["core"]["master_gateway_id"]["value"]  # Shortcut to get the gateway_id directly

    @master_gateway_id.setter
    def master_gateway_id(self, val):
        return

    @property
    def operating_mode(self):
        return self._operating_mode

    @operating_mode.setter
    def operating_mode(self, val):
        if RUN_PHASE[self._run_phase] > 500:
            self.loaded_libraries["states"]["loader.operating_mode"] = val
            if val == 'run':
                logger.debug("Operating mode set to: {mode}", mode=val)
            else:
                logger.warn("Operating mode set to: {mode}", mode=val)
        self._operating_mode = val

    @property
    def run_phase(self):
        return self._run_phase, RUN_PHASE[self._run_phase]

    @run_phase.setter
    def run_phase(self, val):
        if RUN_PHASE[val] > 500:
            self.loaded_libraries["states"]["loader.run_phase"] = val
        self._run_phase = val

    def __getitem__(self, component_requested):
        """
        Look for a requested component, either a library or a module. This searches thru libraries first, then
        modules.
        """
        logger.debug("looking for: {component_requested}", component_requested=component_requested)
        if component_requested in self.loaded_components:
            logger.debug("found by loaded_components! {component_requested}", component_requested=component_requested)
            return self.loaded_components[component_requested]
        elif component_requested in self.loaded_libraries:
            logger.debug("found by loaded_libraries! {component_requested}", component_requested=component_requested)
            return self.loaded_libraries[component_requested]
        elif component_requested in self._moduleLibrary:
            logger.debug("found by self._moduleLibrary! {component_requested}", component_requested=self._moduleLibrary)
            return self._moduleLibrary[component_requested]
        else:
            raise YomboWarning(f"Loader could not find requested component: {{component_requested}}",
                               "101", "__getitem__", "loader")

    def __init__(self, testing=False):
        super().__init__(self)
        Entity._Root = self  # Configures the _Root attributes within the Entity class.
        self.startup_events_queue = []
        self._operating_mode = "system_init"
        self._run_phase = "system_init"
        self.unittest = testing
        self._moduleLibrary = None
        self.event_loop = None
        self.force_python_module_upgrade = False

        self.requirements = {}  # Track which python modules are required

        self.loaded_components = FuzzySearch({self._ClassPath.lower(): self}, .95)
        self.loaded_libraries = FuzzySearch({self._Name.lower(): self}, .95)
        self._invoke_list_cache = {}  # Store a list of hooks that exist or not. A cache.
        self._operating_mode = None  # One of: first_run, config, run
        self.sigint = False  # will be set to true if SIGINT is received
        self.hook_counts = {}  # keep track of hook names, and how many times it's called.

        reactor.addSystemEventTrigger("before", "shutdown", self.shutdown)

    # @inlineCallbacks
    def shutdown(self):
        """
        This is called if SIGINT (ctrl-c) was caught. Very useful incase it was called during startup.
        :return:
        """
        # logger.info("Yombo Gateway stopping.")
        self._run_phase = "shutdown"
        self.sigint = True
        # yield self.unload()

    @inlineCallbacks
    def start(self):  # on startup, load libraries, then modules
        """
        This is effectively the main start function.

        This function is called when the gateway is to startup. In turn,
        this function will load all the components and modules of the gateway.
        """
        self.run_phase = "system_start"

        if randint(1, 10) == 1:
            logger.debug("Upgrading pip...")
            check_output(["pip3", "install", "--upgrade", "pip"])

        logger.info("Reading Yombo requirements.txt file and checking for updates.")
        if os.path.isfile("requirements.txt"):
            try:
                input = yield yombo.utils.read_file("requirements.txt")
            except Exception as e:
                logger.warn("Unable to process requirements file for loader library, reason: {e}", e=e)
            else:
                requirements = yombo.utils.bytes_to_unicode(input.splitlines())
                for line in requirements:
                    yield self.install_python_requirement(line)

        # Get a reference to the asyncio event loop.
        logger.debug("Starting UVLoop")
        yield yombo.utils.sleep(0.01)  # kick the asyncio event loop
        self.event_loop = asyncio.get_event_loop()

        yield self.import_libraries()  # import and init all libraries
        logger.info("Importing libraries, this can take a few moments.")

        self._Configs = self.loaded_libraries["configuration"]

        if self.sigint:
            return
        logger.debug("Calling load functions of libraries.")

        self._run_phase = "modules_import"
        self.operating_mode = self.operating_mode  # so we can update the State!
        if self.operating_mode == "run":
            yield self._moduleLibrary.prepare_modules()
            self._moduleLibrary.import_modules()

        for name, config in HARD_LOAD.items():
            if self.sigint:
                return
            self._log_loader("debug", name, "library", "modules_imported", "About to call _modules_imported_.")
            if self.check_operating_mode(config["operating_mode"]):
                libraryName = name.lower()
                yield self.library_invoke(libraryName, "_modules_imported_", called_by=self)
                HARD_LOAD[name]["_modules_imported_"] = True
            else:
                HARD_LOAD[name]["_modules_imported_"] = False
            self._log_loader("debug", name, "library", "modules_imported", "Finished call to _modules_imported_.")

        self._run_phase = "libraries_load"
        for name, config in HARD_LOAD.items():
            if self.sigint:
                return
            # self._log_loader("debug", name, "library", "load", "About to call _load_.")
            if self.check_operating_mode(config["operating_mode"]):
                HARD_LOAD[name]["_load_"] = "Starting"
                libraryName = name.lower()
                yield self.library_invoke(libraryName, "_load_", called_by=self)
                HARD_LOAD[name]["_load_"] = True
            else:
                HARD_LOAD[name]["_load_"] = False
            self._log_loader("debug", name, "library", "load", "Finished call to _load_.")

        self._moduleLibrary = self.loaded_libraries["modules"]

        # Sets run phase to modules_pre_init and then modules_init'
        yield self._moduleLibrary.init_modules()

        self._run_phase = "libraries_start"
        for name, config in HARD_LOAD.items():
            if self.sigint:
                return
            self._log_loader("debug", name, "library", "start", "About to call _start_.")
            if self.check_operating_mode(config["operating_mode"]):
                libraryName = name.lower()
                yield self.library_invoke(libraryName, "_start_", called_by=self)
                HARD_LOAD[name]["_start_"] = True
            else:
                HARD_LOAD[name]["_start_"] = False
            self._log_loader("debug", name, "library", "_start_", "Finished call to _start_.")

        yield self._moduleLibrary.load_modules()  #includes load & start

        self._run_phase = "libraries_started"
        for name, config in HARD_LOAD.items():
            if self.sigint:
                return
            self._log_loader("debug", name, "library", "started", "About to call _started_.")
            if self.check_operating_mode(config["operating_mode"]):
                libraryName =  name.lower()
                yield self.library_invoke(libraryName, "_started_", called_by=self)
                HARD_LOAD[name]["_started_"] = True
            else:
                HARD_LOAD[name]["_started_"] = False

        self._run_phase = "system_loaded"
        for name, config in HARD_LOAD.items():
            if self.sigint:
                return
            self._log_loader("debug", name, "library", "_modules_started_", "About to call _modules_started_.")
            if self.check_operating_mode(config["operating_mode"]):
                libraryName =  name.lower()
                yield self.library_invoke(libraryName, "_modules_started_", called_by=self)
                HARD_LOAD[name]["_started_"] = True
            else:
                HARD_LOAD[name]["_started_"] = False

        self.loaded_libraries["notifications"].add(
            {"title": "System started",
             "message": "System successfully started.",
             "timeout": 300,
             "source": "Yombo Gateway System",
             "persist": False,
             "always_show": False,
             "targets": "system_startup_complete",
             })

        for event in self.startup_events_queue:
            created_at=event.pop()
            self.loaded_libraries["events"].new(*event, created_at=created_at)
        self.startup_events_queue = None
        self._run_phase = "gateway_running"
        logger.info("Yombo Gateway started.")

    @inlineCallbacks
    def unload(self):
        """
        Called when the gateway should stop. This will gracefully stop the gateway.

        First, unload all modules, then unload all components.
        """
        self.sigint = True  # it"s 99.999% true - usually only shutdown due to this.
        if self._moduleLibrary is not None:
            yield self._moduleLibrary.unload_modules()
        yield self.unload_libraries()
        # self.loop.close()

    @inlineCallbacks
    def install_python_requirement(self, requirement, source=None):
        if source is None:
            source = "System"
        line = yombo.utils.bytes_to_unicode(requirement)
        line = line.strip()
        if len(line) == 0 or line.startswith("#") or line.startswith("git+"):
            return
        logger.debug("Processing requirement: {requirement}", requirement=line)
        requirement = pkg_requirement(line)
        package_name = requirement.name
        package_specifier = requirement.specifier

        if package_name in self.requirements:
            if self.requirements[package_name]['specifier'] == package_specifier:
                self.requirements[package_name]['used_by'].append(source)
                return
            else:
                logger.warn("Unable to install conflicting python module '{name}'. Version '{current}' already set,"
                            " requested '{new}' by: {source}",
                            name=package_name, current=self.requirements[package_name]['specifier'],
                            new=package_specifier, source=source)

                return

        try:
            pkg_info = yield yombo.utils.get_python_package_info(line, events_queue=self.startup_events_queue)
            # logger.debug("Processing requirement: results: {results}", results=pkg_info)
            if pkg_info is None:
                return
        except YomboWarning as e:
            raise YomboCritical(e.message)
        # logger.debug("Have requirement details...")
        if pkg_info is not None:
            save_info = {
                "name": pkg_info.project_name,
                "version": pkg_info._version,
                "path": pkg_info.location,
                "used_by": [source, ],
                "specifier": package_specifier,
            }
        else:
            save_info = {
                "name": package_name,
                "version": "Invalid python module",
                "path": "Invalid module",
                "used_by": [source, ],
                "specifier": package_specifier,
            }

        self.requirements[package_name] = save_info

    def Loader_i18n_atoms(self, **kwargs):
       return [
           {"loader.operating_mode": {
               "en": "One of: first_run, run, config",
               },
           },
       ]

    def check_component_status(self, name, function):
        if name in HARD_LOAD:
            if function in HARD_LOAD[name]:
                return HARD_LOAD[name][function]
        return None

    def _log_loader(self, level, label, type, method, msg=""):
        """
        A common log format for loading/unloading libraries and modules.

        :param level: Log level - debug, info, warn...
        :param label: Module label "x10", "messages"
        :param type: Type of item being loaded: library, module
        :param method: Method being called.
        :param msg: Optional message to include.
        :return:
        """
        log = getattr(logger, level)
        log("Loader: {label}({type})::{method} - {msg}", label=label, type=type, method=method, msg=msg)

    def import_libraries_failure(self, failure):
        logger.error("Got failure during import of library: {failure}. Going to stop now.", failure=failure)
        raise YomboCritical("Load failure for gateway library.")

    @inlineCallbacks
    def import_libraries(self):
        """
        Import then "init" all libraries. Call "loadLibraries" when done.
        """
        logger.debug("Importing gateway libraries.")
        self._run_phase = "libraries_import"
        for name, config in HARD_LOAD.items():
            if self.sigint:
                return
            HARD_LOAD[name]["__init__"] = "Starting"
            pathName = f"yombo.lib.{name}"
            self.import_component(pathName, name, "library")
            HARD_LOAD[name]["__init__"] = True

            component = name.lower()
            library = self.loaded_libraries[component]
            if hasattr(library, "_pre_init_") and isinstance(library._pre_init_, Callable) \
                    and yombo.utils.get_method_definition_level(library._pre_init_) != "yombo.core.module.YomboModule":
                d = Deferred()
                d.addCallback(lambda ignored: self._log_loader("debug", name, "library", "init", "About to call _pre_init_."))
                d.addCallback(lambda ignored: maybeDeferred(library._pre_init_))
                d.callback(1)
                yield d

        logger.debug("Done importing, about to setup Entity class.")
        Entity._Configure_Entity_Class_Do_Not_Call_Me_By_My_Name_()  # Configures the _Root attributes within the Entity class.

        logger.debug("Done with Entity setup, about to start _init_'s.")

        logger.debug("Calling init functions of libraries.")
        self._run_phase = "libraries_init"
        for name, config in HARD_LOAD.items():
            # logger.debug("Library: {name}", name=name)
            if self.sigint:
                return
            HARD_LOAD[name]["_init_"] = False
            # self._log_loader("debug", name, "library", "init", "About to call _init_.")
            component = name.lower()
            library = self.loaded_libraries[component]
            library._event_loop = self.event_loop
            library._AMQP = self.loaded_libraries["amqp"]
            library._AMQPYombo = self.loaded_libraries["amqpyombo"]
            library._Atoms = self.loaded_libraries["atoms"]
            library._AuthKeys = self.loaded_libraries["authkeys"]
            library._Automation = self.loaded_libraries["automation"]
            library._Cache = self.loaded_libraries["cache"]
            library._CallLater = self.loaded_libraries["calllater"]
            library._Commands = self.loaded_libraries["commands"]
            library._Configs = self.loaded_libraries["configuration"]
            library._CronTab = self.loaded_libraries["crontab"]
            library._Events = self.loaded_libraries["events"]
            library._Devices = self.loaded_libraries["devices"]
            library._DeviceCommands = self.loaded_libraries["devicecommands"]
            library._DeviceCommandInputs = self.loaded_libraries["devicecommandinputs"]
            library._DeviceTypeCommands = self.loaded_libraries["devicetypecommands"]
            library._DeviceTypes = self.loaded_libraries["devicetypes"]
            library._Discovery = self.loaded_libraries["discovery"]
            library._DownloadModules = self.loaded_libraries["downloadmodules"]
            library._Gateways = self.loaded_libraries["gateways"]
            library._GatewayComs = self.loaded_libraries["gatewayscommunications"]
            library._GPG = self.loaded_libraries["gpg"]
            library._Hash = self.loaded_libraries["hash"]
            library._HashIDS = self.loaded_libraries["hashids"]
            library._InputTypes = self.loaded_libraries["inputtypes"]
            library._Intents = self.loaded_libraries["intents"]
            library._Locations = self.loaded_libraries["locations"]
            library._Loader = self
            library._Localize = self.loaded_libraries["localize"]
            library._LocalDB = self.loaded_libraries["localdb"]
            library._Locations = self.loaded_libraries["locations"]
            library._Modules = self._moduleLibrary
            library._ModuleDeviceTypes = self.loaded_libraries["moduledevicetypes"]
            library._MQTT = self.loaded_libraries["mqtt"]
            library._Nodes = self.loaded_libraries["nodes"]
            library._Notifications = self.loaded_libraries["notifications"]
            library._Queue = self.loaded_libraries["queue"]
            library._Requests = self.loaded_libraries["requests"]
            library._Scenes = self.loaded_libraries["scenes"]
            library._SQLDict = self.loaded_libraries["sqldict"]
            library._SSLCerts = self.loaded_libraries["sslcerts"]
            library._Startup = self.loaded_libraries["startup"]
            library._States = self.loaded_libraries["states"]
            library._Statistics = self.loaded_libraries["statistics"]
            library._Storage = self.loaded_libraries["storage"]
            library._Tasks = self.loaded_libraries["tasks"]
            library._Template = self.loaded_libraries["template"]
            library._Times = self.loaded_libraries["times"]
            library._YomboAPI = self.loaded_libraries["yomboapi"]
            library._Users = self.loaded_libraries["users"]
            library._VariableData = self.loaded_libraries["variabledata"]
            library._VariableFields = self.loaded_libraries["variablefields"]
            library._VariableGroups = self.loaded_libraries["variablegroups"]
            library._Validate = self.loaded_libraries["validate"]
            library._WebInterface = self.loaded_libraries["webinterface"]
            library._WebSessions = self.loaded_libraries["websessions"]

            # self._log_loader("debug", name, "library", "init", "Done with load magic attributes.")

            if self.check_operating_mode(config["operating_mode"]) is False:
                continue
            HARD_LOAD[name]["_init_"] = "Starting"
            if hasattr(library, "_init_") and isinstance(library._init_, Callable) \
                    and yombo.utils.get_method_definition_level(library._init_) != "yombo.core.module.YomboModule":
                d = Deferred()
                d.addCallback(lambda ignored: self._log_loader("debug", name, "library", "init", "About to call _init_."))
                d.addCallback(lambda ignored: maybeDeferred(library._init_))
                d.addErrback(self.import_libraries_failure)
                # d.addCallback(lambda ignored: self._log_loader("debug", name, "library", "init", "Done with call _init_."))
                d.callback(1)
                yield d
                HARD_LOAD[name]["_init_"] = True
            else:
                logger.error("----==(Library doesn't have init function: {name})==-----", name=name)
            if hasattr(library, "_init2_") and isinstance(library._init2_, Callable) \
                    and yombo.utils.get_method_definition_level(library._init2_) != "yombo.core.module.YomboModule":
                d = Deferred()
                d.addCallback(lambda ignored: self._log_loader("debug", name, "library", "init", "About to call _init2_."))
                d.addCallback(lambda ignored: maybeDeferred(library._init2_))
                d.addErrback(self.import_libraries_failure)
                # d.addCallback(lambda ignored: self._log_loader("debug", name, "library", "init", "Done with call _init2_."))
                d.callback(1)
                yield d

        yombo.utils.setup_yombo_references(self.loaded_libraries["amqp"])

    def check_operating_mode(self, allowed):
        """
        Checks if something should be run based on the current operating_mode.

        :param allowed: Either string or list or possible operating_modes
        :return: True/False
        """
        operating_mode = self.operating_mode

        if operating_mode is None:
            return True

        def check_operating_mode_inside(mode, operating_mode):
            if mode == "all":
                return True
            elif mode == operating_mode:
                return True
            return False

        if isinstance(allowed, str):  # we have a string
            return check_operating_mode_inside(allowed, operating_mode)
        else: # we have something else
            for item in allowed:
                if check_operating_mode_inside(item, operating_mode):
                    return True

    def library_invoke_failure(self, failure, requested_library, hook_name):
        logger.error("Got failure during library invoke for hook ({requested_library}::{hook_name}): {failure}",
                     requested_library=requested_library,
                     hook_name=hook_name,
                     failure=failure)

    @inlineCallbacks
    def library_invoke(self, requested_library, hook_name, **kwargs):
        """
        Invokes a hook for a a given library. Passes kwargs in, returns the results to caller.
        """
        requested_library = requested_library.lower()
        if requested_library not in self.loaded_libraries:
            raise YomboWarning(f"Requested library is missing: {requested_library}")

        if "called_by" not in kwargs:
            raise YomboWarning(
                f"Unable to call hook '{requested_library}:{hook_name}', missing 'called_by' named argument.")
        calling_component = kwargs["called_by"]
        final_results = None

        for hook in [hook_name, "_yombo_universal_hook_"]:
            cache_key = requested_library + hook
            if cache_key in self._invoke_list_cache:
                if self._invoke_list_cache[cache_key] is False:
                    # logger.warn("Cache hook ({cache_key})...SKIPPED", cache_key=cache_key)
                    continue  # skip. We already know function doesn"t exist.
            library = self.loaded_libraries[requested_library]
            if requested_library == "Loader":
                return
            if not (hook.startswith("_") and hook.endswith("_")):
                hook = library._Name.lower() + "_" + hook
            kwargs["hook_name"] = hook_name
            # print("lib hook: %s -> %s" % (hook, hook_name))

            if hasattr(library, hook):
                method = getattr(library, hook)
                if isinstance(method, Callable):
                    if library._Name not in self.hook_counts:
                        self.hook_counts[library._Name] = {}
                    if hook not in self.hook_counts:
                        self.hook_counts[library._Name][hook] = {"Total Count": {"count": 0}}
                    if calling_component not in self.hook_counts[library._Name][hook]:
                        self.hook_counts[library._Name][hook][calling_component] = {"count": 0}
                    self.hook_counts[library._Name][hook][calling_component]["count"] = self.hook_counts[library._Name][hook][calling_component]["count"] + 1
                    self.hook_counts[library._Name][hook]["Total Count"]["count"] = self.hook_counts[library._Name][hook]["Total Count"]["count"] + 1
                    self._invoke_list_cache[cache_key] = True

                    try:
                        d = Deferred()
                        if hook != "_yombo_universal_hook_":
                            d.addCallback(lambda ignored: self._log_loader(
                                "debug", library._Name, "library", hook, f"About to call {hook}"))
                        # print("calling %s:%s" % (library._Name, hook))
                        d.addCallback(lambda ignored: maybeDeferred(method, **kwargs))
                        d.addErrback(self.library_invoke_failure, requested_library, hook)
                        d.callback(1)
                        if hook == "_yombo_universal_hook_":
                            yield d
                        else:
                            final_results = yield d
                    except RuntimeWarning as e:
                        pass
                else:
                    logger.debug("Cache library hook ({library}:{hook})...setting false", library=library._FullName, hook=hook)
                    logger.debug("----==(Library {library} doesn't have a callable function: {function})==-----", library=library._FullName, function=hook)
                    raise YomboWarning(f"Hook is not callable: {hook}")
            else:
    #            logger.debug("Cache hook ({library}:{hook})...setting false", library=library._FullName, hook=hook)
                self._invoke_list_cache[cache_key] = False
        return final_results

    @inlineCallbacks
    def library_invoke_all(self, hook, fullName=False, **kwargs):
        """
        Calls library_invoke for all loaded libraries.
        """
        results = {}
        to_process = {}
        if "components" in kwargs:
            to_process = kwargs["components"]
        else:
            for library_name, library in self.loaded_libraries.items():
                label = library._FullName.lower() if fullName else library._Name.lower()
                to_process[library_name] = label
        if "stoponerror" in kwargs:
            stoponerror = kwargs["stoponerror"]
        else:
            kwargs["stoponerror"] = False
            stoponerror = False

        for library_name, library in self.loaded_libraries.items():
            # logger.debug("invoke all:{libraryName} -> {hook}", libraryName=library_name, hook=hook )
            try:
                result = yield self.library_invoke(library_name, hook, **kwargs)
                if result is None:
                    continue
                results[library] = result
            except YomboWarning:
                pass
            except YomboHookStopProcessing as e:
                if stoponerror is True:
                    e.collected = results
                    e.by_who = label
                    raise

        return results

    def import_component(self, pathName, componentName, componentType, componentUUID=None):
        """
        Load component of given name. Can be a core library, or a module.
        """
        pymodulename = pathName.lower()
        self._log_loader("debug", componentName, componentType, "import", "About to import.")
        try:
            pyclassname = ReSearch("(?<=\.)([^.]+)$", pathName).group(1)
        except AttributeError:
            self._log_loader("error", componentName, componentType, "import", f"Not found. Path: {pathName}")
            logger.error("Library or Module not found: {pathName}", pathName=pathName)
            return
        try:
            module_root = __import__(pymodulename, globals(), locals(), [], 0)
        except ImportError as detail:
            self._log_loader("error", componentName, componentType, "import", f"Not found. Path: {pathName}")
            logger.error("--------==(Error: Library or Module not found)==--------")
            logger.error("----Name: {pathName},  Details: {detail}", pathName=pathName, detail=detail)
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.format_exc())
            logger.error("--------------------------------------------------------")
            raise ImportError("Cannot import module, not found.")
        except Exception as e:
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.format_exc())
            logger.error("--------------------------------------------------------")
            logger.warn("An exception of type {etype} occurred in yombo.lib.nodes:import_component. Message: {msg}",
                        etype=type(e), msg=e)
            logger.error("--------------------------------------------------------")
            raise ImportError(e)

        module_tail = reduce(lambda p1, p2: getattr(p1, p2), [module_root, ]+pymodulename.split(".")[1:])
        klass = getattr(module_tail, pyclassname)

        # Put the component into various lists for mgmt
        if not isinstance(klass, Callable):
            logger.error("Unable to start class '{classname}', it's not callable.", classname=pyclassname)
            raise ImportError(f"Unable to start class '{pyclassname}', it's not callable.")

        try:
            # Instantiate the class
            # logger.debug("Instantiate class: {pyclassname}", pyclassname=pyclassname)
            if componentType == "library":
                moduleinst = klass()  # Start the library class
                if componentName.lower() == "modules":
                    self._moduleLibrary = moduleinst
                self.loaded_components["yombo.lib." + str(componentName.lower())] = moduleinst
                self.loaded_libraries[str(componentName.lower())] = moduleinst
                # this is mostly for manhole module, but maybe useful elsewhere?
                temp = componentName.split(".")
            else:
                moduleinst = klass(self)  # Start the modules class, send the parent.
                self.loaded_components["yombo.modules." + str(componentName.lower())] = moduleinst
                return moduleinst, componentName.lower()
            # logger.debug("Instantiate class: {pyclassname}, done.", pyclassname=pyclassname)

        except YomboCritical as e:
            logger.debug("@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            logger.debug("{e}", e=e)
            logger.debug("@!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            e.exit()
            raise

    @inlineCallbacks
    def unload_libraries(self):
        """
        Only called when server is doing shutdown. Stops controller, server control and server data..
        """
        logger.debug("Stopping libraries: {stuff}", stuff=HARD_UNLOAD)
        self._run_phase = "libraries_stop"
        for name, config in HARD_UNLOAD.items():
            if self.check_operating_mode(config["operating_mode"]):
                logger.debug("stopping: {name}", name=name)
                yield self.library_invoke(name, "_stop_", called_by=self)

        self._run_phase = "libraries_unload"
        for name, config in HARD_UNLOAD.items():
            if self.check_operating_mode(config["operating_mode"]):
                logger.debug("_unload_: {name}", name=name)
                yield self.library_invoke(name, "_unload_", called_by=self)

    def _handleError(self, err):
#        logger.error("Error caught: %s", err.getErrorMessage())
#        logger.error("Error type: %s  %s", err.type, err.value)
        err.raiseException()

    def get_library(self, name):
        """ Get a library by it's name. """
        try:
            return self.loaded_libraries(name.lower())
        except KeyError:
            raise KeyError("No such library: " + str(name))


    def get_module(self, name):
        """ Get a module by it's name. """
        try:
            return self._Modules.loaded_modules(name.lower())
        except KeyError:
            raise KeyError("No such module: " + str(name))


    def get_loaded_component(self, name):
        """
        Returns loaded module object by name. Module must be loaded.
        """
        return self.loaded_components[name.lower()]

    def get_all_loaded_components(self):
        """
        Returns loaded module object by name. Module must be loaded.
        """
        return self.loaded_components

    def find_function(self, component_type, component_name, component_function):
        """
        Finds a function within the system by namme. This is useful for when you need to
        save a pointer to a callback to sql or a dictionary, but cannot save pointers to
        a function because the system may restart. This offers another method to reach
        various functions within the system.

        :param component_type: Either "module" or "library".
        :param component_name: Module or libary name.
        :param component_function: Name of the function. A string for direct access to the function or a list
            can be provided and it will search the a dictionary of items for a callback.
        :return:
        """

        if component_type == "library":
            if component_name not in self.loaded_libraries:
                logger.info("Library not found: {loaded_libraries}", loaded_libraries=self.loaded_libraries)
                raise YomboWarning("Cannot library name.")

            if isinstance(component_function, list):
                if hasattr(self.loaded_libraries[component_name], component_function[0]):
                    remote_attribute = getattr(self.loaded_libraries[component_name], component_function[0]) # the dictionary
                    if component_function[1] in remote_attribute:
                        if not isinstance(remote_attribute[component_function[1]], Callable): # the key should be callable.
                            logger.info(
                                "Could not find callable library function by name: '{component_type} :: {component_name} :: (list) {component_function}'",
                                component_type=component_type, component_name=component_name, component_function=component_function)
                            raise YomboWarning("Cannot find callable")
                        else:
                            logger.info("Look ma, I found a cool function here.")
                            return remote_attribute[component_function[1]]
            else:
                if hasattr(self.loaded_libraries[component_name], component_function):
                    method = getattr(self.loaded_libraries[component_name], component_function)
                    if not isinstance(method, Callable):
                        logger.info(
                            "Could not find callable modoule function by name: '{component_type} :: {component_name} :: {component_function}'",
                            component_type=component_type, component_name=component_name, component_function=component_function)
                        raise YomboWarning("Cannot find callable")
                    else:
                        return method
        elif component_type == "module":
            modules = self._moduleLibrary
            if component_name not in modules._modulesByName:
                raise YomboWarning("Cannot module name.")

            if hasattr(modules._modulesByName[component_name], component_function[0]):
                remote_attribute = getattr(modules._modulesByName[component_name], component_function[0])
                if component_function[1] in remote_attribute:
                    if not isinstance(remote_attribute[component_function[1]], Callable):  # the key should be callable.
                        logger.info(
                            "Could not find callable module function by name: '{component_type} :: {component_name} :: (list){component_function}'",
                            component_type=component_type, component_name=component_name,
                            component_function=component_function)
                        raise YomboWarning("Cannot find callable")
                    else:
                        logger.info("Look ma, I found a cool function here.")
                        return remote_attribute[component_function[1]]
            else:
                if hasattr(modules._modulesByName[component_name], component_function):
                    method = getattr(modules._modulesByName[component_name], component_function)
                    if not isinstance(method, Callable):
                        logger.info(
                            "Could not find callable module function by name: '{component_type} :: {component_name} :: {component_function}'",
                            component_type=component_type, component_name=component_name,
                            component_function=component_function)
                        raise YomboWarning("Cannot find callable")
                    else:
                        return method
        else:
            logger.warn("Not a valid component_type: {component_type}", component_type=component_type)
            raise YomboWarning("Invalid component_type.")


_loader = None


def setup_loader(testing=False):
    global _loader
    if not _loader:
        _loader = Loader(testing)
    return _loader


def get_loader():
    global _loader
    return _loader


def get_the_loaded_components():
    global _loader
    return _loader.get_all_loaded_components()


def get_library(name):
    global _loader
    return _loader.get_library(name)


def get_module(name):
    global _loader
    return _loader.get_module(name)


def stop_loader():
    global _loader
    if not _loader:
        return
    else:
        _loader.unload()
    return
