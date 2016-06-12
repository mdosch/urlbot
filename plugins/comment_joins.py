# -*- coding: utf-8 -*-
import logging
import time
import random
import config
from plugin_system import pluginfunction, ptypes

log = logging.getLogger(__name__)

comment_joins_strings = [
    "%s: please consider to fix your internet connection"
]


@pluginfunction('comment_joins', 'comments frequent joins', ptypes.MUC_ONLINE)
@config.config_locked
def comment_joins(**args):
    # max elapsed time between the latest and the N latest join
    timespan = 120
    max_joins = 6

    current_timestamp = int(time.time())

    arg_user = args['reply_user']
    arg_user_key = arg_user.lower()

    if arg_user_key not in config.runtime_config_store['user_joins']:
        config.runtime_config_store['user_joins'][arg_user_key] = [current_timestamp]
        config.runtimeconf_persist()
        return None

    user_joins = []

    for ts in config.runtime_config_store['user_joins'][arg_user_key]:
        if current_timestamp - int(ts) <= timespan:
            user_joins.append(ts)

    print(user_joins)

    if len(user_joins) >= max_joins:
        config.runtime_config_store['user_joins'].pop(arg_user_key)
        config.runtimeconf_persist()
        log.info("send comment on join")
        return {'msg': random.choice(comment_joins_strings) % arg_user}
    else:
        user_joins.append(current_timestamp)
        config.runtime_config_store['user_joins'][arg_user_key] = user_joins
        config.runtimeconf_persist()
