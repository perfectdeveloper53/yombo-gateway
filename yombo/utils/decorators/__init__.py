"""
Various function decorators.

.. moduleauthor:: Mitch Schwenk <mitch-gw@yombo.net>

:copyright: Copyright 2016-2017 by Yombo.
:license: LICENSE for details.
"""
# Import python libraries
from functools import wraps
from time import time
from hashlib import sha256
import pickle
import warnings
import functools

# Import Yombo libraries
import yombo.utils


def deprecated(func):
    """
    This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emmitted
    when the function is used.
    Found: https://stackoverflow.com/questions/2536307/decorators-in-the-python-standard-lib-deprecated-specifically
    """

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.simplefilter('always', DeprecationWarning) #turn off filter
        warnings.warn("Call to deprecated function {}.".format(func.__name__), category=DeprecationWarning, stacklevel=2)
        warnings.simplefilter('default', DeprecationWarning) #reset filter
        return func(*args, **kwargs)

    return new_func

def static_var(varname, value):
    """
    Sets a static variable within a function. This is an easy way to set a default.

    **Usage**:

    .. code-block:: python

        from yombo.utils.decorators import static_var

        @static_var("my_variable", 0)
        def some_function(x):
            some_function.my_variable += 1
            print "I've been called %s times." % some_function.my_variable

    :param varname: variable name to create
    :param value: initial value to set.
    :return:
    """
    def decorate(func):
        setattr(func, varname, value)
        return func
    return decorate

def memoize_(func):
    """
    Reuse the results of a static function. Subsequent calls will get cached results.

    **Usage**:

    .. code-block:: python

        from yombo.utils.decorators import memoize_

        print fib(35) # Without decorator, will take a little bit of time.
        print fib(35) # With decorator, will be nearly instant - even on first call for a fib.

        @memoize_
        def fib(x):
            if num < 2:
                return num
            else:
                return fib(num-1) + fib(num-2)
    """
    saved = {}

    @wraps(func)
    def _memoize(*args):
        if args not in saved:
            saved[args] = func(*args)
        return saved[args]
    return _memoize

class memoize_ttl(object):
    """
    Yombo modified, but from: http://jonebird.com/2012/02/07/python-memoize-decorator-with-ttl-argument/

    Decorator that caches a function's return value each time it is called within a TTL.
    If called within the TTL and the same arguments, the cached value is returned,
    If called outside the TTL or a different value, a fresh value is returned.

    Default TTL is 60 seconds

    **Usage**:

    .. code-block:: python

        from yombo.utils.decorators import memoize_ttl

        print fib(35) # Without decorator, will take a little bit of time.
        print fib(35) # With decorator, will be nearly instant - even on first call for a fib.

        @memoize_ttl(5) # memoize for 5 seconds
        def fib(x):
            if num < 2:
                return num
            else:
                return fib(num-1) + fib(num-2)
    """
    def __init__(self, ttl=60):
        self.cache = {}
        self.ttl = ttl

    def __call__(self, f):
        def wrapped_f(*args, **kwargs):
            now = time()
            the_hash = (args, sha256(pickle.dumps(kwargs)).hexdigest())
            try:
                value, last_update = self.cache[the_hash]
                if self.ttl > 0 and now - last_update > self.ttl:
                    raise AttributeError
                # print 'DEBUG: cached value'
                return value
            except (KeyError, AttributeError):
                value = f(*args, **kwargs)
                self.cache[the_hash] = (value, now)
                # print 'DEBUG: fresh value'
                return value
            except TypeError:
                # uncachable -- for instance, passing a list as an argument.
                # Better to not cache than to blow up entirely.
                return f(*args, **kwargs)
        return wrapped_f

def timing(function):
    """
    Decorator wrapper that logs the time it takes to complete function.

    Primarily used for profiling.
    """
    @wraps(function)
    def wrapped(*args, **kwargs):
        start_time = time()
        data = function(*args, **yombo.utils.clean_kwargs(**kwargs))
        end_time = time()
        mod_name = function.__module__
        print("Function %s.%s took %s seconds to execute." % (mod_name, function.__name__, (end_time - start_time)))
        return data
    return wrapped
