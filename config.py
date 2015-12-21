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
import os
import sys
from fasteners import interprocess_locked
from configobj import ConfigObj
from validate import Validator


CONFIG_SUFFIX = os.environ.get('BOTSUFFIX', '')
__initialized = False
__config_store = ConfigObj('local_config{}.ini'.format(CONFIG_SUFFIX), configspec='local_config.ini.spec')
runtime_config_store = ConfigObj('persistent_config.ini'.format(CONFIG_SUFFIX), configspec='persistent_config.ini.spec')

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
    runtimeconf_persist()


def runtimeconf_get(key, default=None):
    if key is None:
        return runtime_config_store
    else:
        return runtime_config_store.get(key, default=default)


@interprocess_locked(runtime_config_store.filename)
def runtimeconf_persist():
    logging.getLogger(__name__).debug(json.dumps(runtime_config_store, indent=2))
    runtime_config_store.write()


def runtimeconf_deepget(key, default=None):
    """
    access a nested key with get("plugins.moin.enabled")
    :param key: string of nested properties joined with dots
    :param default: default key if None found
    :return:
    """
    if '.' not in key:
        return runtimeconf_get(key, default)
    else:
        path = key.split('.')
        value = runtimeconf_get(path.pop(0))
        for p in path:
            value = value.get(p, default)
            if value is None:
                break
        return value
