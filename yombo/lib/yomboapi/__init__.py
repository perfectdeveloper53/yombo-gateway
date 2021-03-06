#This file was created by Yombo for use with Yombo Python gateway automation
#software.  Details can be found at http://yombo.net
"""

.. note::

  * For library documentation, see: `YomboAPI @ Library Documentation <https://yombo.net/docs/libraries/yomboapi>`_


Manages interactions with api.yombo.net

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>
.. versionadded:: 0.11.0

:copyright: Copyright 2016-2019 by Yombo.
:license: LICENSE for details.
:view-source: `View Source Code <https://yombo.net/Docs/gateway/html/current/_modules/yombo/lib/yomboapi.html>`_
"""
# Import python libraries
import traceback

# Import twisted libraries
from twisted.internet.defer import inlineCallbacks

# Import Yombo libraries
from yombo.constants import VERSION
from yombo.core.exceptions import YomboWarning, YomboAPICredentials
from yombo.core.library import YomboLibrary
from yombo.core.log import get_logger

from .generic import YA_Commands
logger = get_logger("library.yomboapi")


class YomboAPI(YomboLibrary, YA_Commands):
    @inlineCallbacks
    def _init_(self, **kwargs):
        self.my_gateway_id = self._Configs.get2("core", "gwid", None, False)
        self.gateway_hash = self._Configs.get2("core", "gwhash", None, False)

        self.api_app_key = self._Configs.get("yomboapi", "api_app_key", "4Pz5CwKQCsexQaeUvhJnWAFO6TRa9SafnpAQfAApqy9fsdHTLXZ762yCZOct", False)
        self.base_url = self._Configs.get("yomboapi", "baseurl", "https://api.yombo.net/api", False)
        self.gateway_credentials_is_valid = False
        yield self._check_gateway_credentials()

    @inlineCallbacks
    def _check_gateway_credentials(self):
        """
        Talks to the Yombo API and validates the current gateway ID / Gateway Hash (password) and
        the API Auth Key is valid. Sometimes a new API auth key is returned during this check, it
        should be saved for future calls.

        :return:
        """
        logger.debug(f"About to validate gateway credentials")
        gateway_id = self.my_gateway_id()
        gateway_hash = self.gateway_hash()

        if gateway_id == "local" or gateway_hash is None:
            self.gateway_credentials_is_valid = False
            return

        try:
            logger.debug(f"Now doing credential check....")
            response = yield self.request("POST", f"/v1/gateways/{gateway_id}/check_authentication",
                                          {
                                            "hash": gateway_hash,
                                          },
                                          authorization_header="None",
                                          )
        except YomboWarning as e:
            logger.warn("Unable to validate gateway credentials: {message}", message=e.message)
            if e.errorno in (400, 404):
                self._Configs.set("core", "gwid", "local")

            self.gateway_credentials_is_valid = False
            return

        except Exception as e:
            logger.info("check_gateway_credentials API Error: {error}", error=e)
            logger.error("---------------==(Traceback)==--------------------------")
            logger.error("{trace}", trace=traceback.format_exc())
            logger.error("--------------------------------------------------------")
            logger.warn("An exception of type {etype} occurred in yombo.lib.yomboapi:import_component. Message: {msg}",
                        etype=type(e), msg=e)
            logger.error("--------------------------------------------------------")
            self.gateway_credentials_is_valid = False
        else:
            data = response.content["data"]
            self.gateway_credentials_is_valid = data["attributes"]["hash_valid"]
            # print(f"api_auth_valid 222: gateway credentals: {self.gateway_credentials_is_valid}")

    @inlineCallbacks
    def validate_user_token(self, user_token):
        gateway_id = self.my_gateway_id()
        try:
            response = yield self.request("POST", f"/v1/gateways/{gateway_id}/check_authentication",
                                          {
                                              "token": user_token,
                                          },
                                          )
        except Exception as e:
            logger.debug("validate_login_key API Errror: {error}", error=e)
            raise YomboWarning(f"Invalid API response: {e}", response.response_code, "validate_user_token", "yomboapi")
        else:
            return response.content["data"]
            return data["attributes"]["hash_valid"]

    @inlineCallbacks
    def request(self, method, url, request_data=None, headers={}, authorization_header=None):
        if "page[size]" not in url or "page%5Bsize%5D" not in url:
            if "?" in url:
                url += "&"
            else:
                url += "?"
            url += "page[size]=500"
        logger.debug("yomboapi request: {url}", url=url)
        request = ApiRequest(self, method, url, request_data, headers, authorization_header)
        logger.debug("headers: {headers}", headers=request.headers)
        logger.debug("yombo api request request_data: {request_data}", request_data=request_data)
        response = yield request.request()

        self._check_results(response, method, url, request_data)
        return response

    def _check_results(self, response, method, url, request_data):
        if response.content_type == "string":
            logger.warn("-----==( Error: API received an invalid response, got a string back )==----")
            logger.warn("Request: {request}", request=response.request.__dict__)
            logger.warn("URL: {method} {uri}", method=response.request.method, uri=response.request.uri)
            logger.warn("Header: {request_headers}", request_headers=response.request.headers)
            logger.warn("Request Data: {request_data}", request_data=request_data)
            logger.warn("Response Headers: {headers}", headers=response.headers)
            logger.warn("Content: {content}", content=response.content)
            logger.warn("--------------------------------------------------------")
        elif response.response_code >= 300:
            logger.warn("-----==( Error: API received an invalid response )==----")
            logger.warn("Request: {request}", request=response.request.__dict__)
            logger.warn("Code: {code}", code=response.response_code)
            logger.warn("URL: {method} {uri}", method=response.request.method, uri=response.request.uri)
            logger.warn("Header: {request_headers}", request_headers=response.request.headers)
            logger.warn("Request Data: {request_data}", request_data=request_data)
            logger.warn("Response Headers: {headers}", headers=response.headers)
            logger.warn("Content: {content}", content=response.content)
            logger.warn("--------------------------------------------------------")
            message = ""
            logger.warn("Error with API request: {method} {url}", method=method, url=url)
            if "errors" in response.content:
                errors = response.content["errors"]
                for error in errors:
                    if len(message) == 0:
                        message += ", "
                    message += f"{message}  {error['title']} - {error['detail']}"
                    raise YomboWarning(response.content["errors"], response.response_code, "update_results",
                                       "yomboapi", meta=response)
            else:
                message = f"{response.response_code} - {response.response_phrase}"
            raise YomboWarning(message, response.response_code, "update_results", "yomboapi", meta=response)


