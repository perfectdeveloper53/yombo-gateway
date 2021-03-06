"""
Various utilities used to perform common functions to help speed development.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2018 by Yombo.
:license: See LICENSE for details.
"""
# Import python libraries
try:
    import fcntl
    HAS_FCNTL = True
except ImportError:
    # fcntl is not available on windows
    HAS_FCNTL = False

import base64
from difflib import SequenceMatcher
from docutils.core import publish_parts
import errno
from hashlib import sha256, sha224
import importlib
import inspect
import itertools
import jinja2
import json
import markdown
import math
import msgpack
import os
from packaging.requirements import Requirement as pkg_requirement
import pkg_resources
import random
import re
import shutil
import string
import socket
from subprocess import check_output, CalledProcessError
import sys
from time import time
import treq
import textwrap
from urllib.parse import urlparse
import zlib

from twisted.internet import reactor, threads
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import deferLater

# Import 3rd-party libs
from yombo.ext.hashids import Hashids
import yombo.ext.magic as magicfile

# Import Yombo libraries
from yombo.core.entity import Entity
from yombo.core.exceptions import YomboWarning
from yombo.core.library import YomboLibrary
from yombo.core.module import YomboModule
from yombo.utils.decorators import cached, memoize_
import yombo.ext.base62 as base62

logger = None  # This is set by the set_twisted_logger function.
_Yombo = None  # Set by setup_yombo_references()

magicparse = magicfile.Magic(mime_encoding=True, mime=True)

@inlineCallbacks
def test_url_listening(url):
    """
    Tries to check if a server is listening at the URL. Returns True/False, or YomboWarning if port number was
    not provided. In the URL.

    :param url:
    :return:
    """
    parts = urlparse(url)
    scheme = parts.scheme
    host = parts.netloc
    if scheme is None or host is None:
        raise SyntaxWarning("Invalid URL format.")

    port = parts.port
    if port is None:  # Try to guess port number
        if scheme == "ftp":
            port = 21
        elif scheme == "ssh":
            port = 22
        elif scheme == "telnet":
            port = 23
        elif scheme == "smtp":
            port = 25
        elif scheme == "tfpt":
            port = 69
        elif scheme == "http":
            port = 80
        elif scheme == "https":
            port = 443

    if port is None:
        raise YomboWarning("Port number not found.")
    results = yield test_port_listening(host, port)
    return results


@inlineCallbacks
def test_port_listening(host, port):
    """
    Returns a deferred whose result will be True/False.

    Tests if port is open on the host.

    :param host:
    :param port:
    :return:
    """
    results = yield threads.deferToThread(host, port)
    return results


