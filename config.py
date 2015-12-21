"""
Interface to access:
 - local configuration
 - shared configuration
 - shared runtime state

All configuration is stored in a single ini-file and
persistent state is pickle-dumped into a binary file.

TODO: check lock safety
"""
import json
import logging
import sys
from configobj import ConfigObj
from validate import Validator

__initialized = False
__config_store = ConfigObj('local_config.ini', configspec='local_config.ini.spec')
runtime_config_store = ConfigObj('persistent_config.ini', configspec='persistent_config.ini.spec')

validator = Validator()
result = __config_store.validate(validator)
runtime_config_store.validate(validator)

if not result:
    print('Config file validation failed!')
    sys.exit(1)
else:
    __initialized = True
    __config_store.write()


def conf_get(key):
    if not __initialized:
        raise RuntimeError("not __initialized")
    try:
        return __config_store[key]
    except KeyError as e:
        logger = logging.getLogger(__name__)
        logger.warn('conf(): unknown key ' + str(key))
        print(json.dumps(__config_store, indent=2))
        raise


def conf_set(key, val):
    __config_store[key] = val
    __config_store.write()
    return None


def runtimeconf_set(key, value):
    runtime_config_store[key] = value
    runtime_config_store.write()


def runtimeconf_get(key, default=None):
    if key is None:
        return runtime_config_store
    else:
        return runtime_config_store.get(key, default=default)


def runtimeconf_deepget(key, default=None):
    if '.' not in key:
        return runtimeconf_get(key, default)
    else:
        path = key.split('.')
        value = runtimeconf_get(path.pop(0))
        for p in path:
            value = value.get(p)
            if value is None:
                return None
        return value
