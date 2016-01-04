# -*- coding: utf-8 -*-
import logging
import time
import traceback
import types

import config
from common import RATE_NO_LIMIT, pluginfunction, ptypes_PARSE, ptypes_COMMAND, ptypes
from plugins import commands, parsers

joblist = []
plugins = {p: [] for p in ptypes}
log = logging.getLogger(__name__)


def plugin_enabled_get(urlbot_plugin):
    plugin_section = config.runtimeconf_deepget('plugins.{}'.format(urlbot_plugin.plugin_name))
    if plugin_section and "enabled" in plugin_section:
        return plugin_section.as_bool("enabled")
    else:
        return urlbot_plugin.is_enabled


def plugin_enabled_set(plugin, enabled):
    if config.conf_get('persistent_locked'):
        log.warn("couldn't get exclusive lock")

    config.conf_set('persistent_locked', True)

    if plugin.plugin_name not in config.runtime_config_store['plugins']:
        config.runtime_config_store['plugins'][plugin.plugin_name] = {}

    config.runtime_config_store['plugins'][plugin.plugin_name]['enabled'] = enabled
    config.runtimeconf_persist()
    config.conf_set('persistent_locked', False)


def register_active_event(t, callback, args, action_runner, plugin, msg_obj):
    """
    Execute a callback at a given time and react on the output

    :param t: when to execute the job
    :param callback: the function to execute
    :param args: parameters for said function
    :param action_runner: bots action dict parser
    :param plugin: pass-through object for action parser
    :param msg_obj: pass-through object for action parser
    :return:
    """
    def func(func_args):
        action = callback(*func_args)
        if action:
            action_runner(action=action, plugin=plugin, msg_obj=msg_obj)
    joblist.append((t, func, args))


def register_event(t, callback, args):
    joblist.append((t, callback, args))


def else_command(args):
    log.info('sent short info')
    return {
        'msg': args['reply_user'] + ''': I'm a bot (highlight me with 'info' for more information).'''
    }


def register(func_type):
    """
    Register plugins.

    :param func_type: plugin functions with this type (ptypes) will be loaded
    """

    if func_type == ptypes_COMMAND:
        local_commands = [command_plugin_activation, command_list, command_help, reset_jobs]
        plugin_funcs = list(commands.__dict__.values()) + local_commands
    elif func_type == ptypes_PARSE:
        plugin_funcs = parsers.__dict__.values()
    else:
        raise RuntimeError("invalid func type: {}".format(func_type))

    functions = [
        f for f in plugin_funcs if
        isinstance(f, types.FunctionType) and
        all([
            f.__dict__.get('is_plugin', False),
            getattr(f, 'plugin_type', None) == func_type
        ])
        ]

    log.info('auto-reg %s: %s' % (func_type, ', '.join(
        f.plugin_name for f in functions
    )))

    for f in functions:
        register_plugin(f, func_type)


def register_plugin(function, func_type):
    try:
        plugins[func_type].append(function)
    except Exception as e:
        log.warn('registering %s failed: %s, %s' % (function, e, traceback.format_exc()))


def register_all():
    register(ptypes_PARSE)
    register(ptypes_COMMAND)


def event_trigger():
    if 0 == len(joblist):
        return True

    now = time.time()

    for (i, (t, callback, args)) in enumerate(joblist):
        if t < now:
            callback(*args)
            del (joblist[i])
    return True


@pluginfunction('help', 'print help for a command or all known commands', ptypes_COMMAND)
def command_help(argv, **args):
    what = argv[0] if argv else None
    logger = logging.getLogger(__name__)

    if not what:
        logger.info('empty help request, sent all commands')
        commands = args['cmd_list']
        commands.sort()
        parsers = args['parser_list']
        parsers.sort()
        return {
            'msg': [
                '%s: known commands: %s' % (
                    args['reply_user'], ', '.join(commands)
                ),
                'known parsers: %s' % ', '.join(parsers)
            ]
        }

    for p in plugins[ptypes_COMMAND] + plugins[ptypes_PARSE]:
        if what == p.plugin_name:
            logger.info('sent help for %s' % what)
            return {
                'msg': args['reply_user'] + ': help for %s %s %s: %s' % (
                    'enabled' if plugin_enabled_get(p) else 'disabled',
                    'parser' if p.plugin_type == ptypes_PARSE else 'command',
                    what, p.plugin_desc
                )
            }
    logger.info('no help found for %s' % what)
    return {
        'msg': args['reply_user'] + ': no such command: %s' % what
    }


@pluginfunction('plugin', "'disable' or 'enable' plugins", ptypes_COMMAND)
def command_plugin_activation(argv, **args):
    if not argv:
        return

    command = argv[0]
    plugin = argv[1] if len(argv) > 1 else None

    if command not in ('enable', 'disable'):
        return

    log.info('plugin activation plugin called')

    if not plugin:
        return {
            'msg': args['reply_user'] + ': no plugin given'
        }
    elif command_plugin_activation.plugin_name == plugin:
        return {
            'msg': args['reply_user'] + ': not allowed'
        }

    for p in plugins[ptypes_COMMAND] + plugins[ptypes_PARSE]:
        if p.plugin_name == plugin:
            plugin_enabled_set(p, 'enable' == command)

            return {
                'msg': args['reply_user'] + ': %sd %s' % (
                    command, plugin
                )
            }

    return {
        'msg': args['reply_user'] + ': unknown plugin %s' % plugin
    }


@pluginfunction('list', 'list plugin and parser status', ptypes_COMMAND)
def command_list(argv, **args):

    log.info('list plugin called')

    if 'enabled' in argv and 'disabled' in argv:
        return {
            'msg': args['reply_user'] + ": both 'enabled' and 'disabled' makes no sense"
        }

    # if not given, assume both
    if 'command' not in argv and 'parser' not in argv:
        argv.append('command')
        argv.append('parser')

    out_command = []
    out_parser = []
    if 'command' in argv:
        out_command = plugins[ptypes_COMMAND]
    if 'parser' in argv:
        out_parser = plugins[ptypes_PARSE]
    if 'enabled' in argv:
        out_command = [p for p in out_command if plugin_enabled_get(p)]
        out_parser = [p for p in out_parser if plugin_enabled_get(p)]
    if 'disabled' in argv:
        out_command = [p for p in out_command if not plugin_enabled_get(p)]
        out_parser = [p for p in out_parser if not plugin_enabled_get(p)]

    msg = [args['reply_user'] + ': list of plugins:']

    if out_command:
        msg.append('commands: %s' % ', '.join([p.plugin_name for p in out_command]))
    if out_parser:
        msg.append('parsers: %s' % ', '.join([p.plugin_name for p in out_parser]))
    return {'msg': msg}


@pluginfunction('reset-jobs', "reset joblist", ptypes_COMMAND, ratelimit_class=RATE_NO_LIMIT)
def reset_jobs(argv, **args):
    if args['reply_user'] != config.conf_get('bot_owner'):
        return
    else:
        joblist.clear()
        return {'msg': 'done.'}