def _test_port_listening(host, port):
    """
    Should only be called by it's parent 'test_port_listening' due to blocking.
    :return:
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    logger.debug("# Test non ssl host - port: {host} - {port}", host=host, port=port)
    return sock.connect_ex((host, port)) == 0


def download_file(url, destination_filename):
    """
    Returns a deferred!

    This downloads a file from a URL and saves it toa  file.
    :param url:
    :param destination_filename:
    :return:
    """
    destination = open(destination_filename, 'wb')
    d = treq.get(url, unbuffered=True)
    d.addCallback(treq.collect, destination.write)
    d.addBoth(lambda _: destination.close())
    return d


def search_for_executable(executable):
    """
    Searches the user's path for an executable.

    This is blocking, this should be called in a thread using threads.deferToThread()

    :param executable: string - Name of program to find.
    :return: string - path and file
    """
    path = os.environ['PATH']
    paths = path.split(os.pathsep)
    for p in paths:
        f = os.path.join(p, executable)
        if os.path.isfile(f):
            return f
    return None


def setup_yombo_references(loader):
    """
    Setup global references to Yombo libraries. This is called by loader::import_libraries()

    :param loader: Pointer to the loader instance.
    :return:
    """
    global _Yombo
    _Yombo = Entity(loader)


def generate_source_string(gateway_id=None, offset=None):
    """
    Gets the python file, class, and method that was called. For example, if this was
    called from yombo.lib.amqp within the class "AMQP" in the function new, the results
    would look like: "F:yombo.lib.amqp C:AMQP Md:new"

    If this wasn't called from within a class, it would look like:
    "F:yombo.core.soemthing M:washere"

    If gateway_id is supplied, it will now look like:
    "G:zbc1230 F:yombo.lib.amqp C:AMQP M:new"

    The offset is used to determine how far back in the call stack it should look. For example,
    if this function was called within yombo.lib.module.somemodule and want to get the method
    that directly called it, use offset "1".  If the previous caller is desired, use 2, etc.

    :param gateway_id:
    :param offset:
    :return:
    """
    if offset is None:
        offset = 1

    offset = offset + 1
    callingframe = sys._getframe(offset)
    mod = inspect.getmodule(callingframe)
    if "self" in callingframe.f_locals:
        results = f"F:{mod.__name__} C:{callingframe.f_locals['self'].__class__.__name__} " \
                  f"M:{callingframe.f_code.co_name}"
    else:
        results = f"F:{mod.__name__} M:{callingframe.f_code.co_name}"

    if gateway_id is not None:
        return f"G:{gateway_id} {results}"
    return results


def get_yombo_instance_type(value):
    """
    Determine what type of Yombo instance is being since, it's it name.

    :param value: An instance of some sort. Returns False if it's not a Yombo instance.
    :return:
    """
    if isinstance(value, YomboLibrary):
        return "library", value._FullName
    elif isinstance(value, YomboModule):
        return "module", value._FullName
    elif isinstance(value, str):
        return "unknown", value
    return None, None


def set_twisted_logger(the_logger):
    """
    Called by core.gwservice::start() to setup the utils logger.
    :param logger:
    :return:
    """
    global logger
    logger = the_logger


def json_human(data):
    return json.dumps(data, indent=4, sort_keys=True)


def sha224_compact(value):
    return base62.encodebytes(sha224(unicode_to_bytes(value)).digest())


def sha256_compact(value):
    return base62.encodebytes(sha256(unicode_to_bytes(value)).digest())


@inlineCallbacks
def get_python_package_info(required_package_name, install=None, events_queue=None):
    """
    Checks if a given python package name is installed. If so, returns it's info, otherwise returns None.

    :param required_package_name:
    :return:
    """
    global _Yombo
    if install is None:
        install = True

    conditions = ("==", "<=", ">=")
    if any(s in required_package_name for s in conditions) is False:
        logger.warn("Invalid python requirement line: {package_name}", package_name=required_package_name)
        raise YomboWarning("python requirement must specify a version or version with wildcard.")

    requirement = pkg_requirement(required_package_name)
    package_name = requirement.name

    try:
        pkg_info = pkg_resources.get_distribution(required_package_name)
    except pkg_resources.DistributionNotFound as e:
        if events_queue is not None:
            events_queue.append(["pip", "not_found", (str(required_package_name)), time()])
        else:
            _Yombo._Events.new("pip", "not_found", (str(required_package_name)))
        logger.info("Python package {required_package} is missing.",
                    required_package=required_package_name,
                    )
        if install is False:
            return None
    except pkg_resources.VersionConflict as e:
        pkg_info = pkg_resources.get_distribution(package_name)
        logger.info("Python package {required_package} is old. Found: {version_installed}, want: {wanted}",
                    required_package=package_name,
                    version_installed=pkg_info.version,
                    wanted=str(requirement.specifier),
                    )
        if events_queue is not None:
            events_queue.append(["pip", "update_needed",
                                 (package_name, str(pkg_info.version), str(requirement.specifier)), time()])
        else:
            _Yombo._Events.new("pip", "update_needed",
                               (package_name, str(pkg_info.version), str(requirement.specifier)))
        if install is False:
            return pkg_info

    else:
        return pkg_info

    # We now install the package...
    start_time = time()
    yield install_python_package(required_package_name)
    duration = round(float(time()) - start_time, 4)
    importlib.reload(pkg_resources)
    try:
        pkg_info = pkg_resources.get_distribution(required_package_name)
        logger.info("Python package installed: {name} = {version}",
                    name=pkg_info.project_name, version=pkg_info.version)

        if events_queue is not None:
            events_queue.append(["pip", "installed",
                                 (str(pkg_info.project_name), str(pkg_info.version), duration), time()])
        else:
            _Yombo._Events.new("pip", "installed", (str(pkg_info.project_name), str(pkg_info.version), duration))
        return pkg_info
    except pkg_resources.DistributionNotFound as e:
        raise YomboWarning(f"Unable to upgrade package: {e}")
    return None


@inlineCallbacks
def install_python_package(package_name):
    def update_pip_module(module_name):
        try:
            logger.info("About to install/upgrade python package: {module_name}", module_name=module_name)
            out = check_output(["pip3", "install", "-U", module_name])
            t = 0, out
        except CalledProcessError as e:
            t = e.returncode, e.message
        return t

    try:
        pip_results = yield threads.deferToThread(update_pip_module, package_name)
        if pip_results[0] != 0:
            raise Exception(pip_results[1])
    except Exception as e:
        logger.error("Unable to install/upgrade python package '{package_name}', reason: {e}",
                    package_name=package_name, e=e)
        logger.error("Try to manually isntall/update required packages: pip3 install -U -r requirements.txt")
        raise YomboWarning("Unable to install/upgrade python package.")

# def get_mdns(hostname):
#     import dns.resolver
#     myRes = dns.resolver.Resolver()
#     myRes.nameservers = ["224.0.0.251"]  # mdns multicast address
#     myRes.port = 5353  # mdns port
#     a = myRes.query("hostname.local", "A")
#     return a[0].to_text()


@inlineCallbacks
def read_file(filename, convert_to_unicode=None):
    """
    Read a file, non-blocking.

    :param filename:
    :return:
    """
    def getFile(read_filename):
        f = open(read_filename, "r")
        data = f.read()
        f.close()
        return data

    contents = yield threads.deferToThread(getFile, filename)
    if convert_to_unicode is True:
        return bytes_to_unicode(contents)
    return contents


@inlineCallbacks
def save_file(filename, content, mode=None):
    """
    A quick function to save data to a file. Defaults to overwrite, us mode "a" to append.

    Don't use this for saving large files.

    :param filename: Full path to save to.
    :param content: Content to save.
    :param mode: File open mode, default to "w".
    :return:
    """
    def writeFile(file, data, file_mode):
        if not os.path.exists(os.path.dirname(file)):
            try:
                os.makedirs(os.path.dirname(file))
            except OSError as exc:  # Guard against race condition
                if exc.errno != errno.EEXIST:
                    raise YomboWarning(f"Unable to save file: {exc}")
        if file_mode is None:
            if isinstance(data, bytes):
                file_mode = "wb"
            else:
                file_mode = "w"
        file = open(file, file_mode)
        file.write(data)
        file.close()

    yield threads.deferToThread(writeFile, filename, content, mode)


@inlineCallbacks
def copy_file(source_path, dest_path):
    def do_copy(src, dst):
        shutil.copy2(src, dst)

    yield threads.deferToThread(do_copy, source_path, dest_path)


@inlineCallbacks
def move_file(source_path, dest_path):
    def do_move(src, dst):
        shutil.copy2(src, dst)
    yield threads.deferToThread(do_move, source_path, dest_path)


@inlineCallbacks
def file_size(filename):
    def do_size(file):
        os.path.getsize(file)
    yield threads.deferToThread(do_size, filename)


@inlineCallbacks
def delete_file(filename, remove_empty=None):
    """
    Delete a file, returns a deferred.

    :param filename: Full path of file to delete
    :param remove_empty: If the directory is empty after the file is deleted, remove the directory.
    :return:
    """
    def deleteFile(delete_filename, delete_empty):
        try:
            os.remove(delete_filename)
        except OSError as e:
            raise YomboWarning(f"delete_file: Could not delete: {e}")
        if delete_empty is True:
            folder = os.path.dirname(delete_filename)
            if os.path.exists(folder) and os.path.isdir(folder):
                all_items = os.listdir(os.path.dirname(delete_filename))
                if len(all_items) == 0:
                    os.rmdir(folder)

    if remove_empty is None:
        remove_empty = False

    yield threads.deferToThread(deleteFile, filename, remove_empty)


@inlineCallbacks
def mime_type_from_file(filename):
    """
    Gets the mime type by inspecting the file.

    :param filename:
    :return:
    """
    def get_mime(file):
        my_results = magicparse.from_file(file)
        mime, charset = my_results.split("; charset=")
        return {"content_type": mime, "charset": charset}
    results = yield threads.deferToThread(get_mime, filename)
    return results


@inlineCallbacks
def mime_type_from_buffer(data):
    """
    Gets the mime type by inspecting the file.

    :param filename:
    :return:
    """
    def get_mime(buffer):
        my_results = magicparse.from_buffer(buffer)
        mime, charset = my_results.split("; charset=")
        return {"content_type": mime, "charset": charset}
    results = yield threads.deferToThread(get_mime, data)
    return results


@inlineCallbacks
def memory_usage():
    usage = yield read_file("/proc/self/status", convert_to_unicode=True)
    return int(re.search(r"^VmRSS:\s+(\d+) kb$", usage, flags=re.IGNORECASE|re.MULTILINE).group(1))


def get_nested_dict(data_dict, map_list):
    """
    Get a dictionary value using keys as a list.
    From: https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys

    :param dic:
    :param map_list:
    :return:
    """
    for k in map_list: data_dict = data_dict[k]
    return data_dict
    # return reduce(operator.getitem, dic, keys)


def set_nested_dict(dic, keys, value):
    """
    For a given dic(t) and keys, set a value.
    From:https://stackoverflow.com/questions/14692690/access-nested-dictionary-items-via-a-list-of-keys

    >>> d = {}
    >>> set_nested_dict(d, ["computer", "folder", "file"], "yombo.txt")
    >>> d
    {"computer": {"folder": {"file": "yombo.txt"}}}

    :param dic:
    :param keys:
    :param value:
    :return:
    """
    for key in keys[:-1]:
        dic = dic.setdefault(key, {})
    dic[keys[-1]] = value


def slice_dict(dic, start, stop=None, step=None):
    """
    Slices a dictionary.
    Usage:
    >>> new_dict = slice_dict(old_dict, stop)  # start = 0 if not specificed
    >>> new_dict = slice_dict(old_dict, start, stop)
    >>> new_dict = slice_dict(old_dict, start, stop, step)

    Examples:
    >>> new_dict = slice_dict(old_dict, 1)  # equiv for a list: some_list[0:1]
    >>> new_dict = slice_dict(old_dict, 2, 4)  # equiv for a list: some_list[2:4]
    >>> new_dict = slice_dict(old_dict, 2, 6)  # Start at 2, end at 6, skiping every other one.

    :param dic:
    :param start: Place to start slicing, default is 0
    :param stop: Where to stop slicing
    :param step: Used to skep items, like every other one
    :return:
    """
    if stop is None:
        return dict(itertools.islice(dic.items(), start))

    return dict(itertools.islice(dic.items(), start, stop, step))


def ordereddict_to_dict(value):
    """
    Convert an ordered dict to a regular dict, recursive.

    :param value:
    :return:
    """
    for k, v in value.items():
        if isinstance(v, dict):
            value[k] = ordereddict_to_dict(v)
    return dict(value)


def data_pickle(data, encoder=None, zip=None, local=None):
    """
    Encodes data with an encoder type. The default is "msgpack_base85". This allows data to be sent to
    databases or nearly everywhere.

    :param data: String, list, or dictionary to be encoded.
    :param encoder: Optional encode method. One of: json, msgpack, msgpack_zip, msgpack_base85, msgpack_base85_zip
    :param zip: True or a compression number from 1 to 9.

    :return: bytes (not string) of the encoded data that can be used with data_unpickle.
    """
    if zip is True:
        has_zip = True
        zip = 5
    elif isinstance(zip, int):
        has_zip = True
        if zip < 1 or zip > 9:
            zip = 5
    elif zip is None:
        has_zip = False
        zip = 5
    else:
        has_zip = False
        zip = 5

    if encoder is None:
        if has_zip:
            encoder = "msgpack_base85_zip"
        else:
            encoder = "msgpack_base85"

    if "json" in encoder and "msgack" in encoder:
        raise YomboWarning("Pickle data can only have json or msgpack, not both.")
    if "base64" in encoder and "base85" in encoder:
        raise YomboWarning("Pickle data can only have base64 or base85, not both.")

    if "json" in encoder:
        try:
            data = json.dumps(data, separators=(",", ":"))
        except Exception as e:
            raise YomboWarning(f"Error encoding json: {e}")
    elif "msgpack" in encoder:
        try:
            data = msgpack.packb(data)
        except Exception as e:
            raise YomboWarning(f"Error encoding msgpack: {e}")

    if "zip" in encoder:
        try:
            data = zlib.compress(data, zip)
        except Exception as e:
            raise YomboWarning(f"Error encoding msgpack_base85_zip: {e}")

    if "base64" in encoder:
        data = bytes_to_unicode(base64.b64encode(data))
        if local is True:
            data = data.rstrip("=")
    elif "base85" in encoder:
        data = bytes_to_unicode(base64.b85encode(data))

    return data


def data_unpickle(data, encoder=None, zip=None):
    """
    Unpack data packed with data_pickle.

    :param data:
    :param encoder:
    :param zip: True if incoming data is zipped...

    :return:
    """
    if data is None:
        return None
    data = bytes_to_unicode(data)

    if encoder is None:
        # if zip_level is True or isinstance(zip_level, int):
        #     encoder = "msgpack_base85_zip"
        # else:
        encoder = "msgpack_base85"

    # Sometimes empty dictionaries are encoded...  This is a simple shortcut.
    if encoder == "msgpack_base85_zip" and data == "cwTD&004mifd":
        return {}
    elif encoder == "msgpack_base85" and data == "fB":
        return {}

    if "json" in encoder and "msgack" in encoder:
        raise YomboWarning("Unpickle data can only have json or msgpack, not both.")
    if "base64" in encoder and "base85" in encoder:
        raise YomboWarning("Unpickle data can only have base64 or base85, not both.")

    if "base64" in encoder:
        data = data + "=" * (-len(data) % 4)
        data = base64.b64decode(data)
    elif "base85" in encoder:
        data = base64.b85decode(data)

    try:
        data = zlib.decompress(data)
    except Exception as e:
        pass

    if "json" in encoder:
        try:
            data = bytes_to_unicode(json.loads(data))
        except Exception as e:
            raise YomboWarning(f"Error encoding json: {e}")
    elif "msgpack" in encoder:
        try:
            data = bytes_to_unicode(msgpack.unpackb(data))
        except Exception as e:
            raise YomboWarning(f"Error encoding msgpack: {e}")

    return data


def instance_properties(obj, startswith_filter=None, endwith_filter=None):
    """
    Get the attributes of an instance and return a dictionary.

    Modified from: https://stackoverflow.com/questions/61517/python-dictionary-from-an-objects-fields
    :param obj:
    :return:
    """
    pr = {}
    for name in dir(obj):
        value = getattr(obj, name)
        if not name.startswith("__") and not inspect.ismethod(value):
            if startswith_filter is not None:
                if name.startswith(startswith_filter) is False:
                    continue
            if endwith_filter is not None:
                if name.endswith(endwith_filter) is False:
                    continue
            pr[name] = value
    return pr


def pattern_search(look_for, items):
    """
    Allows searching thru a list of items (a dict or list). For example, a list of:

    ["yombo.status.hello", "yombo.status.bye", "visitor.livingroom.hello"]

    You can search using #'s for wildcards consuming ay number of spaces between or +'s
    as a wildcard for only on work.  For example, a search of "#.hello" would result in:

    ["yombo.status.hello", "visitor.livingroom.hello"]

    While a search of "yombo.status.+" would result in:

    ["yombo.status.hello", "yombo.status.bye"]

    :param look_for:
    :param items:
    :return:
    """
    regex = re.compile(look_for.replace("#", ".*").replace("$", "\$").replace("+", "[/\$\s\w\d]+"))
    out_list = []
    if isinstance(items, dict):
        for item, data in items.items():
            result = regex.match(item)
            if result is not None:
                out_list.append(item)
    elif isinstance(items, list):
        for item in items:
            result = regex.match(item)
            if result is not None:
                out_list.append(item)
    return out_list


def split(the_string, delimiter=","):
    """
    Pass in a string, and get back a list. This also ignore white spaces padding the delimiter.

    :param the_string: The string to parse
    :param delimiter: Default: , (commad).
    :return:
    """
    return [x.strip() for x in the_string.split(delimiter)]


def clean_kwargs(**kwargs):
    """
    Returns a dictionary without any keys starting with "__" (double underscore).
    """
    data = {}
    start = kwargs.get("start", "__")
    for key, val in kwargs.items():
        if not key.startswith(start):
            data[key] = val
    return data


def clean_dict(dictionary, **kwargs):
    """
    Returns a dictionary without any keys starting with kwargs["start"] (default "_" underscore).
    """
    data = {}
    start = kwargs.get("start", "_")
    for key, val in dictionary.items():
        if not key.startswith(start):
            data[key] = val
    return data


def bytes_to_unicode(value):
    """
    Converts strings, lists, and dictionarys to unicode. Handles nested items too. Non-strings are untouched.
    Inspired by: http://stackoverflow.com/questions/13101653/python-convert-complex-dictionary-of-strings-from-unicode-to-ascii

    :param value: Convert strings to unicode.
    :type value: dict, list, str
    :return:
    """
    if isinstance(value, dict):
        return dict((bytes_to_unicode(key), bytes_to_unicode(value)) for key, value in value.items())
    elif isinstance(value, list):
        return [bytes_to_unicode(element) for element in value]
    elif isinstance(value, bytes) or isinstance(value, bytearray):
        try:
            return value.decode("utf-8")
        except Exception:
            return value
    else:
        return value


def unicode_to_bytes(value):
    """
    Converts strings, lists, and dictionarys to strings. Handles nested items too. Non-strings are untouched.
    Inspired by: http://stackoverflow.com/questions/13101653/python-convert-complex-dictionary-of-strings-from-unicode-to-ascii

    :param value:
    :return:
    """
    if isinstance(value, dict):
        return dict((unicode_to_bytes(key), unicode_to_bytes(value)) for key, value in value.items())
    elif isinstance(value, list):
        return [unicode_to_bytes(element) for element in value]
    elif isinstance(value, str):
        return value.encode()
    else:
        return value


def snake_case(value):
    return value.replace(" ", "_").lower()


def dict_has_key(dictionary, keys):
    """
    Check if a dictionary has the given list of keys

    **Usage**:

    .. code-block:: python

       from yombo.utils import dict_has_key
       a_dictionary = {"identity": {"location": {"state": "California"}}}
       a_list = ["identity", "location", "state"]
       has_state = dict_has_key(a_dictionary, a_list)
       #has_state is now: True

    :param dictionary: A dictionary to check
    :type dictionary: dict
    :param key: A list of keys
    :type key: list
    """
    if not isinstance(keys, list):
        keys = [keys]
    try:
        for key in keys:
             tossaway = dictionary[key]
    except KeyError:
        return False
    except TypeError:
        return False
    else:
        return True


def dict_find_key(search_dictionary, val):
    """
    Find a key of a dictionary for a given value.

    :param search_dictionary: The dictionary to search.
    :type search_dictionary: dict
    :param val: The value to search for.
    :type val: any valid dict key type
    :return: The key of dictionary dic given the value
    :rtype: any valid dict key type
    """
    return [k for k, v in search_dictionary.items() if v == val][0]


def dict_has_value(dictionary, keys, value):
    """
    Check if a dictionary has the value based on a given list of keys

    **Usage**:

    .. code-block:: python

       from yombo.utils import dict_has_value
       a_dictionary = {"identity": {"location": {"state": "California"}}}
       a_list = ["identity", "location", "state"]
       has_california = dict_has_value(a_dictionary, a_list, "California")
       #has_california is now: True

    :param dictionary: A dictionary to check
    :type dictionary: dict
    :param key: A list of keys
    :type key: list
    :param value: The value to test for
    :type value: Any value a dictionary can hold.
    """
    if not isinstance(keys, list):
        keys = [keys]
    try:
        for key in keys[:-1]:
             dictionary = dictionary[key]
        if dictionary[keys[-1]] == value:
            return True
    except KeyError:
        return False
    except TypeError:
        return False
    else:
        return False


def dict_set_value(dictionary, keys, value):
    """
    Set dictionary value based on a given list of keys

    **Usage**:

    .. code-block:: python

       from yombo.utils import dict_set_value
       a_dictionary = {}
       a_list = ["identity", "location", "state"]
       dict_set_value(a_dictionary, a_list, "California")
       #a_dictionary now: {"identity": {"location": {"state": "California"}}}

    :param dictionary: A dictionary to update
    :type dictionary: dict
    :param key: A list of keys
    :type key: list
    :param value: The value to set
    :type value: Any value a dictionary can hold.
    """
    if not isinstance(keys, list):
        keys = [keys]
    for key in keys[:-1]:
         dictionary = dictionary.setdefault(key, {})
    dictionary[keys[-1]] = value


def dict_get_value(dictionary, keys):
    """
    Get dictionary value based on a given list of keys

    **Usage**:

    .. code-block:: python

       from yombo.utils import dict_get_value
       a_dictionary  = {"identity": {"location": {"state": "California"}}}
       a_list = ["identity", "location", "state"]
       value = dict_get_value(a_dictionary, a_list)
       #value = "California"

    :param dictionary: A dictionary to update
    :type dictionary: dict
    :param key: A list of keys
    :type key: list
    """
    if not isinstance(keys, list):
        keys = [keys]
    for key in keys[:-1]:
         dictionary = dictionary.setdefault(key, {})
    return dictionary[keys[-1]]


def dict_merge(original, changes):
    """
    Recursively merges a dictionary with any changes. Sub-dictionaries won't be overwritten - just updated.

    *Usage**:

    .. code-block:: python

        my_information = {
            "name": "Mitch"
            "phone: {
                "mobile": "4155551212"
            }
        }

        updated_information = {
            "phone": {
                "home": "4155552121"
            }
        }

        print(dict_merge(my_information, updated_information))

    # Output:

    .. code-block:: none

        {
            "name": "Mitch"
            "phone: {
                "mobile": "4155551212",
                "home": "4155552121"
            }
        }
    """
    for key, value in original.items():
        if key not in changes:
            changes[key] = value
        elif isinstance(value, dict):
            dict_merge(value, changes[key])
    return changes


def dict_diff(dict1, dict2):
    """
    Returns the differences between two dictionarys.

    **Usage**:

    .. code-block:: python

       from yombo.utils import dict_diff
       aa = dict(a=1, b=2)
       bb = dict(a=2, b=2)
       added, removed, modified, same = dict_diff(aa, bb)

    :param dict1:
    :param dict2:
    :return:
    """
    dict1_keys = set(dict1.keys())
    dict2_keys = set(dict2.keys())
    intersect_keys = dict1_keys.intersection(dict2_keys)
    added = dict1_keys - dict2_keys
    removed = dict2_keys - dict1_keys
    modified = {o : (dict1[o], dict2[o]) for o in intersect_keys if dict1[o] != dict2[o]}
    same = set(o for o in intersect_keys if dict1[o] == dict2[o])
    return added, removed, modified, same


def dict_filter(input_dict, key_list):
    """
    Returns a new dictionary with only the supplied list of keys.

    :param input_dict:
    :param key_list:
    :return:
    """
    return dict((key, input_dict[key]) for key in key_list if key in input_dict)


def file_last_modified(path_to_file):
    return os.path.getmtime(path_to_file)


def percentage(part, whole):
    """
    Return a float representing a percentage of part against the whole.

    For example: percentage(7, 12) returns: 58.333333333333336

    :param part:
    :param whole:
    :return:
    """
    return 100 * float(part)/float(whole)


def percentile(data_list, percent, key=lambda x:x):
    """
    Find the percentile of a list of values.

    I think this was found here:http://code.activestate.com/recipes/511478-finding-the-percentile-of-the-values/

    :param data_list: A list of values. Note N MUST BE already sorted.
    :param percent: A float value from 0.0 to 1.0.
    :param key: Optional key function to compute value from each element of N

    :return: The percentile of the values
    """
    if not data_list:
        return None
    k = (len(data_list)-1) * percent
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return key(data_list[int(k)])
    d0 = key(data_list[int(f)]) * (c-k)
    d1 = key(data_list[int(c)]) * (k-f)
    return d0+d1


def do_search_instance(attributes, haystack, allowed_keys, limiter=None, max_results=None,
                       required_field=None, required_value=None,
                       ignore_field=None, ignore_value=None):
    """
    Does the actual search of the devices. It scans through each item in haystack, and searches for any
    supplied attributes using fuzzy logic. The limiter (either specified in the attributes or the limiter
    argument if not supplied in teh attributes) controls how much of a string much match to be included in
    the results.

    Scan through the dictionary (or list), and match keys. Returns the value of
    the best matching key.

    :param attributes: Either a list of dictionaries containing: field, value, limiter or a dictionary
      containing field:values to match.
    :type attributes: list of dictionaries, or a dictionary of attributes/value.
    :param operation: Set weather to all matching, or highest matching. Either "any" or "highest".
    """
    if limiter is None:
        limiter = .90
    if limiter > .99999999:
        limiter = .99
    elif limiter < .10:
        limiter = .10

    if isinstance(attributes, dict):
        new_attributes = []
        for field, value in attributes.items():
            new_attributes.append({
                "field": field,
                "value": value,
                "limiter": limiter,
            })
        attributes = new_attributes
        del new_attributes
    elif isinstance(attributes, list) is False:
        raise YomboWarning("Attributes must be a list.")

    # print(f"do_search_attrs: {attributes}")
    for attr in attributes:
        if isinstance(attr, dict) is False:
            raise YomboWarning("Attribute items must be dictionaries")
        if all(k in ("field", "value") for k in attr):
            raise YomboWarning("Attribute dictionary doesn't have required keys.")
        if attr["field"] not in allowed_keys:
            raise YomboWarning(f"Field is not a valid searchable item: {attr['field']}")

        if "limiter" not in attr:
            attr["limiter"] = limiter
        else:
            if attr["limiter"] is None:
                attr["limiter"] = limiter
            if attr["limiter"] > .99999999999:
                attr["limiter"] = .99
            elif attr["limiter"] < .10:
                attr["limiter"] = .10

    # Prepare the minion
    stringDiff = SequenceMatcher()

    # used when return highest
    best_ratio = 0
    best_limiter = 0
    # best_match = None
    # best_key = None

    key_list = []

    for item_id, item in haystack.items():
        if ignore_field is not None:
            if getattr(item, ignore_field) == ignore_value:
                continue
        if required_field is not None:
            if getattr(item, required_field) != required_value:
                continue
        for attr in attributes:
            stringDiff.set_seq1(str(attr["value"]))
            # try:
            stringDiff.set_seq2(str(getattr(item, attr["field"])))
            # except TypeError:
            #     continue  # might get here, even though it"s not a string. Catch it!
            ratio = stringDiff.ratio()

            if ratio < limiter:
                continue
            # if this is the best ratio so far - save it and the value
            if ratio > best_ratio:
                best_ratio = ratio
                best_limiter = attr["limiter"]

            key_list.append({"key": item_id, "value": item, "ratio": ratio})

    key_list = sorted(key_list, key=lambda k: k["ratio"], reverse=True)
    result_values = {}
    result_ratios = {}
    # count = 0
    for item in key_list:
        if item["key"] in result_values:
            if item["ratio"] > result_ratios[item["key"]]:
                result_ratios[item["key"]] = item["ratio"]
            continue
        result_values[item["key"]] = item["value"]
        result_ratios[item["key"]] = item["ratio"]

        # count += 1
        if isinstance(max_results, int) and (len(result_values) == max_results and max_results > 0):
            break

    if best_ratio is None:
        raise KeyError("No items found above the cut off limit.")

    return {
        "was_found": best_ratio >= best_limiter,  # the part that does the actual check.
        "best_ratio": best_ratio,
        "values": result_values,
        "ratios": result_ratios,
    }


def get_method_definition_level(meth):
    for cls in inspect.getmro(meth.__self__.__class__):
        if meth.__name__ in cls.__dict__: return str(cls)
    return None


def random_string(**kwargs):
    """
    Generate a random alphanumeric string. *All arguments are kwargs*.

    **Usage**:

    .. code-block:: python

       from yombo.utils import random_string
       someRandonness = random_string(letters="ABCDEF0123456789") #make a hex value

    :param length: Length of the output string. Default: 32
    :type length: int
    :param letters: A string of characters to to create the new string from.
        Default: letters upper and lower, numbers 0-9
    :type letters: string
    :return: A random string that contains choices from `letters`.
    :rtype: string
    """
    length = kwargs.get("length", 32)
    letters = None
    if "char_set" in kwargs:
        char_set = kwargs["char_set"]
        if char_set == "extended":
            letters = "abcdefghijklmnopqrstuvwxyABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!()*-;<>^-{}~"
        else:
            letters = kwargs["char_set"]
    else:
        letters = kwargs.get("letters", None)

    if not hasattr(random_string, "randomStuff"):
        random_string.randomStuff = random.SystemRandom()

    if letters is None:
        lst = [random_string.randomStuff.choice(string.ascii_letters + string.digits) for n in range(length)]
        return "".join(lst)
    else:
        lst = [random_string.randomStuff.choice(letters) for n in range(length)]
        return "".join(lst)


def random_int(middle, percent, **kwargs):
    """
    Generate random integer based on a middle number and percent range.

    **Usage**:

    .. code-block:: python

       from yombo.utils import random_int
       someRandonness = random_string(1000, .40)  # get a random number 600 and 1400

    :param middle: The middle number of the rang to get
    :type middle: int
    :param percent: A percentage to range from.
    :type percent: float
    :return: A random number
    :rtype: int
    """

    start = round(middle - (middle * percent))
    end = round(middle + (middle * percent))
    return random.randint(start, end)


def excerpt(value, length=None):
    if length is None:
        length = 25

    if isinstance(value, str):
        return textwrap.shorten(value, length)
    return value


def make_link(link, link_text, target=None, options=None):
    if options is None:
        options = ""
    if link == "" or link is None or link.lower() == "None":
        return "None"
    if target is None:
        target = "_self"
    return f'<a href="{link}" target="{target}" {options}>{link_text}</a>'


def format_markdown(input_text, formatting=None):
    if formatting == "restructured" or formatting is None:
        return publish_parts(input_text, writer_name="html")["html_body"]
    elif formatting == "markdown":
        return markdown.markdown(input_text, extensions=["markdown.extensions.nl2br", "markdown.extensions.codehilite"])
    return input_text


def display_hide_none(value, allow_string=None, default=None):
    """
    Changes type None to display "".

    :param value:
    :param allow_string:
    :return:
    """
    if value is None:
        if default is not None:
            return default
        else:
            return ""
    if isinstance(value, str):
        if allow_string is True:
            return value
        if value.lower() == "none":
            return ""
    return value


def human_alphabet():
    """ A subset of the alphabet, but with 1 (one), l (ele)...etc, removed."""
    return "ABCDEFGHJKLMNPQRTSUVWXYZabcdefghkmnopqrstuvwxyz23456789"


def get_public_gw_id():
    configs = get_component("yombo.lib.configuration")
    try:
        gwid = configs.get("core", "gwid")[0:6] + ":" + configs.get("core", "gwuuid")[0:5]
        return gwid
    except:
        return "unknown"

#
# def get_library(name):
#     """
#     Returns the requested library by it's name using :ref:`FuzzySearch <fuzzysearch>`. This
#     allows the name to be off by one or two letters.
#
#     :raises KeyError: When the requested component cannot be found.
#     :param name: The name of the component (library or module) to find.  Returns a
#         pointer to the object so it's functions and attributes can be accessed.
#     :type name: string
#     :return: Pointer to requested library or module.
#     :rtype: Object reference
#     """
#     get_library.asdfsadf = 'asdfasdf'
#     if not hasattr(get_library, "library"):
#         from yombo.lib.loader import get_library
#         get_library.library = get_library
#     try:
#         return get_library.library(name)
#     except KeyError:
#         raise KeyError("No such library" + str(name))
#
#
# def get_module(name):
#     """
#     Returns the requested library by it's name using :ref:`FuzzySearch <fuzzysearch>`. This
#     allows the name to be off by one or two letters.
#
#     :raises KeyError: When the requested component cannot be found.
#     :param name: The name of the component (library or module) to find.  Returns a
#         pointer to the object so it's functions and attributes can be accessed.
#     :type name: string
#     :return: Pointer to requested library or module.
#     :rtype: Object reference
#     """
#     if not hasattr(get_module, "module"):
#         from yombo.lib.loader import get_module
#         get_module.library = get_library
#     try:
#         return get_module.library(name)
#     except KeyError:
#         raise KeyError("No such library" + str(name))


