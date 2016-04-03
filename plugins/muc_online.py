import logging
import time
import random

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


@pluginfunction('comment_joins', 'comments frequent joins', ptypes_MUC_ONLINE)
@config_locked
def comment_joins(**args):
    # max elapsed time between the latest and the N latest join
    timespan  = 120
    max_joins = 6

    comment_joins_strings = [
        "%s: please consider to fix your internet connection"
    ]

    current_timestamp = int(time.time())

    arg_user = args['reply_user']
    arg_user_key = arg_user.lower()

    if arg_user_key not in config.runtime_config_store['user_joins']:
        config.runtime_config_store['user_joins'][arg_user_key] = [ current_timestamp ]
        config.runtimeconf_persist()
        return None

    user_joins = config.runtime_config_store['user_joins'][arg_user_key]

    user_joins = [
        ts if current_timestamp - int(ts) <= timespan else [] for ts in user_joins
    ]
    user_joins.append(current_timestamp)

    if len(user_joins) >= max_joins:
        config.runtime_config_store['user_joins'].pop(arg_user_key)
        config.runtimeconf_persist()
        return { 'msg':  random.choice(comment_joins_strings) % arg_user }
    else:
        config.runtimeconf_persist()
