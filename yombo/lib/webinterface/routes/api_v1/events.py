# Import python libraries
import re

from twisted.internet.defer import inlineCallbacks

from yombo.lib.webinterface.auth import require_auth
from yombo.lib.webinterface.routes.api_v1.__init__ import return_json

def route_api_v1_events(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/events/<string:event_type>/<string:event_subtype>", methods=["GET"])
        @require_auth(api=True)
        @inlineCallbacks
        def apiv1_events_get(webinterface, request, session, event_type, event_subtype):
            session.has_access("events", "*", "view", raise_error=True)
            args = request.args

            try:
                draw = int(args["draw"][0])
                start = int(args["start"][0])
                length = int(args["length"][0])
                order_column_number = int(args["order[0][column]"][0])
                search_string = str(args["search[value]"][0])
                col_name = f"columns[{order_column_number}][data]"
                order_column_name = str(args[col_name][0])
            except:
                return return_json(request, {}, 500)

            order_direction = args["order[0][dir]"][0]
            if order_direction.lower() not in ("asc", "desc"):
                return return_json(request, {}, 500)

            if re.match("^[ \w-]+$", search_string) is None:
                search_string = ""

            data, total_count, filtered_count = yield webinterface._LocalDB.search_events_for_datatables(
                event_type, event_subtype, order_column_name, order_direction, start,
                length, search_string)

            response = {
                "draw": draw,
                "recordsTotal": total_count,
                "recordsFiltered": filtered_count,
                "data": data,
            }

            return return_json(request, response)
