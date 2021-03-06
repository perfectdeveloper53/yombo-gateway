# Import python libraries
from time import time

from twisted.internet.defer import inlineCallbacks

from yombo.core.exceptions import YomboWarning
from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_good, return_not_found, return_error, args_to_dict
from yombo.utils import sleep


def route_api_v1_device(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/device", methods=["GET"])
        @require_auth(api=True)
        def apiv1_device_get(webinterface, request, session):
            session.has_access("device", "*", "view", raise_error=True)
            return webinterface.render_api(request, None,
                                           data_type="devices",
                                           attributes=webinterface._Devices.class_storage_as_list()
                                           )

        @webapp.route("/device/<string:device_id>", methods=["GET"])
        @require_auth(api=True)
        def apiv1_device_details_get(webinterface, request, session, device_id):
            session.has_access("device", device_id, "view", raise_error=True)
            arguments = args_to_dict(request.args)
            if len(device_id) > 200 or isinstance(device_id, str) is False:
                return return_error(request, "invalid device_id format", 400)

            if device_id in webinterface._Devices:
                device = webinterface._Devices[device_id]
            else:
                return return_not_found(request, "Device not found")

            payload = device.asdict()
            if "item" in arguments:
                payload = payload[arguments["item"]]
            return return_good(
                request,
                payload=payload
            )

        @webapp.route("/device/<string:device_id>/command/<string:command_id>", methods=["GET", "POST"])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_device_command_get_post(webinterface, request, session, device_id, command_id):
            session.has_access("device", device_id, "control", raise_error=True)
            if len(device_id) > 200 or isinstance(device_id, str) is False:
                return return_error(request, "invalid device_id format", 400)
            if len(command_id) > 200 or isinstance(command_id, str) is False:
                return return_error(request, "invalid command_id format", 400)

            try:
                wait_time = float(request.args.get("_wait")[0])
            except:
                wait_time = 2

            arguments = args_to_dict(request.args)

            pin_code = arguments.get("pin_code", None)
            delay = arguments.get("delay", None)
            max_delay = arguments.get("max_delay", None)
            not_before = arguments.get("not_before", None)
            not_after = arguments.get("not_after", None)
            inputs = arguments.get("inputs", None)
            if device_id in webinterface._Devices:
                device = webinterface._Devices[device_id]
            else:
                return return_not_found(request, "Device not found")
            try:
                device_command_id = device.command(
                    cmd=command_id,
                    auth=session,
                    pin=pin_code,
                    delay=delay,
                    max_delay=max_delay,
                    not_before=not_before,
                    not_after=not_after,
                    inputs=inputs,
                    idempotence=request.idempotence,
                )
            except KeyError as e:
                print(f"error with apiv1_device_command_get_post keyerror: {e}")
                return return_not_found(request, f"Error with command, it is not found: {e}")
            except YomboWarning as e:
                print(f"error with apiv1_device_command_get_post warning: {e}")
                return return_error(request, f"Error with command: {e}")

            DC = webinterface._DeviceCommands.device_commands[device_command_id]
            if wait_time > 0:
                exit_while = False
                start_time = time()
                while(start_time > (time() - wait_time) and exit_while is False):
                    yield sleep(.075)
                    if DC.status_id >= 100:
                        exit_while = True
            if len(device.status_history) > 0:
                status_current = device.status_history[0].asdict()
            else:
                status_current = None

            if len(device.status_history) > 1:
                status_previous = device.status_history[1].asdict()
            else:
                status_previous = None

            return return_good(
                request,
                payload={
                    "device_command_id": device_command_id,
                    "device_command": DC.asdict(),
                    "status_current": status_current,
                    "status_previous": status_previous,

                }
            )