def get_component(name):
    """
    Return loaded component (module or library). This can be used to find
    other modules or libraries. The getComponent uses the :ref:`FuzzySearch <fuzzysearch>`
    class to make searching easier, but can only be off one or two letters
    due to importance of selecting the correct library or module.

    :raises KeyError: When the requested component cannot be found.
    :param name: The name of the component (library or module) to find.  Returns a
        pointer to the object so it's functions and attributes can be accessed.
    :type name: string
    :return: Pointer to requested library or module.
    :rtype: Object reference
    """
    if not hasattr(get_component, "components"):
        from yombo.lib.loader import get_the_loaded_components
        get_component.components = get_the_loaded_components()
    try:
        return get_component.components[name.lower()]
    except KeyError:
        raise KeyError("No such loaded component:" + str(name))


def is_string_bool(value=None):
    """
    Returns a True/False/None based on the string. If nothing is found, "YomboWarning" is raised.
    Returns a boolean value representing the "truth" of the value passed. Returns true if the string
    provided is "true/True/trUE, etc".

    :param value: String of either "true" or "false" (case insensitive), returns bool or raises YomboWarning.
    """
    if isinstance(value, str):
        if str(value).lower() == "true":
            return True
        elif str(value).lower() == "false":
            return False
        elif str(value).lower() == "none":
            return None
        else:
            raise YomboWarning("String is not true, false, or none.")
    if isinstance(value, bool):
        return value
    raise YomboWarning("String is not true, false, or none.")


