"""
Interface to access:
 - local configuration
 - shared configuration
 - shared runtime state

All configuration is stored in a single ini-file and
persistent state is pickle-dumped into a binary file.

TODO: check lock safety
TODO: manage persistent state in configobj
"""
import json
import logging
import sys
from configobj import ConfigObj
from validate import Validator

__initialized = False
__config_store = ConfigObj('local_config.ini', configspec='local_config.ini.spec')

validator = Validator()
result = __config_store.validate(validator)

if not result:
    print('Config file validation failed!')
    sys.exit(1)
else:
    __initialized = True
    __config_store.write()


def get(key):
    if not __initialized:
        raise RuntimeError("not __initialized")
    try:
        return __config_store[key]
    except KeyError as e:
        logger = logging.getLogger(__name__)
        logger.warn('conf(): unknown key ' + str(key))
        print(json.dumps(__config_store, indent=2))
        raise


def set(key, val):
    __config_store[key] = val
    __config_store.write()
    return None
