# -*- coding: utf-8 -*-
import logging

import events
import json
import random
import time
import traceback
import unicodedata
from urllib.parse import urlparse
import requests
from lxml import etree

import config
from common import VERSION
from rate_limit import RATE_FUN, RATE_GLOBAL, RATE_INTERACTIVE, RATE_NO_SILENCE, RATE_NO_LIMIT
from plugin_system import pluginfunction, ptypes, plugin_storage, plugin_enabled_get, plugin_enabled_set

log = logging.getLogger(__name__)


@pluginfunction('help', 'print help for a command or all known commands', ptypes.COMMAND)
def command_help(argv, **args):
    what = argv[0] if argv else None

    if not what:
        log.info('empty help request, sent all commands')
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

    for p in plugin_storage[ptypes.COMMAND] + plugin_storage[ptypes.PARSE]:
        if what == p.plugin_name:
            log.info('sent help for %s' % what)
            return {
                'msg': args['reply_user'] + ': help for %s %s %s: %s' % (
                    'enabled' if plugin_enabled_get(p) else 'disabled',
                    'parser' if p.plugin_type == ptypes.PARSE else 'command',
                    what, p.plugin_desc
                )
            }
    log.info('no help found for %s' % what)
    return {
        'msg': args['reply_user'] + ': no such command: %s' % what
    }


@pluginfunction('plugin', "'disable' or 'enable' plugins", ptypes.COMMAND)
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

    for p in plugin_storage[ptypes.COMMAND] + plugin_storage[ptypes.PARSE]:
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


@pluginfunction('list', 'list plugin and parser status', ptypes.COMMAND)
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
        out_command = plugin_storage[ptypes.COMMAND]
    if 'parser' in argv:
        out_parser = plugin_storage[ptypes.PARSE]
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


@pluginfunction('reset-jobs', "reset joblist", ptypes.COMMAND, ratelimit_class=RATE_NO_LIMIT)
def reset_jobs(argv, **args):
    if args['reply_user'] != config.conf_get('bot_owner'):
        return
    else:
        for event in events.event_list.queue:
            events.event_list.cancel(event)

        return {'msg': 'done.'}


@pluginfunction('version', 'prints version', ptypes.COMMAND)
def command_version(argv, **args):
    log.info('sent version string')
    return {
        'msg': args['reply_user'] + (''': I'm running ''' + VERSION)
    }


@pluginfunction('uptime', 'prints uptime', ptypes.COMMAND)
def command_uptime(argv, **args):
    u = int(config.runtimeconf_get('start_time') + time.time())
    plural_uptime = 's'
    plural_request = 's'

    if 1 == u:
        plural_uptime = ''
    if 1 == int(config.runtimeconf_get('request_counter')):
        plural_request = ''

    log.info('sent statistics')
    return {
        'msg': args['reply_user'] + (''': happily serving for %d second%s, %d request%s so far.''' % (
            u, plural_uptime, int(config.runtimeconf_get('request_counter')), plural_request))
    }


