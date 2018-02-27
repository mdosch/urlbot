# -*- coding: utf-8 -*-
import logging
import time
import config
from common import get_nick_from_object
from plugin_system import pluginfunction, ptypes
log = logging.getLogger(__name__)


@pluginfunction('send_record', 'delivers previously saved message to user', ptypes.MUC_ONLINE)
@config.config_locked
def send_record(**args):
    arg_user = args['reply_user']
    arg_user_key = arg_user.lower()
    user_records = config.runtimeconf_get('user_records')

    if arg_user_key in user_records:
        records = user_records[arg_user_key]

        if not records:
            return None

        response = {
            'msg': '%s, there %s %d message%s for you:\n%s' % (
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


@pluginfunction(
    'record', 'record a message for a now offline user (usage: record {user} {some message};'
              ' {some message} == "previous" to use the last channel message)', ptypes.COMMAND)
@config.config_locked
def command_record(argv, **args):
    if len(argv) < 2:
        return {
            'msg': '%s: usage: record {user} {some message}' % args['reply_user']
        }

    target_user = argv[0].lower().strip(':').strip('\u200e')
    message = '{} ({}): '.format(args['reply_user'], time.strftime('%Y-%m-%d %H:%M'))
    if argv[1] == "previous":
        prev_message_obj = args['stack'][-1]
        message += '[{}]: '.format(get_nick_from_object(prev_message_obj))
        message += prev_message_obj['body']
    else:
        message += ' '.join(argv[1:])

    if target_user not in config.runtime_config_store['user_records']:
        config.runtime_config_store['user_records'][target_user] = []

    config.runtime_config_store['user_records'][target_user].append(message)

    config.runtimeconf_persist()

    return {
        'msg': '%s: message saved for %s' % (args['reply_user'], target_user)
    }


@pluginfunction('show-records', 'show current offline records', ptypes.COMMAND)
def command_show_recordlist(argv, **args):
    log.info('sent offline records list')

    user = None if not argv else argv[0]

    return {
        'msg':
            '%s: offline records%s: %s' % (
                args['reply_user'],
                '' if not user else ' (limited to %s)' % user,
                ', '.join(
                    [
                        '%s (%d)' % (key, len(val)) for key, val in config.runtime_config_store['user_records'].items()
                        if not user or user.lower() in key.lower()
                        ]
                )
            )
    }
