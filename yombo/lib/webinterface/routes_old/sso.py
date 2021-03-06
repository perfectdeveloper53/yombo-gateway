# This file was created by Yombo for use with Yombo Python Gateway automation
# software.  Details can be found at https://yombo.net
"""
This implements the "/sso" sub-route of the web interface.

SSO = Single-sign on.  Allows users to automatically login using crediential information
from my.yombo.net.

The login flow:  User visits homepage. Clicks on "login", they are redirected to my.yombo.net
for credentials. After they are logged in, they will be redirected back to this gateway. This
gateway will receive the request_id and a JWT. The JWT can be authenticated using either the
DNS ssojwt.yombo.net TEXT, or simply call the API:
POST https://api.yombo.net/gateway/{gateway_id}/check_user_token

.. warning::

   This library is not intended to be accessed by developers or users. These functions, variables,
   and classes **should not** be accessed directly by modules. These are documented here for completeness.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.24.0

:copyright: Copyright 2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://github.com/yombo/yombo-gateway/blob/master/yombo/lib/webinterface/routes/sso.py>`_
"""

import json

from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import run_first
from yombo.core.log import get_logger

logger = get_logger("library.webinterface.route.sso")


def route_sso(webapp):
    with webapp.subroute("/sso") as webapp:
        @webapp.route("/")
        def page_devices(webinterface, request, session):
            return webinterface.redirect(request, "/")

        @webapp.route("/gateway_user_login")
        @inlineCallbacks
        def page_devices_index(webinterface, request, session):
            gateway_id = webinterface.gateway_id
            if "token" not in request.args:
                print("token is required....")
                return webinterface.redirect(request, "/")
            if "request_id" not in request.args:
                print("request_id is required....")
                return webinterface.redirect(request, "/")

            token = request.args.get("token", [{}])[0]
            request_id = request.args.get("request_id", [{}])[0]
            response = webinterface._YomboAPI.request("POST", f"/v1/gateways/{gateway_id}/check_user_token)",
                                                      {
                                                          "token": token,
                                                      })

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/index.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            item_keys, permissions = webinterface._Users.get_access(session, "device", "view")
            return page.render(
                alerts=webinterface.get_alerts(),
                request=request,
                user=session.user,
                permissions=permissions,
                item_keys=item_keys,
            )

        @webapp.route("/add")
        @require_auth()
        @inlineCallbacks
        def page_devices_add_select_device_type_get(webinterface, request, session):
            session.has_access("device", "*", "add")

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/add_select_device_type.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/add", "Add Device - Select Device Type")
            device_types = yield webinterface._DeviceTypes.addable_device_types()

            return page.render(
                alerts=webinterface.get_alerts(),
                device_types=device_types,
            )

        @webapp.route("/add/<string:device_type_id>", methods=["POST", "GET"])
        @require_auth()
        @inlineCallbacks
        def page_devices_add_post(webinterface, request, session, device_type_id):
            session.has_access("device", "*", "add")

            try:
                device_type = webinterface._DeviceTypes[device_type_id]
                device_type_id = device_type.device_type_id
            except Exception as e:
                webinterface.add_alert(f"Device Type ID was not found: {device_type_id}", "warning")
                return webinterface.redirect(request, "/devices/add")

            ok_to_save = True

            if "json_output" in request.args:
                json_output = request.args.get("json_output", [{}])[0]
                json_output = json.loads(json_output)
                if "first_time" in json_output:
                    ok_to_save = False
            else:
                json_output = {}
                ok_to_save = False

            try:
                pin_required = int(json_output.get("pin_required", 0))
                if pin_required == 1:
                    if request.args.get("pin_code")[0] == "":
                        webinterface.add_alert("Device requires a pin code, but none was set.", "warning")
                        return webinterface.redirect(request, "/devices")
            except Exception as e:
                logger.warn("Processing 'pin_required': {e}", e=e)
                pin_required = 0

            try:
                start_percent = json_output.get("start_percent", None)
                energy_usage = json_output.get("energy_usage", None)
                energy_map = {}
                if start_percent is not None and energy_usage is not None:
                    for idx, percent in enumerate(start_percent):
                        try:
                            energy_map[float(float(percent) / 100)] = energy_usage[idx]
                        except:
                            pass
                else:
                    ok_to_save = False

                energy_map = sorted(list(energy_map.items()), key=lambda x_y: float(x_y[0]))
            except Exception as e:
                logger.warn("Error while processing device add_details: {e}", e=e)

            variable_data = yield webinterface._Variables.extract_variables_from_web_data(json_output.get("vars", {}))
            device = {
                "location_id": json_output.get("location_id", ""),
                "area_id": json_output.get("area_id", ""),
                "machine_label": json_output.get("machine_label", ""),
                "label": json_output.get("label", ""),
                "description": json_output.get("description", ""),
                "status": int(json_output.get("status", 1)),
                "statistic_label": json_output.get("statistic_label", ""),
                "statistic_type": json_output.get("statistic_type", "datapoint"),
                "statistic_bucket_size": json_output.get("statistic_bucket_size", ""),
                "statistic_lifetime": json_output.get("statistic_lifetime", 365),
                "device_type_id": device_type_id,
                "pin_required": pin_required,
                "pin_code": json_output.get("pin_code", ""),
                "pin_timeout": json_output.get("pin_timeout", ""),
                "energy_type": json_output.get("energy_type", ""),
                "energy_map": energy_map,
                "variable_data": variable_data,
                # "intent_allow": None,
                # "intent_text": None,
            }

            if ok_to_save:
                try:
                    results = yield webinterface._Devices.add_device(device, source="webinterface", session=session["yomboapi_session"])
                except YomboWarning as e:
                    webinterface.add_alert(f"Cannot add device, reason: {e.message}")
                    return webinterface.redirect(request, "/devices")

                if results["status"] == "success":
                    msg = {
                        "header": "Device Added",
                        "label": "Device added successfully",
                        "description": "",
                    }

                    webinterface._Notifications.add({"title": "Restart Required",
                                                     "message": 'Device added. A system <strong><a  class="confirm-restart" href="#" title="Restart Yombo Gateway">restart is required</a></strong> to take affect.',
                                                     "source": "Web Interface",
                                                     "persist": False,
                                                     "priority": "high",
                                                     "always_show": True,
                                                     "always_show_allow_clear": False,
                                                     "id": "reboot_required",
                                                     "local": True,
                                                     })

                    page = webinterface.get_template(request, webinterface.wi_dir + "/pages/misc/reboot_needed.html")
                    return page.render(alerts=webinterface.get_alerts(),
                                       msg=msg,
                                       )
                else:
                    webinterface.add_alert(f"{results['apimsghtml']}")

            device_variables = yield webinterface._Variables.get_variable_groups_fields(
                group_relation_type="device_type",
                group_relation_id=device_type_id,
            )

            if variable_data is not None:
                device_variables = yield webinterface._Variables.merge_variable_groups_fields_data_data(
                    device_variables,
                    json_output.get("vars", {})
                )


            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/add_details.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, "/devices/add", "Add Device - Details")
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               device_variables=device_variables,
                               device_type=device_type,
                               locations=webinterface._Locations.sorted(),
                               states=webinterface._States.get("#")
                               )

        @webapp.route("/<string:device_id>/details")
        @require_auth()
        @inlineCallbacks
        def page_devices_details(webinterface, request, session, device_id):
            session.has_access("device", device_id, "view")

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert(f"Device ID was not found.  {e}", "warning")
                return webinterface.redirect(request, "/devices/index")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/details.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            add_devices_breadcrumb(webinterface, request, device_id, session)
            device_variables = device.device_variables
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               device_variables=device_variables,
                               states=webinterface._States.get("#")
                               )

        @webapp.route("/<string:device_id>/delete", methods=["GET"])
        @require_auth()
        def page_device_delete_get(webinterface, request, session, device_id):
            session.has_access("device", device_id, "remove")

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert(f"Device ID was not found.  {e}", "warning")
                return webinterface.redirect(request, "/devices/index")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/delete.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, f"/devices/{device_id}/details", device.label)
            webinterface.add_breadcrumb(request, f"/devices/{device_id}/delete", "Delete")
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               states=webinterface._States.get("#")
                               )

        @webapp.route("/<string:device_id>/delete", methods=["POST"])
        @require_auth()
        @inlineCallbacks
        def page_device_delete_post(webinterface, request, session, device_id):
            session.has_access("device", device_id, "remove")

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert(f"Device ID was not found.  {e}", "warning")
                return webinterface.redirect(request, "/devices/index")
            try:
                confirm = request.args.get("confirm")[0]
            except Exception:
                confirm = None
            if confirm != "delete":
                page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/delete.html")
                webinterface.add_alert("Must enter 'delete' in the confirmation box to delete the device.", "warning")
                return page.render(alerts=webinterface.get_alerts(),
                                   device=device,
                                   states=webinterface._States.get("#")
                                   )

            device_results = yield webinterface._Devices.delete_device(device.device_id,
                                                                       session=session["yomboapi_session"])
            if device_results["status"] == "failed":
                webinterface.add_alert(device_results["apimsghtml"], "warning")
                return webinterface.redirect(request, "/devices/index")

            webinterface.add_alert("Device deleted.", "warning")
            return webinterface.redirect(request, "/devices/index")

        @webapp.route("/<string:device_id>/disable", methods=["GET"])
        @require_auth()
        def page_device_disable_get(webinterface, request, session, device_id):
            session.has_access("device", device_id, "disable")

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert(f"Device ID was not found.  {e}", "warning")
                return webinterface.redirect(request, "/devices/index")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/disable.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, f"/devices/{device_id}/details", device.label)
            webinterface.add_breadcrumb(request, f"/devices/{device_id}/disable", "Disable")
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               )

        @webapp.route("/<string:device_id>/disable", methods=["POST"])
        @require_auth()
        @inlineCallbacks
        def page_device_disable_post(webinterface, request, session, device_id):
            session.has_access("device", device_id, "disable")

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert(f"Device ID was not found.  {e}", "warning")
                return webinterface.redirect(request, "/devices/index")
            confirm = request.args.get("confirm")[0]
            if confirm != "disable":
                page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/disable.html")
                webinterface.add_alert("Must enter 'disable' in the confirmation box to disable the device.", "warning")
                return page.render(alerts=webinterface.get_alerts(),
                                   device=device,
                                   )

            device_results = yield webinterface._Devices.disable_device(device.device_id,
                                                                        session=session["yomboapi_session"])
            if device_results["status"] == "failed":
                webinterface.add_alert(device_results["apimsghtml"], "warning")
                return webinterface.redirect(request, "/devices/index")

            webinterface.add_alert("Device disabled.", "warning")
            return webinterface.redirect(request, "/devices/index")


        @webapp.route("/<string:device_id>/enable", methods=["GET"])
        @require_auth()
        def page_device_enable_get(webinterface, request, session, device_id):
            session.has_access("device", device_id, "enable")

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert(f"Device ID was not found.  {e}", "warning")
                return webinterface.redirect(request, "/devices/index")
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/enable.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, f"/devices/{device_id}/details", device.label)
            webinterface.add_breadcrumb(request, f"/devices/{device_id}/enable", "Enable")
            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               )

        @webapp.route("/<string:device_id>/enable", methods=["POST"])
        @require_auth()
        @inlineCallbacks
        def page_device_enable_post(webinterface, request, session, device_id):
            session.has_access("device", device_id, "enable")

            try:
                device = webinterface._Devices[device_id]
                device_id = device.device_id
            except Exception as e:
                webinterface.add_alert(f"Device ID was not found. {e}", "warning")
                return webinterface.redirect(request, "/devices/index")
            confirm = request.args.get("confirm")[0]
            if confirm != "enable":
                page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/enable.html")
                webinterface.add_alert("Must enter 'enable' in the confirmation box to enable the device.", "warning")
                return page.render(alerts=webinterface.get_alerts(),
                                   device=device,
                                   )

            device_results = yield webinterface._Devices.enable_device(device.device_id,
                                                                       session=session["yomboapi_session"])
            if device_results["status"] == "failed":
                webinterface.add_alert(device_results["apimsghtml"], "warning")
                return webinterface.redirect(request, "/devices/index")

            webinterface.add_alert("Device enabled.", "warning")
            return webinterface.redirect(request, f"/devices/{device_id}/details")

        @webapp.route("/<string:device_id>/edit", methods=["GET"])
        @require_auth()
        @inlineCallbacks
        def page_devices_edit_get(webinterface, request, session, device_id):
            session.has_access("device", device_id, "edit")

            try:
                device_api_results = yield webinterface._YomboAPI.request("GET", f"/v1/device/{device_id}",
                                                                          session=session["yomboapi_session"])
            except YomboWarning as e:
                webinterface.add_alert(e.html_message, "warning")
                return webinterface.redirect(request, "/devices/index")
            device = device_api_results["data"]
            device["device_id"] = device["id"]
            del device["id"]
            new_map = {}
            for key, value in device["energy_map"].items():
                new_map[float(key)] = float(value)
            device["energy_map"] = new_map

            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/devices/index", "Devices")
            webinterface.add_breadcrumb(request, f"/devices/{device_id}/details",
                                        webinterface._Locations.area_label(device["area_id"], device["label"]))
            webinterface.add_breadcrumb(request, f"/devices/{device_id}/edit", "Edit")
            variable_data = yield webinterface._Variables.get_variable_data("device", device["device_id"])
            page = yield page_devices_edit_form(
                webinterface,
                request,
                session,
                device,
                variable_data,
            )
            return page

        @webapp.route("/<string:device_id>/edit", methods=["POST"])
        @require_auth()
        @inlineCallbacks
        def page_devices_edit_post(webinterface, request, session, device_id):
            session.has_access("device", device_id, "edit")

            device = webinterface._Devices.devices[device_id]
            device_id = device.device_id

            if "json_output" in request.args:
                json_output = request.args.get("json_output", [{}])[0]
                json_output = json.loads(json_output)
                if "first_time" in json_output:
                    ok_to_save = False
            else:
                json_output = {}
                ok_to_save = False


            try:
                status = int(json_output.get("status", 0))
            except Exception as e:
                pin_required = 1

            try:
                pin_required = int(json_output.get("pin_required", 0))
                if pin_required == 1:
                    if request.args.get("pin_code")[0] == "":
                        webinterface.add_alert("Device requires a pin code, but none was set.", "warning")
                        return webinterface.redirect(request, f"/devices/{device_id}/edit")
            except Exception as e:
                logger.warn("Processing 'pin_required': {e}", e=e)
                pin_required = 0

            start_percent = request.args.get("start_percent")
            energy_usage = request.args.get("energy_usage")
            energy_map = {}
            for idx, percent in enumerate(start_percent):
                try:
                    energy_map[float(float(percent)/100)] = energy_usage[idx]
                except:
                    pass

            energy_map = sorted(list(energy_map.items()), key=lambda x_y1: float(x_y1[0]))
            json_output = json.loads(request.args.get("json_output")[0])

            # print("energy_map: %s " % energy_map)
            variable_data = yield webinterface._Variables.extract_variables_from_web_data(json_output["vars"])

            energy_tracker_source = request.args.get("energy_tracker_source")[0]
            if energy_tracker_source == "calculated":
                energy_tracker_device = None
            elif energy_tracker_source == "device":
                energy_tracker_device = request.args.get("energy_tracker_device")[0]
            elif energy_tracker_source == "state":
                energy_tracker_device = request.args.get("energy_tracker_state")[0]
            else:
                webinterface.add_alert("Invalid energy tracker source", "warning")
                return webinterface.redirect(request, f"/devices/{device_id}/edit")

            data = {
                "location_id": request.args.get("location_id")[0],
                "area_id": request.args.get("area_id")[0],
                "machine_label": request.args.get("machine_label")[0],
                # "device_type_id": request.args.get("device_type_id")[0],
                "label": request.args.get("label")[0],
                "description": request.args.get("description")[0],
                "status": status,
                "statistic_label": request.args.get("statistic_label")[0],
                "statistic_type": request.args.get("statistic_type")[0],
                "statistic_bucket_size": request.args.get("statistic_bucket_size")[0],
                "statistic_lifetime": request.args.get("statistic_lifetime")[0],
                "pin_required": pin_required,
                "pin_code": request.args.get("pin_code")[0],
                "pin_timeout": request.args.get("pin_timeout")[0],
                "energy_type": request.args.get("energy_type")[0],
                "energy_tracker_source":energy_tracker_source,
                "energy_tracker_device": energy_tracker_device,
                "energy_map": energy_map,
                "variable_data":  variable_data,
                # "intent_allow": None,
                # "intent_text": None,
            }

            try:
                results = yield webinterface._Devices.edit_device(device_id, data, session=session["yomboapi_session"])
            except YomboWarning as e:
                results = {
                    "status": "failed",
                    "apimsghtml": e,
                }

            if results["status"] == "failed":

                data["device_type_id"] = device.device_type_id
                data["device_id"] = device_id
                webinterface.add_alert(results["apimsghtml"], "warning")

                webinterface.home_breadcrumb(request)
                webinterface.add_breadcrumb(request, "/devices/index", "Devices")
                webinterface.add_breadcrumb(request, f"/devices/{device_id}/details",
                                            webinterface._Locations.area_label(device["area_id"], device["label"]))
                webinterface.add_breadcrumb(request, f"/devices/{device_id}/edit", "Edit")
                page = yield page_devices_edit_form(
                    webinterface,
                    request,
                    session,
                    data,
                    json_output["vars"]
                )
                return page

            webinterface.add_alert("Device saved.", "warning")
            return webinterface.redirect(request, f"/devices/{device_id}/details")

        @inlineCallbacks
        def page_devices_edit_form(webinterface, request, session, device, variable_data=None):
            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/edit.html")
            # device_variables = device.device_variables
            # print("device: %s" % device)
            device_variables = yield webinterface._Variables.get_variable_groups_fields(
                group_relation_type="device_type",
                group_relation_id=device["device_type_id"]
            )

            if variable_data is not None:
                device_variables = yield webinterface._Variables.merge_variable_groups_fields_data_data(
                                         device_variables,
                                         variable_data,
                                         )

            return page.render(alerts=webinterface.get_alerts(),
                               device=device,
                               device_variables=device_variables,
                               states=webinterface._States.get("#"),
                               )

        @webapp.route("/device_commands")
        @require_auth()
        def page_devices_device_commands(webinterface, request, session):
            session.has_access("device_command", "*", "view")

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/device_commands.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/info", "Info")
            webinterface.add_breadcrumb(request, "/devices/delayed_commands", "Device Commands")
            return page.render(alerts=webinterface.get_alerts(),
                               device_commands=webinterface._DeviceCommands.device_commands,
                               )

        @webapp.route("/device_commands/<string:device_command_id>/details")
        @require_auth()
        def page_devices_device_commands_details(webinterface, request, session, device_command_id):
            session.has_access("device_command", device_command_id, "view")

            page = webinterface.get_template(request, webinterface.wi_dir + "/pages/devices/device_command_details.html")
            webinterface.home_breadcrumb(request)
            webinterface.add_breadcrumb(request, "/info", "Info")
            webinterface.add_breadcrumb(request, "/devices/device_commands", "Device Commands")
            webinterface.add_breadcrumb(request, "/devices/device_commands", "Request")
            try:
                device_command = webinterface._DeviceCommands.device_commands[device_command_id]
            except Exception as e:
                webinterface.add_alert(f"Cannot find requested id. <br>Error details: {e}")
                return webinterface.redirect(request, "/devices/device_commands")
            return page.render(alerts=webinterface.get_alerts(),
                               device_command=device_command,
                               )
