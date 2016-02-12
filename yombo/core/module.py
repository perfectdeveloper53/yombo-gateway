# cython: embedsignature=True
#This file was created by Yombo for use with Yombo Python Gateway automation
#software.  Details can be found at https://yombo.net
"""
A shell for module developers to get basic items configured for modules.

All modules should extend this module.  See the class documentation for
additional details.

Modules have 3 phases of startup: _init, _load, _start.
    - Init - Get the basics of the module running.  All libraries are
      loaded and available.  Not all modules have been through init
      this stage.  A deferred can be returned if the :ref:`Loader`
      should wait until the module has completed it's init phase.
    - Load - All modules have completed init phase.  Now it's time to get the
      module ready to receive messages. By the time Load() finishes, the
      module should be able to receive messages - even if it queue for later.
      A deferred can be returned if the :ref:`Loader`
      should wait until the module has completed it's load phase.
      A _preload_ function exists and will be called before _load_.
    - Start - The module should already be running by now. The module can
      now start sending messages to other components for processing.
      A _prestart_ function exists and will be called before _start_.

.. warning::

   It's highly suggested to **NOT** use the __init__ function for your module's
   class. If you *must* use the __init__ function, be sure to call the parent
   __init__ function before any actions take place within your local __init__.

Modules have 2 phases of shutdown: _stop, _unload
    - Stop - The gateway is on the first phase of shutting down. The module
      should no longer send messages.  It can still receive them after this
      function ends.
    - Unload - This module should stop everything, close connections, close
      files, save any work. The module will no longer receive any messages
      during this phase of shutdown.

**Hooks**

Yombo's module system also implements a concept of "hooks". A hook is a
python function that is can be called from other libraries or modules.

See :ref:`Hooks <hooks>` for details on usage and examples.

**Usage**:

.. code-block:: python

   from yombo.core.module import YomboModule
   class ExampleModule(YomboModule):
       def _init_(self):
           self._ModDescription = "Insteon API command interface"
           self._ModAuthor = "Mitch Schwenk @ Yombo"
           self._ModUrl = "https://yombo.net/SomeUrlForDetailsAboutThisModule"
       def _load_(self):
           pass    #do stuff on loading of the module.
                   #modules can't send messages at this point, but after load completes
                   #it should be able to receive messages for processing.
        def _start_(self):
            pass    #do stuff when module can now send and receive messages.
        def _stop_(self):
            pass    # the first phase of module gateway shut down. Should no longer
                    # send messages to other modules/components like normal run time
                    # but can still technically do so if desired while inside this
                    # call.  After this function completes, should no longer send
                    # messages, but is required to continue to process messages
                    # until the unload() function is called.
        def _unload_(self):
            pass    #the gateway is on final phase of shutdown. Must quit now!
        def ExampleModule_message_subscriptions(self, **kwargs):
           return ['cmd'] # register to get all CMD messages.
        def ExampleModule_voicecmds(self, **kwargs):
           return [ {'voiceCmd': "homevision [reset]", 'order' : 'nounverb'} ] # register new voice commands
        def message(self, message):
            pass    #process an incoming message.

The module can register to any distribution that is a valid message type as
well "all" to receive all message types. See
*msgType* details in the :py:meth:`yombo.core.message.Message.__init__`
documentation.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
:copyright: Copyright 2012-2016 by Yombo.
:license: LICENSE for details.
"""
# Import Yombo libraries
#from yombo.core.component import IModule
from yombo.core.helpers import getCommands, getCronTab
from yombo.core.fuzzysearch import FuzzySearch
from yombo.core.exceptions import YomboWarning
from yombo.core.log import getLogger

logger = getLogger('core.module')

class YomboModule:
    """
    Setups a module to assist the developer write modules quickly. Pre-defines several items.

    :cvar _Name: (string) Name of the class (aka module name). EG: x10api
    :cvar _FullName: (string) Name **full** of the class for routing. EG: yombo.modules.x10api
    :cvar _Description: (string) Description, needs to be set in the module's init() function.
    :cvar _ModAuthor: (string) Module author, needs to be set in the module's init() function.
    :cvar _ModUrl: (string) URL for additional information about this
      module, needs to be set in the module's init() function.
    :cvar _Atoms: (object/dict) The Yombo Atoms library, but can accessed as a dictionary or object.
    :cvar _Commands: preloaded pointer to all configured commands.
    :cvar _Devices: (dict) Dictionary to all devices this module controls.
    :cvar _DevicesByType: (callback) A function to quickly get all devices for a specific device type.
    :cvar _DeviceTypes: (list) List of device types that are registered for this module.
    :cvar _DevicesLibrary: preloaded pointer to Devices library.
    :cvar _Libraries: (dict) A dictionary of all modules. Returns pointers.
    :cvar _Modules: (object/dict) The Modules Library, can be access as dictionary or object. Returns a pointer.
    :cvar _ModuleType: (string) Type of module (Interface, Command, Logic, Other).
    :cvar _ModuleUUID: (string) The UUID of the module.
    :cvar _ModuleVariables: (dict) Dictionary of the module level variables as defined online
      and set as per the user.
    :cvar _States: (object/dict) The Yombo States library, but can accessed as a dictionary or object.
    """
    def __init__(self):
        """
        Setup basic class items. See variables list for specific information
        variable information.
        """
        self._Name = self.__class__.__name__
        self._FullName = "yombo.gateway.modules.%s" % (self.__class__.__name__)
        self._ModDescription = "NA"
        self._ModAuthor = "NA"
        self._ModURL = "NA"
        self._ModuleType = None
        self._ModuleUUID = None

        self._Commands = getCommands()

        self._Devices = None
        self._DeviceTypes = None
        self._DevicesLibrary = None
        self._DevicesByType = None  # A callable (function)

        self._ModuleVariables = None
        self._ModulesLibrary = None

    def dump(self):
        return self.__str__()
    def __str__(self):
        return {
            '_Name': self._Name,
            '_FullName': self._FullName,
            '_ModDescription': self._ModDescription,
            '_ModAuthor': self._ModAuthor,
            '_ModuleType': self._ModuleType,
            '_ModuleUUID': self._ModuleUUID,

        }

    def _init_(self):
        """
        Phase 1 of 3 for statup - configure basic variables, etc. Like __init__.
        """
        raise NotImplementedError()

    def _load_(self):
        """
        Phase 2 of 3 for statup - Called when module should load anything else. After this
        function completes, it should be able to accept and process messages. Doesn't send
        messages at this stage.
        """
        pass

    def _start_(self):
        """
        Phase 3 of 3 for statup - Called when this module should start processing and is
        now able to send messages to other components.
        """
        pass

    def _stop_(self):
        """
        Phase 1 of 2 for shutdown - Stop sending messages, but can still accept incomming
        messages for processing.
        """
        pass

    def _unload_(self):
        """
        Phase 2 of 2 for shutdown - By the time this is called, no messages will be sent
        to this module. Close all connections/items. Once this function ends, it's
        possible that the process will terminate.
        """
        pass

    def message(self, message):
        """
        Incoming messeages from other components (internal and external to the gateway) will
        be sent to this method.
        """
        pass