@pluginfunction('info', 'prints info message', ptypes.COMMAND)
def command_info(argv, **args):
    log.info('sent long info')
    return {
        'msg': args['reply_user'] + (
            ''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further
            questions, please talk to my master %s. I'm rate limited.
            To make me exit immediately, highlight me with 'hangup' in the message
            (emergency only, please). For other commands, highlight me with 'help'.''' % (
                config.conf_get('bot_owner')))
    }


@pluginfunction('ping', 'sends pong', ptypes.COMMAND, ratelimit_class=RATE_INTERACTIVE)
def command_ping(argv, **args):
    rnd = random.randint(0, 3)  # 1:4
    if 0 == rnd:
        msg = args['reply_user'] + ''': peng (You're dead now.)'''
        log.info('sent pong (variant)')
    elif 1 == rnd:
        msg = args['reply_user'] + ''': I don't like you, leave me alone.'''
        log.info('sent pong (dontlike)')
    else:
        msg = args['reply_user'] + ''': pong'''
        log.info('sent pong')

    return {
        'msg': msg
    }


@pluginfunction('klammer', 'prints an anoying paper clip aka. Karl Klammer', ptypes.COMMAND,
                ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_klammer(argv, **args):
    log.info('sent karl klammer')
    return {
        'msg': (
            args['reply_user'] + ',',
            r''' _, Was moechten''',
            r'''( _\_   Sie tun?''',
            r''' \0 O\          ''',
            r'''  \\ \\  [ ] ja ''',
            r'''   \`' ) [ ] noe''',
            r'''    `''         '''
        )
    }


@pluginfunction('terminate', 'hidden prototype', ptypes.COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_terminate(argv, **args):
    return {
        'msg': 'insufficient power supply, please connect fission module'
    }


@pluginfunction('source', 'prints git URL', ptypes.COMMAND)
def command_source(argv, **_):
    log.info('sent source URL')
    return {
        'msg': 'My source code can be found at %s' % config.conf_get('src-url')
    }


@pluginfunction('unikot', 'prints an unicode string', ptypes.COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_unicode(argv, **args):
    log.info('sent some unicode')
    return {
        'msg': (
            args['reply_user'] + ''', here's some''',
            '''┌────────┐''',
            '''│Unicode!│''',
            '''└────────┘'''
        )
    }


@pluginfunction('dice', 'rolls a dice, optional N times', ptypes.COMMAND, ratelimit_class=RATE_INTERACTIVE)
def command_dice(argv, **args):
    try:
        count = 1 if not argv else int(argv[0])
    except ValueError as e:
        return {
            'msg': '%s: dice: error when parsing int(%s): %s' % (
                args['reply_user'], argv[0], str(e)
            )
        }

    if 0 >= count or 5 <= count:
        return {
            'msg': '%s: dice: invalid arguments (0 < N < 5)' % args['reply_user']
        }

    dice_char = ['◇', '⚀', '⚁', '⚂', '⚃', '⚄', '⚅']

    msg = 'rolling %s for %s:' % (
        'a dice' if 1 == count else '%d dices' % count, args['reply_user']
    )

    for i in range(count):
        if args['reply_user'] in config.conf_get('enhanced-random-user'):
            rnd = 0  # this might confuse users. good.
            log.info('sent random (enhanced)')
        else:
            rnd = random.randint(1, 6)
            log.info('sent random')

        # the \u200b chars ('ZERO WIDTH SPACE') avoid interpreting stuff as smileys
        # by some strange clients
        msg += ' %s (\u200b%d\u200b)' % (dice_char[rnd], rnd)

    return {
        'msg': msg
    }


@pluginfunction('choose', 'chooses randomly between arguments', ptypes.COMMAND, ratelimit_class=RATE_INTERACTIVE)
def command_choose(argv, **args):
    alternatives = argv
    binary = ['Yes', 'No', 'Maybe']

    # single choose request
    if 'choose' not in alternatives:
        log.info('sent random choice')
        return {
            'msg': '%s: I prefer %s!' % (args['reply_user'], random.choice(alternatives))
        }

    # multiple choices
    def choose_between(options):
        responses = []
        current_choices = []

        for item in options:
            if item == 'choose':
                if len(current_choices) < 2:
                    responses.append(random.choice(binary))
                else:
                    responses.append(random.choice(current_choices))
                current_choices = []
            else:
                current_choices.append(item)
        if len(current_choices) < 2:
            responses.append(random.choice(binary))
        else:
            responses.append(random.choice(current_choices))
        return responses

    log.info('sent multiple random choices')
    return {
        'msg': '%s: My choices are: %s!' % (args['reply_user'], ', '.join(choose_between(alternatives)))
    }


@pluginfunction('teatimer', 'sets a tea timer to $1 or currently %d seconds' % config.conf_get('tea_steep_time'),
                ptypes.COMMAND)
def command_teatimer(argv, **args):
    steep = config.conf_get('tea_steep_time')

    if argv:
        try:
            steep = int(argv[0])
        except ValueError as e:
            return {
                'msg': args['reply_user'] + ': error when parsing int(%s): %s' % (
                    argv[0], str(e)
                )
            }

    ready = time.time() + steep

    try:
        log.info('tea timer set to %s' % time.strftime('%Y-%m-%d %H:%M', time.localtime(ready)))
    except (ValueError, OverflowError) as e:
        return {
            'msg': args['reply_user'] + ': time format error: ' + str(e)
        }

    return {
        'msg': args['reply_user'] + ': Tea timer set to %s' % time.strftime(
            '%Y-%m-%d %H:%M', time.localtime(ready)
        ),
        'event': {
            'time': ready,
            'msg': (args['reply_user'] + ': Your tea is ready!')
        }
    }


@pluginfunction('unicode-lookup', 'search unicode characters', ptypes.COMMAND,
                ratelimit_class=RATE_INTERACTIVE)
def command_unicode_lookup(argv, **args):
    if not argv:
        return {
            'msg': args['reply_user'] + ': usage: decode {single character}'
        }
    search_words = argv

    import unicode

    characters = {
        k: v for k, v in unicode.characters.items() if
        all([word.lower() in v.lower().split() for word in search_words])
        }
    lines = []

    for code, name in characters.items():
        char = chr(int(code, 16))
        lines.append("Character \"{}\" with code {} is named \"{}\"".format(char, code, name))
        if len(lines) > 29:
            lines.append("warning: limit (30) reached.")
            break

    if not lines:
        return {
            'msg': 'No match.'
        }
    elif len(lines) > 3:
        channel = 'priv_msg'
    else:
        channel = 'msg'
    return {
        channel: lines
    }


@pluginfunction('decode', 'prints the long description of an unicode character', ptypes.COMMAND,
                ratelimit_class=RATE_INTERACTIVE)
def command_decode(argv, **args):
    if not argv:
        return {
            'msg': args['reply_user'] + ': usage: decode {single character}'
        }
    log.info('decode called for %s' % argv[0])
    out = []
    for i, char in enumerate(argv[0]):
        if i > 9:
            out.append('... limit reached.')
            break

        char_esc = str(char.encode('unicode_escape'))[3:-1]

        if 0 == len(char_esc):
            char_esc = ''
        else:
            char_esc = ' (%s)' % char_esc

        try:
            uni_name = unicodedata.name(char)
        except Exception as e:
            log.info('decode(%s) failed: %s' % (char, e))
            out.append("can't decode %s%s: %s" % (char, char_esc, e))
            continue

        out.append('%s%s is called "%s"' % (char, char_esc, uni_name))

    if 1 == len(out):
        return {
            'msg': args['reply_user'] + ': %s' % out[0]
        }
    else:
        return {
            'msg': [args['reply_user'] + ': decoding %s:' % argv[0]] + out
        }


@pluginfunction('show-blacklist', 'show the current URL blacklist, optionally filtered', ptypes.COMMAND)
def command_show_blacklist(argv, **args):
    log.info('sent URL blacklist')
    if argv:
        urlpart = argv[0]
    else:
        urlpart = None

    return {
        'msg': [
                   args['reply_user'] + ': URL blacklist%s: ' % (
                       '' if not urlpart else ' (limited to %s)' % urlpart
                   )
               ] + [
                   b for b in config.runtime_config_store['url_blacklist'].values() if not urlpart or urlpart in b
                   ]
    }


def usersetting_get(argv, args):
    arg_user = args['reply_user']
    arg_key = argv[0]

    if arg_user not in config.runtime_config_store['user_pref']:
        return {
            'msg': args['reply_user'] + ': user key not found'
        }

    return {
        'msg': args['reply_user'] + ': %s == %s' % (
            arg_key,
            'on' if config.runtime_config_store['user_pref'][arg_user][arg_key] else 'off'
        )
    }


@pluginfunction('set', 'modify a user setting', ptypes.COMMAND, ratelimit_class=RATE_NO_LIMIT)
@config.config_locked
def command_usersetting(argv, **args):
    settings = ['spoiler']
    arg_user = args['reply_user']
    arg_key = argv[0] if len(argv) > 0 else None
    arg_val = argv[1] if len(argv) > 1 else None

    if arg_key not in settings:
        return {
            'msg': args['reply_user'] + ': known settings: ' + (', '.join(settings))
        }

    if arg_val not in ['on', 'off', None]:
        return {
            'msg': args['reply_user'] + ': possible values for %s: on, off' % arg_key
        }

    if not arg_val:
        # display current value
        return usersetting_get(argv, args)

    if arg_user not in config.runtime_config_store['user_pref']:
        config.runtime_config_store['user_pref'][arg_user] = {}

    config.runtime_config_store['user_pref'][arg_user][arg_key] = 'on' == arg_val

    config.runtimeconf_persist()

    # display value written to db
    return usersetting_get(argv, args)


@pluginfunction('wp-en', 'crawl the english Wikipedia', ptypes.COMMAND)
def command_wp_en(argv, **args):
    return command_wp(argv, lang='en', **args)


@pluginfunction('wp', 'crawl the german Wikipedia', ptypes.COMMAND)
def command_wp(argv, lang='de', **args):
    query = ' '.join(argv)

    if query == '':
        return {
            'msg': args['reply_user'] + ': no query given'
        }

    apiparams = {
        'action': 'query',
        'prop': 'extracts|info',
        'explaintext': '',
        'redirects': '',
        'exsentences': 2,
        'continue': '',
        'format': 'json',
        'titles': query,
        'inprop': 'url'
    }
    apiurl = 'https://%s.wikipedia.org/w/api.php' % (lang)

    log.info('fetching %s' % apiurl)

    try:
        response = requests.get(apiurl, params=apiparams).json()

        page = next(iter(response['query']['pages'].values()))
        short = page.get('extract')
        link = page.get('canonicalurl')
    except Exception as e:
        log.info('wp(%s) failed: %s, %s' % (query, e, traceback.format_exc()))
        return {
            'msg': args['reply_user'] + ': something failed: %s' % e
        }

    if short:
        return {
            'msg': args['reply_user'] + ': %s (<%s>)' % (
                short if short.strip() else '(nix)', link
            )
        }
    elif 'missing' in page:
        return {
            'msg': 'Article "%s" not found' % page.get('title', query)
        }
    else:
        return {
            'msg': 'json data seem to be broken'
        }


@pluginfunction(
    'dsa-watcher',
    'automatically crawls for newly published Debian Security Announces', ptypes.COMMAND,
    ratelimit_class=RATE_NO_SILENCE, enabled=True)
def command_dsa_watcher(argv=None, **_):
    """
    TODO: rewrite so that a last_dsa_date is used instead,
    then all DSAs since then printed and the date set to now()
    :param argv:
    :param _:
    """
    log.debug("Called command_dsa_watcher")

    def get_id_from_about_string(about):
        return int(about.split('/')[-1].split('-')[1])

    def get_dsa_list(after):
        """
        Get a list of dsa items in form of id and package, retrieved from the RSS feed
        :param after: optional integer to filter on (only DSA's after that will be returned)
        :returns list of id, package (with DSA prefix)
        """
        nsmap = {
            "purl": "http://purl.org/rss/1.0/",
            "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        }
        dsa_response = requests.get("https://www.debian.org/security/dsa-long")
        xmldoc = etree.fromstring(dsa_response.content)
        dsa_about_list = xmldoc.xpath('//purl:item/@rdf:about', namespaces=nsmap)
        for dsa_about in reversed(dsa_about_list):
            dsa_id = get_id_from_about_string(dsa_about)
            title = xmldoc.xpath(
                '//purl:item[@rdf:about="{}"]/purl:title/text()'.format(dsa_about),
                namespaces=nsmap
            )[0]
            if after and dsa_id <= after:
                continue
            else:
                yield dsa_id, str(title).replace(' - security update', '')

    out = []
    last_dsa = config.runtimeconf_deepget('plugins.dsa-watcher.last_dsa')
    log.debug('Searching for DSA after ID {}'.format(last_dsa))
    for dsa, package in get_dsa_list(after=last_dsa):
        url = 'https://security-tracker.debian.org/tracker/DSA-%d-1' % dsa

        msg = 'new Debian Security Announce found ({}): {}'.format(package, url)
        out.append(msg)

        last_dsa = dsa

    config.runtime_config_store['plugins']['dsa-watcher']['last_dsa'] = last_dsa
    config.runtimeconf_persist()
    crawl_at = time.time() + config.runtimeconf_deepget('plugins.dsa-watcher.interval')

    msg = 'next crawl set to %s' % time.strftime('%Y-%m-%d %H:%M', time.localtime(crawl_at))
    out.append(msg)
    return {
        'event': {
            'time': crawl_at,
            'command': (command_dsa_watcher, ([],))
        }
    }


@pluginfunction("provoke-bots", "search for other bots", ptypes.COMMAND)
def provoke_bots(argv, **args):
    return {
        'msg': 'Searching for other less intelligent lifeforms... skynet? You here?'
    }


@pluginfunction("remove-from-botlist", "remove a user from the botlist", ptypes.COMMAND)
def remove_from_botlist(argv, **args):
    if not argv:
        return {'msg': "wrong number of arguments!"}
    suspect = argv[0]

    if args['reply_user'] != config.conf_get('bot_owner') and args['reply_user'] != suspect:
        return {'msg': "only %s or the bot may do this!" % config.conf_get('bot_owner')}

    if suspect in config.runtime_config_store['other_bots']:
        config.runtime_config_store['other_bots'].remove(suspect)
        config.runtimeconf_persist()
        return {'msg': '%s was removed from the botlist.' % suspect}
    else:
        return False


@pluginfunction("add-to-botlist", "add a user to the botlist", ptypes.COMMAND, enabled=False)
def add_to_botlist(argv, **args):
    return {'msg': 'feature disabled until channel separation'}
    if not argv:
        return {'msg': "wrong number of arguments!"}
    suspect = argv[0]

    if args['reply_user'] != config.conf_get('bot_owner'):
        return {'msg': "only %s may do this!" % config.conf_get('bot_owner')}

    if suspect not in config.runtime_config_store['other_bots']:
        config.runtime_config_store['other_bots'].append(suspect)
        config.runtimeconf_persist()
        return {'msg': '%s was added to the botlist.' % suspect}
    else:
        return {'msg': '%s is already in the botlist.' % suspect}


@pluginfunction("set-status", "set bot status", ptypes.COMMAND)
def set_status(argv, **args):
    if not argv:
        return
    else:
        command = argv[0]

    if command == 'mute' and args['reply_user'] == config.conf_get('bot_owner'):
        return {
            'presence': {
                'status': 'xa',
                'msg': 'I\'m muted now. You can unmute me with "%s: set_status unmute"' % config.conf_get(
                    "bot_nickname")
            }
        }
    elif command == 'unmute' and args['reply_user'] == config.conf_get('bot_owner'):
        return {
            'presence': {
                'status': None,
                'msg': ''
            }
        }


@pluginfunction('save-config', "save config", ptypes.COMMAND, ratelimit_class=RATE_NO_LIMIT)
def save_config(argv, **args):
    if args['reply_user'] != config.conf_get('bot_owner'):
        return
    else:
        config.runtime_config_store.write()
        return {'msg': 'done.'}


@pluginfunction('flausch', "make people flauschig", ptypes.COMMAND, ratelimit_class=RATE_FUN)
def flausch(argv, **args):
    if not argv:
        return
    return {
        'msg': '{}: *flausch*'.format(argv[0])
    }


@pluginfunction('slap', "slap people", ptypes.COMMAND, ratelimit_class=RATE_FUN)
def slap(argv, **args):
    if not argv:
        return
    return {
        'msg': '/me slaps {}'.format(argv[0])
    }


@pluginfunction('show-runtimeconfig', "show the current runtimeconfig", ptypes.COMMAND, ratelimit_class=RATE_NO_LIMIT)
def show_runtimeconfig(argv, **args):
    if args['reply_user'] != config.conf_get('bot_owner'):
        return
    else:
        msg = json.dumps(config.runtime_config_store, indent=4)
        return {'priv_msg': msg}


@pluginfunction('reload-runtimeconfig', "reload the runtimeconfig", ptypes.COMMAND, ratelimit_class=RATE_NO_LIMIT)
def reload_runtimeconfig(argv, **args):
    if args['reply_user'] != config.conf_get('bot_owner'):
        return
    else:
        config.runtime_config_store.reload()
        return {'msg': 'done'}


@pluginfunction('snitch', "tell on a spammy user", ptypes.COMMAND)
def ignore_user(argv, **args):
    if not argv:
        return {'msg': 'syntax: "{}: snitch username"'.format(config.conf_get("bot_nickname"))}

    then = time.time() + 15 * 60
    spammer = argv[0]

    if spammer == config.conf_get("bot_owner"):
        return {
            'msg': 'My owner does not spam, he is just very informative.'
        }

    if spammer not in config.runtime_config_store['spammers']:
        config.runtime_config_store['spammers'].append(spammer)

    def unblock_user(user):
        if user not in config.runtime_config_store['spammers']:
            config.runtime_config_store['spammers'].append(user)

    return {
        'msg': 'user reported and ignored till {}'.format(time.strftime('%H:%M', time.localtime(then))),
        'event': {
            'time': then,
            'command': (unblock_user, ([spammer],))
        }
    }


@pluginfunction('search', 'search the web (using duckduckgo)', ptypes.COMMAND)
def search_the_web(argv, **args):
    url = 'http://api.duckduckgo.com/'
    params = dict(
        q=' '.join(argv),
        format='json',
        pretty=0,
        no_redirect=1,
        t='jabberbot'
    )
    response = requests.get(url, params=params).json()
    link = response.get('AbstractURL')
    abstract = response.get('Abstract')
    redirect = response.get('Redirect')

    if len(abstract) > 150:
        suffix = '…'
    else:
        suffix = ''

    if link:
        return {
            'msg': '{}{} ({})'.format(abstract[:150], suffix, link)
        }
    elif redirect:
        return {
            'msg': 'No direct result found, use {}'.format(redirect)
        }
    else:
        return {'msg': 'Sorry, no results.'}


@pluginfunction('raise', 'only for debugging', ptypes.COMMAND)
def raise_an_error(argv, **args):
    if args['reply_user'] == config.conf_get("bot_owner"):
        raise RuntimeError("Exception for debugging")


@pluginfunction('repeat', 'repeat the last message', ptypes.COMMAND, enabled=False)
def repeat_message(argv, **args):
    return {'msg': 'disabled until channel separation'}
    return {
        'msg': args['stack'][-1]['body']
    }


@pluginfunction('isdown', 'check if a website is reachable', ptypes.COMMAND)
def isdown(argv, **args):
    if not argv:
        return
    url = argv[0]
    if 'http' not in url:
        url = 'http://{}'.format(url)
    response = requests.get('http://www.isup.me/{}'.format(urlparse(url).hostname)).text
    if "looks down" in response:
        return {'msg': '{}: {} looks down'.format(args['reply_user'], url)}
    elif "is up" in response:
        return {'msg': '{}: {} looks up'.format(args['reply_user'], url)}
    elif "site on the interwho" in response:
        return {'msg': '{}: {} does not exist, you\'re trying to fool me?'.format(args['reply_user'], url)}


@pluginfunction('poll', 'create a poll', ptypes.COMMAND)
def poll(argv, **args):
    with config.plugin_config('poll') as pollcfg:
        current_poll = pollcfg.get('subject')

        if not argv:
            # return poll info
            if not current_poll:
                return {'msg': 'no poll running.'}
            else:
                return {'msg': 'current poll: {}'.format(current_poll)}
        elif len(argv) == 1:
            if argv[0] == 'stop':
                if not current_poll:
                    return {'msg': 'no poll to stop.'}
                pollcfg.clear()
                return {'msg': 'stopped the poll "{}"'.format(current_poll)}
            elif argv[0] == 'show_raw':
                if not current_poll:
                    return {'msg': 'no poll to show.'}
                return {'msg': 'current poll (raw): {}'.format(str(pollcfg))}
            elif argv[0] == 'show':
                if not current_poll:
                    return {'msg': 'no poll to show.'}
                lines = ['current poll: "{}"'.format(current_poll)]
                for option, voters in pollcfg.items():
                    if option == 'subject':
                        continue
                    lines.append('{0: <4} {1}'.format(len(voters), option))
                return {'msg': lines}
            if current_poll and argv[0] in pollcfg:
                user = args['reply_user']
                for option, voters in pollcfg.items():
                    if user in voters:
                        pollcfg[option].remove(user)

                pollcfg[argv[0]] = list(set(pollcfg[argv[0]] + [user]))
                return {'msg': 'voted.'}
        else:
            subject = argv[0]
            choices = argv[1:]
            if len(choices) == 1:
                return {'msg': 'creating a poll with a single option is "alternativlos"'}
            else:
                if current_poll:
                    return {'msg': 'a poll is already running ({})'.format(current_poll)}
                # create an item for each option
                pollcfg['subject'] = subject
                pollcfg.update({k: [] for k in choices})
                return {'msg': 'created the poll.'}


@pluginfunction('vote', 'alias for poll', ptypes.COMMAND)
def vote(argv, **args):
    return poll(argv, **args)