def is_true_false(value, only_bool=False):
    """
    Used by various utils to determine if an input is high or low. Other functions like is_one_zero and is_yes_no will
    return the results in different ways based on results from here

    :param value: A string, bool, int to test
    :param only_bool: If true, will only return bools. Otherwise, None will be returned if indeterminate input.
    :return:
    """
    if isinstance(value, bool):
            return value
    elif isinstance(value, str):
        value = value.lower()
        if value in ("true", "1", "open", "opened", "on", "running", "alive"):
            return True
        if value in ("false", "0", "close", "closed", "off", "stopped", "dead"):
            return False
    elif isinstance(value, int):
            if value == 1:
                return True
            elif value == 0:
                return False
    else:
        if only_bool:
            return False
        else:
            return None


def is_yes_no(value):
    """
    Tries to guess if input is a positive value (1, "1", True, "On", etc). If it is, returns "Yes", otherwise,
    returns "No". Useful to convert something to human Yes/No.
    :param value:
    :return: String on either "Yes" or "No".
    """
    if is_true_false(value, True):
        return "Yes"
    else:
        return "No"


def is_one_zero(value):
    """
    Like is_yes_no, but returns 1 for yes/true/on/open/running, 0 for otherwise.

    Tries to guess if input is a positive value (1, "1", True, "On", etc). If it is, returns "Yes", otherwise,
    returns "No". Useful to convert something to human Yes/No.
    :param value:
    :return:
    """
    if is_true_false(value, True):
        return 1
    else:
        return 0