class ApiRequest:
    """
    Used to create requests from the API.
    """
    def __init__(self, parent, method="GET", url="", request_data=None, headers={}, authorization_header=None):
        self._Parent = parent
        self.api_app_key = self._Parent.api_app_key
        self.base_url = self._Parent.base_url
        self.user_agent = f"yombo-gateway-{VERSION}"

        self.method = method
        if url.startswith("/"):
            self.url = self. base_url + url
        else:
            self.url = url
        self.request_data = request_data
        self.timeout = 30
        self.extra_headers = headers

        self._my_headers = {
            "Accept": "application/json",
            "X-Api-Key": self.api_app_key,
            "Content-Type": "application/json",
        }

        self._authorization_header = self.check_authorization_header(authorization_header)
        self.requested_headers = None

    @property
    def headers(self):
        """ Merge my headers with requested headers"""
        if self._authorization_header is not None:
            return {**self.extra_headers, **self._my_headers, **self._authorization_header}
        else:
            return {**self.extra_headers, **self._my_headers}

        # return {**self.extra_headers, **self._my_headers, **self.authorization_header()}

    def check_authorization_header(self, incoming):
        # print("checking auth header 1")
        if incoming is None or incoming == "":
            # print("checking auth header 2")
            if self._Parent.gateway_credentials_is_valid is False:
                return None
            return {"Authorization": f"YomboGateway {self._Parent.my_gateway_id()} {self._Parent.gateway_hash()}"}
        else:
            return {"Authorization": incoming}

    @inlineCallbacks
    def request(self):
        # print("request::request 1")
        self.requested_headers = self.headers
        # print(f"method: {self.method}  url: {self.url}, headers: {self.requested_headers}, data: {self.request_data}, timeout={self.timeout}")
        response = yield self._Parent._Requests.request(self.method, self.url, headers=self.requested_headers,
                                                        json=self.request_data, timeout=self.timeout)
        # print(f"request::request 3 - {self.url}")
        return response

