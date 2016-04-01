import logging

import config
from common import (
    pluginfunction,
    ptypes_MUC_ONLINE
)

log = logging.getLogger(__name__)


@pluginfunction('send_record', 'delivers previously saved message to user', ptypes_MUC_ONLINE)
def send_record(**args):
    arg_user = args['reply_user']
    arg_user_key = arg_user.lower()
    user_records = config.runtimeconf_get('user_records')

    if arg_user_key in user_records:
        records = user_records[arg_user_key]

        if not records:
            return None

        response = {
            'msg':  '%s, there %s %d message%s for you:\n%s' % (
                    arg_user,
                    'is' if len(records) == 1 else 'are',
                    len(records),
                    '' if len(records) == 1 else 's',
                    '\n'.join(records)
                )
        }

        if config.conf_get('persistent_locked'):
            log.warning("couldn't get exclusive lock")
            return None

        config.conf_set('persistent_locked', True)

        user_records.pop(arg_user_key)
        config.runtimeconf_persist()

        config.conf_set('persistent_locked', False)

        return response
