=============================
Software Framework Components
=============================

The Yombo Gateway is a framework that allows users to quickly develop
modules to implement automation of various devices around the home, office,
and anything in between.

Navigating the framework
===========================

The gateway framework is split into a few directories:

 * :ref:`framework_ext` - 3rd party extensions.
 * :ref:`framework_constants` - Used to keep various attributes consistent across the Yombo Gateway framework.
 * :ref:`framework_core` - Basic functions used by various libraries.
 * :ref:`framework_lib` - Libraries provide all the services and tools to manage the system, including sending
   :doc:`commands <../lib/commands>` to :doc:`devices <../lib/devices/devices>`.
 * :ref:`framework_modules` - Extend the features of the Yombo gateway and are located in the modules folder.
 * :ref:`framework_utils` - Various utilities for getting things done.

.. _framework_core:

Core
=====

Core modules are the base Yombo Gateway API functions. They provide the base
features to be used by libraries and modules.

.. toctree::
   :maxdepth: 1

   ../core/exceptions.rst
   ../core/gwservice.rst
   ../core/library.rst
   ../core/log.rst
   ../core/module.rst

.. _framework_lib:

Lib
=====

Libraries build on the core modules and functions and provide essential
gateway services, such as routing commands from devices, talking to other
IoT devices, etc.

.. toctree::
   :maxdepth: 1

   ../lib/amqp.rst
   ../lib/amqpyombo.rst
   ../lib/amqpyombo_handlers/amqpyombo_handlers.rst
   ../lib/authkey.rst
   ../lib/atoms.rst
   ../lib/automation.rst
   ../lib/cache.rst
   ../lib/commands.rst
   ../lib/configuration.rst
   ../lib/crontab.rst
   ../lib/devices/devices.rst
   ../lib/devicetypes.rst
   ../lib/downloadmodules.rst
   ../lib/discovery.rst
   ../lib/gateways.rst
   ../lib/gateway_communications.rst
   ../lib/gpg.rst
   ../lib/inputtypes/inputtypes.rst
   ../lib/hash.rst
   ../lib/hashids.rst
   ../lib/loader.rst
   ../lib/localdb.rst
   ../lib/localize.rst
   ../lib/locations.rst
   ../lib/modules.rst
   ../lib/mqtt.rst
   ../lib/nodes.rst
   ../lib/notifications.rst
   ../lib/queue.rst
   ../lib/scenes.rst
   ../lib/sqldict.rst
   ../lib/sslcerts/sslcerts.rst
   ../lib/startup.rst
   ../lib/states.rst
   ../lib/statistics/statistics.rst
   ../lib/tasks.rst
   ../lib/times.rst
   ../lib/validate.rst
   ../lib/variables.rst
   ../lib/voicecmds.rst
   ../lib/webinterface/webinterface.rst
   ../lib/websessions.rst
   ../lib/yomboapi.rst

.. _framework_constants:

Constants
=========

Easily reference the same values across the Yombo Gateway framework.

.. toctree::
   :maxdepth: 1

   ../constants/constants.rst

.. _framework_modules:

Modules
=======

System modules, user modules, and downloaded modules go into the modules folder. These extend
the capabilites of the gateway and provide the gateway the ability to communicate with
various devices over various protocols.

For a list of modules available to be installed by end users: `Available Modules <https://yg2.in/f_gdoc_modules>`_

.. _framework_utils:

Utils
=====

Various utilities to help the Yombo Gateway get things done.

.. toctree::
   :maxdepth: 1

   ../utils/decorators.rst
   ../utils/dictobject.rst
   ../utils/filereader.rst
   ../utils/fuzzysearch.rst
   ../utils/lookupdict.rst
   ../utils/maxdict.rst
   ../utils/utils.rst

.. _framework_ext:

Ext
===

This directory contains external modules that ship with Yombo to support
the framework features. They are governed under their respective
licenses. See the COPYING file included with this distribution for more
information.

.. toctree::
   :maxdepth: 1

   ../ext/bermiinflector.rst
   ../ext/expiringdict.rst
   ../ext/hashids.rst
   ../ext/mqtt.rst
   ../ext/twistar.rst
   ../ext/totp.rst
   ../ext/txrdq.rst
   ../ext/validators.rst

Last updated: |today|
