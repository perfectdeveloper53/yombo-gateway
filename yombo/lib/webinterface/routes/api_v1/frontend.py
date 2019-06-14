# Import python libraries
import json

from yombo.lib.webinterface.auth import require_auth
from yombo.constants import CONTENT_TYPE_JSON


def route_api_v1_frontend(webapp):
    with webapp.subroute("/api/v1/frontend") as webapp:

        @webapp.route("/navbar_items", methods=["GET"])
        @require_auth(api=True)
        def apiv1_frontend_navbar_items_get(webinterface, request, session):
            # session.has_access("gateway", "*", "view", raise_error=True)
            request.setHeader("Content-Type", CONTENT_TYPE_JSON)
            return json.dumps(webinterface.dashboard_sidebar_navigation())