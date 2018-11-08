# Import python libraries

# Import 3rd-party libs

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.core.exceptions import YomboWarning
from yombo.core.log import get_logger
from yombo.utils import data_pickle, data_unpickle
from yombo.utils.datatypes import coerce_value

from yombo.lib.localdb import Sessions
logger = get_logger("library.localdb.websessions")


class DB_Websessions(object):
    @inlineCallbacks
    def get_web_session(self, session_id=None):
        def parse_record(data):
            save_data = data_unpickle(data.auth_data)
            return {
                "id": data.id,
                "enabled": coerce_value(data.enabled, "bool"),
                "user_id": data.user_id,
                "auth_at": save_data.get("auth_at", 0),
                "auth_pin": save_data.get("auth_pin", False),
                "auth_pin_at": save_data.get("auth_pin_at", 0),
                "created_by": save_data.get("created_by", "unknown"),
                "gateway_id": data.gateway_id,
                "auth_data": save_data.get("auth_data", {}),
                "created_at": data.created_at,
                "last_access_at": data.last_access_at,
                "updated_at": data.updated_at,
            }
        if session_id is None:
            records = yield Sessions.all()
            output = []
            for record in records:
                output.append(parse_record(record))
            return output
        else:
            record = yield Sessions.find(session_id)
            if record is None:
                raise YomboWarning(f"Session not found in deep storage: {session_id}", errorno=23231)
            return parse_record(record)

    @inlineCallbacks
    def save_web_session(self, session):
        logger.debug("save_web_session: session.auth_id: {auth_id}", auth_id=session._auth_id)
        save_data = data_pickle({
            "auth_data": session.auth_data,
            "auth_at": session.auth_at,
            "auth_pin": session.auth_pin,
            "auth_pin_at": session.auth_pin_at,
            "created_by": session.created_by,
        })

        args = {
            "id": session._auth_id,
            "enabled": coerce_value(session.enabled, "int"),
            "gateway_id": session.gateway_id,
            "auth_data": save_data,
            "user_id": session.user_id,
            "created_at": session.created_at,
            "last_access_at": session.last_access_at,
            "updated_at": session.updated_at,
        }
        yield self.dbconfig.insert("webinterface_sessions", args, None, "OR IGNORE")

    @inlineCallbacks
    def update_web_session(self, session):
        logger.debug("update_web_session: session.auth_id: {auth_id}", auth_id=session._auth_id)
        save_data = data_pickle({
            "auth_data": session.auth_data,
            "auth_type": session.auth_type,
            "auth_at": session.auth_at,
            "auth_pin": session.auth_pin,
            "auth_pin_at": session.auth_pin_at,
            "created_by": session.created_by,
        })
        args = {
            "enabled": coerce_value(session.enabled, "int"),
            "auth_data": save_data,
            "user_id": session.user_id,
            "last_access_at": session.last_access_at,
            "updated_at": session.updated_at,
            }
        yield self.dbconfig.update("webinterface_sessions", args, where=["id = ?", session._auth_id])

    @inlineCallbacks
    def delete_web_session(self, session_id):
        yield self.dbconfig.delete("webinterface_sessions", where=["id = ?", session_id])
