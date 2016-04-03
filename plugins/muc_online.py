import logging

import config
from common import (
    pluginfunction, config_locked,
    ptypes_MUC_ONLINE
)

log = logging.getLogger(__name__)


@pluginfunction('send_record', 'delivers previously saved message to user', ptypes_MUC_ONLINE)
@config_locked
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

        user_records.pop(arg_user_key)
        config.runtimeconf_persist()

        return response