def is_none(value):
    """
    Returns None type if the input is None type, or a string saying "none". If it"s not, will return the input.

    :param value:
    :return:
    """
    if value is None:
        return None
    elif isinstance(value, str):
        if value.lower() == "none":
            return None
    return value


def forgiving_float(value):
    """
    Primarily used for templates as a filter. Tries to convert input to a float. Doesn"t die if it fails.

    :param value:
    :return:
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return value


def forgiving_round(value, precision=0):
    """
    Primarily used for templates as a filter. Rounds string, int, or float Accepts a precision to
    determine number of decimals places.

    :param precision:
    """
    try:
        value = round(float(value), precision)
        return int(value) if precision == 0 else value
    except (ValueError, TypeError):
        return value  # return input if value cannot be rounded.


def multiply(value, amount):
    """
    Primarily used for templates as a filter. Takes an int, string, or float and multiplies it.

    :param value: Input
    :param amount: Multiplier
    """
    try:
        return float(value) * amount
    except (ValueError, TypeError):
        return value  # return input if value cannot be multiplied.


def logarithm(value, base=math.e):
    """
    Primarily used for templates as a filter. Performs logarithm math to a value.

    :param value:
    :param base:
    """
    try:
        return math.log(float(value), float(base))
    except (ValueError, TypeError):
        return value  # return input if value cannot be processed.


def fail_when_undefined(value):
    """Filter to force a failure when the value is undefined."""
    if isinstance(value, jinja2.Undefined):
        value()
    return value


def test_bit(int_type, offset):
    """
    Tests whether a specific bit is on or off for a given int.

    :param int_type: The given int to interrogate.
    :type int_type: int
    :param offset: The bit location to return, starting from lowest to highest.
    :type offset: int
    :return: If the bit is on or off
    """
    mask = 1 << offset
    if (int_type & mask) > 0:
        return 1
    else:
        return 0
    # return int_type & mask


class ViewAsObject(object):
    def __init__(self, d):
        self.__dict__ = d


def sleep(secs):
    """
    A simple non-blocking sleep function.  This generates a twisted
    deferred. You have to decorate your function to make the yield work
    properly.

    **Usage**:

    .. code-block:: python

       from twisted.internet import defer
       from yombo.core.helpers import sleep

       @defer.inlineCallbacks
       def myFunction(self):
           logger.info("About to sleep.")
           yield sleep(5.4) # sleep 5.4 seconds.
           logger.info("I"m refreshed.")

    :param secs: Number of seconds (whole or partial) to sleep for.
    :type secs: int of float
    """
    return deferLater(reactor, secs, lambda: None)


def hashid_encode(input_value, min_length=2, salt="", alphabet="ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvxyz234"):
    """
    Encodes an int and returns a string. This typically shortens the length and is great for
    showing users a better representation of a large int - if they don't care about the actual value.

    :param input_value: Int - Input value to encode to a string.
    :param min_length: Int - Minimum length string should be. Will pad if required.
    :param salt: String - A salt to mangle the value. This isn't secure!
    :param alphabet: String -
    :return:
    """
    hashid = Hashids(salt, min_length, alphabet)
    return hashid.encode(input_value)


def hashid_decode(input_value, min_length=2, salt="", alphabet="ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvxyz234"):
    hashid = Hashids(salt, min_length, alphabet)
    return hashid.decode(input_value)


@memoize_
def is_freebsd():
    """
    Returns if the host is freebsd or not
    """
    return sys.platform.startswith("freebsd")


@memoize_
def is_linux():
    """
    Returns if the host is linus or not
    """
    return sys.platform.startswith("linux")


@memoize_
def is_windows():
    """
    Returns if the host is windows or not
    """
    return sys.platform.startswith("win")


@memoize_
def is_sunos():
    """
    Returns if the host is sunos or not
    """
    return sys.platform.startswith("sunos")
