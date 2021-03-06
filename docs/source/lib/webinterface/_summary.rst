.. index:: webinterface_summary

.. _webinterface_summary:

.. currentmodule:: yombo.lib.webinterface


=======================================
WebInterface (yombo.lib.webinterface)
=======================================

Provides web interface to the Yombo Gateway. Useful for setting up the gateway and
interacting with th Yombo API.

The web interface is broken down into several modules. See below for the core module functions.

See the `Web Interface library documentation <https://yombo.net/docs/libraries/web_interface>`_ for more
details.

Web Interface Library
=========================

Primary webinterface library files.

.. toctree::
   :maxdepth: 1

   __init__.rst
   class_helpers/builddist.rst
   class_helpers/errorhandler.rst
   class_helpers/render.rst
   class_helpers/webserver.rst

Routes
=======

Route files handle various URLs for the Web Interface library. Currently, the
documentation system is unable to automatically generate easily viewable
documentation. Please view the
`source code for the routes <https://github.com/yombo/yombo-gateway/tree/master/yombo/lib/webinterface/routes>`_ .

Web Interface HTML
==================

The HTML pages displayed can be viewed from the git repository:
`HTML Pages <https://github.com/yombo/yombo-gateway/tree/master/yombo/lib/webinterface/pages>`_ .

Helper Files
============

.. toctree::
   :maxdepth: 1

   auth.rst
   constants.rst

Last updated: |today|
