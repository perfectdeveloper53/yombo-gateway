"""
Handles calls to view the system atoms. Atoms cannot be changed.
"""
# Import Yombo libraries
from yombo.lib.webinterface.auth import require_auth


def route_api_v1_atoms(webapp):
    with webapp.subroute("/api/v1") as webapp:

        @webapp.route("/atoms", methods=["GET"])
        @require_auth(api=True)
        def apiv1_atoms_get(webinterface, request, session):
            """ Gets the system atoms. """
            return webinterface.render_api(request, None,
                                           data_type="atoms",
                                           attributes=webinterface._Atoms.class_storage_as_list()
                                           )
