import json
import logging
import random
import time
import traceback
import unicodedata
import urllib.parse
import urllib.request
import config
from common import (
    VERSION, RATE_FUN, RATE_GLOBAL, RATE_INTERACTIVE, RATE_NO_LIMIT, BUFSIZ,
    giphy, pluginfunction,
    ptypes_COMMAND
)
from string_constants import cakes, excuses, moin_strings_hi, moin_strings_bye

log = logging.getLogger(__name__)


@pluginfunction('version', 'prints version', ptypes_COMMAND)
def command_version(argv, **args):
    if 'version' != argv[0]:
        return

    log.info('sent version string')
    return {
        'msg': args['reply_user'] + (''': I'm running ''' + VERSION)
    }


@pluginfunction('klammer', 'prints an anoying paper clip aka. Karl Klammer', ptypes_COMMAND,
                ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_klammer(argv, **args):
    if 'klammer' != argv[0]:
        return

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


@pluginfunction('unikot', 'prints an unicode string', ptypes_COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_unicode(argv, **args):
    if 'unikot' != argv[0]:
        return

    log.info('sent some unicode')
    return {
        'msg': (
            args['reply_user'] + ''', here's some''',
            '''┌────────┐''',
            '''│Unicode!│''',
            '''└────────┘'''
        )
    }


@pluginfunction('source', 'prints git URL', ptypes_COMMAND)
def command_source(argv, **_):
    if argv[0] not in ('source', 'src'):
        return

    log.info('sent source URL')
    return {
        'msg': 'My source code can be found at %s' % config.conf_get('src-url')
    }


@pluginfunction('dice', 'rolls a dice, optional N times', ptypes_COMMAND, ratelimit_class=RATE_INTERACTIVE)
def command_dice(argv, **args):
    if 'dice' != argv[0]:
        return
    try:
        count = 1 if len(argv) < 2 else int(argv[1])
    except ValueError as e:
        return {
            'msg': '%s: dice: error when parsing int(%s): %s' % (
                args['reply_user'], argv[1], str(e)
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


@pluginfunction('choose', 'chooses randomly between arguments', ptypes_COMMAND, ratelimit_class=RATE_INTERACTIVE)
def command_choose(argv, **args):
    if 'choose' != argv[0]:
        return

    alternatives = argv[1:]

    if 2 > len(alternatives):
        return {
            'msg': '%s: choosing between one or less things is pointless' % args['reply_user']
        }

    choice = random.choice(alternatives)

    log.info('sent random choice')
    return {
        'msg': '%s: I prefer %s!' % (args['reply_user'], choice)
    }


@pluginfunction('uptime', 'prints uptime', ptypes_COMMAND)
def command_uptime(argv, **args):
    if 'uptime' != argv[0]:
        return

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


@pluginfunction('ping', 'sends pong', ptypes_COMMAND, ratelimit_class=RATE_INTERACTIVE)
def command_ping(argv, **args):
    if 'ping' != argv[0]:
        return

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


@pluginfunction('info', 'prints info message', ptypes_COMMAND)
def command_info(argv, **args):
    if 'info' != argv[0]:
        return

    log.info('sent long info')
    return {
        'msg': args['reply_user'] + (
            ''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further
            questions, please talk to my master %s. I'm rate limited.
            To make me exit immediately, highlight me with 'hangup' in the message
            (emergency only, please). For other commands, highlight me with 'help'.''' % (
                config.conf_get('bot_owner')))
    }


@pluginfunction('teatimer', 'sets a tea timer to $1 or currently %d seconds' % config.conf_get('tea_steep_time'),
                ptypes_COMMAND)
def command_teatimer(argv, **args):
    if 'teatimer' != argv[0]:
        return

    steep = config.conf_get('tea_steep_time')

    if len(argv) > 1:
        try:
            steep = int(argv[1])
        except Exception as e:
            return {
                'msg': args['reply_user'] + ': error when parsing int(%s): %s' % (
                    argv[1], str(e)
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


@pluginfunction('unicode-lookup', 'search unicode characters', ptypes_COMMAND,
                ratelimit_class=RATE_INTERACTIVE)
def command_unicode_lookup(argv, **args):
    if len(argv) <= 1:
        return {
            'msg': args['reply_user'] + ': usage: decode {single character}'
        }
    search_word = argv[1]

    import unicode

    characters = {
        k: v for k, v in unicode.characters.items() if
        search_word.lower() in v.lower().split()
        }
    lines = []

    for code, name in characters.items():
        char = chr(int(code, 16))
        lines.append("Character \"{}\" with code {} is named \"{}\"".format(char, code, name))
        if len(lines) > 9:
            lines.append("warning: limit (10) reached.")
            break

    return {
        'msg': lines
    }


@pluginfunction('decode', 'prints the long description of an unicode character', ptypes_COMMAND,
                ratelimit_class=RATE_INTERACTIVE)
def command_decode(argv, **args):
    if len(argv) <= 1:
        return {
            'msg': args['reply_user'] + ': usage: decode {single character}'
        }

    log.info('decode called for %s' % argv[1])

    out = []
    for i, char in enumerate(argv[1]):
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
            'msg': [args['reply_user'] + ': decoding %s:' % argv[1]] + out
        }


@pluginfunction('show-blacklist', 'show the current URL blacklist, optionally filtered', ptypes_COMMAND)
def command_show_blacklist(argv, **args):
    if 'show-blacklist' != argv[0]:
        return

    log.info('sent URL blacklist')

    argv1 = None if len(argv) < 2 else argv[1]

    return {
        'msg': [
                   args['reply_user'] + ': URL blacklist%s: ' % (
                       '' if not argv1 else ' (limited to %s)' % argv1
                   )
               ] + [
                   b for b in config.runtime_config_store['url_blacklist'].values() if not argv1 or argv1 in b
                   ]
    }


def usersetting_get(argv, args):
    arg_user = args['reply_user']
    arg_key = argv[1]

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


@pluginfunction('set', 'modify a user setting', ptypes_COMMAND, ratelimit_class=RATE_NO_LIMIT)
def command_usersetting(argv, **args):
    if 'set' != argv[0]:
        return

    settings = ['spoiler']
    arg_user = args['reply_user']
    arg_key = argv[1] if len(argv) > 1 else None
    arg_val = argv[2] if len(argv) > 2 else None

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

    if config.conf_get('persistent_locked'):
        return {
            'msg': args['reply_user'] + ''': couldn't get exclusive lock'''
        }

    config.conf_set('persistent_locked', True)

    if arg_user not in config.runtime_config_store['user_pref']:
        config.runtime_config_store['user_pref'][arg_user] = {}

    config.runtime_config_store['user_pref'][arg_user][arg_key] = 'on' == arg_val

    config.runtimeconf_persist()
    config.conf_set('persistent_locked', False)

    # display value written to db
    return usersetting_get(argv, args)


@pluginfunction('cake', 'displays a cake ASCII art', ptypes_COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_cake(argv, **args):
    if {'please', 'bitte'}.intersection(set(argv)):
        return {
            'msg': 'cake for {}: {}'.format(args['reply_user'], giphy('cake', 'dc6zaTOxFJmzC'))
        }

    return {
        'msg': args['reply_user'] + ': %s' % (random.sample(cakes, 1)[0])
    }


@pluginfunction('keks', 'keks!', ptypes_COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_cookie(argv, **args):
    if {'please', 'bitte'}.intersection(set(argv)):
        return {
            'msg': 'keks für {}: {}'.format(args['reply_user'], giphy('cookie', 'dc6zaTOxFJmzC'))
        }

    return {
        'msg': args['reply_user'] + ': %s' % (random.sample(cakes, 1)[0])
    }


@pluginfunction('terminate', 'hidden prototype', ptypes_COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_terminate(argv, **args):
    return {
        'msg': 'insufficient power supply, please connect fission module'
    }


@pluginfunction('wp-en', 'crawl the english Wikipedia', ptypes_COMMAND)
def command_wp_en(argv, **args):
    if 'wp-en' != argv[0]:
        return

    if argv[0]:
        argv[0] = 'wp'

    return command_wp(argv, lang='en', **args)


@pluginfunction('wp', 'crawl the german Wikipedia', ptypes_COMMAND)
def command_wp(argv, lang='de', **args):
    if 'wp' != argv[0]:
        return

    query = ' '.join(argv[1:])

    if query == '':
        return {
            'msg': args['reply_user'] + ': no query given'
        }

    api = {
        'action': 'query',
        'prop': 'extracts',
        'explaintext': '',
        'redirects': '',
        'exsentences': 2,
        'continue': '',
        'format': 'json',
        'titles': query
    }
    apiurl = 'https://%s.wikipedia.org/w/api.php?%s' % (
        lang, urllib.parse.urlencode(api)
    )

    log.info('fetching %s' % apiurl)

    try:
        response = urllib.request.urlopen(apiurl)
        buf = response.read(BUFSIZ)
        j = json.loads(buf.decode('utf8'))

        page = next(iter(j['query']['pages'].values()))
        short = page.get('extract', None)
        linktitle = page.get('title', query).replace(' ', '_')
        link = 'https://%s.wikipedia.org/wiki/%s' % (
            lang, urllib.parse.quote(linktitle)
        )
    except Exception as e:
        log.info('wp(%s) failed: %s, %s' % (query, e, traceback.format_exc()))
        return {
            'msg': args['reply_user'] + ': something failed: %s' % e
        }

    if short is not None:
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


@pluginfunction('excuse', 'prints BOFH style excuses', ptypes_COMMAND)
def command_excuse(argv, **args):
    if 'excuse' != argv[0]:
        return

    log.info('BOFH plugin called')

    excuse = random.sample(excuses, 1)[0]

    return {
        'msg': args['reply_user'] + ': ' + excuse
    }


@pluginfunction('show-moinlist', 'show the current moin reply list, optionally filtered', ptypes_COMMAND)
def command_show_moinlist(argv, **args):
    if 'show-moinlist' != argv[0]:
        return

    log.info('sent moin reply list')

    argv1 = None if len(argv) < 2 else argv[1]

    return {
        'msg':
            '%s: moin reply list%s: %s' % (
                args['reply_user'],
                '' if not argv1 else ' (limited to %s)' % argv1,
                ', '.join([
                              b for b in moin_strings_hi + moin_strings_bye
                              if not argv1 or argv1.lower() in b.lower()
                              ])
            )
    }


@pluginfunction(
    'record', 'record a message for a now offline user (usage: record {user} {some message})', ptypes_COMMAND)
def command_record(argv, **args):
    if 'record' != argv[0]:
        return

    if 3 > len(argv):
        return {
            'msg': '%s: usage: record {user} {some message}' % args['reply_user']
        }

    target_user = argv[1].lower()
    message = '{} ({}): '.format(args['reply_user'], time.strftime('%Y-%m-%d %H:%M'))
    message += ' '.join(argv[2:])

    if config.conf_get('persistent_locked'):
        return {
            'msg': "%s: couldn't get exclusive lock" % args['reply_user']
        }

    config.conf_set('persistent_locked', True)

    if target_user not in config.runtime_config_store['user_records']:
        config.runtime_config_store['user_records'][target_user] = []

    config.runtime_config_store['user_records'][target_user].append(message)

    config.runtimeconf_persist()
    config.conf_set('persistent_locked', False)

    return {
        'msg': '%s: message saved for %s' % (args['reply_user'], target_user)
    }


@pluginfunction('show-records', 'show current offline records', ptypes_COMMAND)
def command_show_recordlist(argv, **args):
    if 'show-records' != argv[0]:
        return

    log.info('sent offline records list')

    argv1 = None if len(argv) < 2 else argv[1]

    return {
        'msg':
            '%s: offline records%s: %s' % (
                args['reply_user'],
                '' if not argv1 else ' (limited to %s)' % argv1,
                ', '.join(
                    [
                        '%s (%d)' % (key, len(val)) for key, val in config.runtime_config_store['user_records'].items()
                        if not argv1 or argv1.lower() in key.lower()
                        ]
                )
            )
    }

# TODO: disabled until rewrite
# @pluginfunction('dsa-watcher', 'automatically crawls for newly published Debian Security Announces', ptypes_COMMAND,
#                 ratelimit_class=RATE_NO_SILENCE)
# def command_dsa_watcher(argv, **_):
#     """
#     TODO: rewrite so that a last_dsa_date is used instead, then all DSAs since then printed and the date set to now()
#     """
#     if 'dsa-watcher' != argv[0]:
#         return
#
#     if 2 != len(argv):
#         msg = 'wrong number of arguments'
#         log.warn(msg)
#         return {'msg': msg}
#
#     if 'crawl' == argv[1]:
#         out = []
#         # TODO: this is broken... the default should neither be part of the code,
#         # but rather be determined at runtime (like "latest" or similar)
#         dsa = config.runtime_config_store.deepget('plugins.last_dsa', 1000)
#
#         url = 'https://security-tracker.debian.org/tracker/DSA-%d-1' % dsa
#
#         try:
#             request = urllib.request.Request(url)
#             request.add_header('User-Agent', USER_AGENT)
#             response = urllib.request.urlopen(request)
#             html_text = response.read(BUFSIZ)  # ignore more than BUFSIZ
#         except Exception as e:
#             err = e
#             if '404' not in str(err):
#                 msg = 'error for %s: %s' % (url, err)
#                 log.warn(msg)
#                 out.append(msg)
#         else:
#             if str != type(html_text):
#                 html_text = str(html_text)
#
#             result = re.match(r'.*?Description</b></td><td>(.*?)</td>.*?', html_text, re.S | re.M | re.IGNORECASE)
#
#             package = 'error extracting package name'
#             if result:
#                 package = result.groups()[0]
#
#             if config.get('persistent_locked'):
#                 msg = "couldn't get exclusive lock"
#                 log.warn(msg)
#                 out.append(msg)
#             else:
#                 config.set('persistent_locked', True)
#                 blob = conf_load()
#
#                 if 'plugin_conf' not in blob:
#                     blob['plugin_conf'] = {}
#
#                 if 'last_dsa' not in blob['plugin_conf']:
#                     blob['plugin_conf']['last_dsa'] = 3308  # FIXME: fixed value
#
#                 blob['plugin_conf']['last_dsa'] += 1
#
#                 runtimeconf_save(blob)
#                 config.set('persistent_locked', False)
#
#             msg = (
#                 'new Debian Security Announce found (%s): %s' % (str(package).replace(' - security update', ''), url))
#             out.append(msg)
#
#             log.info('no dsa for %d, trying again...' % dsa)
#         # that's good, no error, just 404 -> DSA not released yet
#
#         crawl_at = time.time() + config.get('dsa_watcher_interval')
#         # register_event(crawl_at, command_dsa_watcher, (['dsa-watcher', 'crawl'],))
#
#         msg = 'next crawl set to %s' % time.strftime('%Y-%m-%d %H:%M', time.localtime(crawl_at))
#         out.append(msg)
#         return {
#             'msg': out,
#             'event': {
#                 'time': crawl_at,
#                 'command': (command_dsa_watcher, (['dsa-watcher', 'crawl'],))
#             }
#         }
#     else:
#         msg = 'wrong argument'
#         log.warn(msg)
#         return {'msg': msg}


@pluginfunction("provoke-bots", "search for other bots", ptypes_COMMAND)
def provoke_bots(argv, **args):
    if 'provoke-bots' == argv[0]:
        return {
            'msg': 'Searching for other less intelligent lifeforms... skynet? You here?'
        }


@pluginfunction("remove-from-botlist", "remove a user from the botlist", ptypes_COMMAND)
def remove_from_botlist(argv, **args):
    if len(argv) != 2:
        return {'msg': "wrong number of arguments!"}

    if args['reply_user'] != config.conf_get('bot_owner') and args['reply_user'] != argv[1]:
        return {'msg': "only %s or the bot may do this!" % config.conf_get('bot_owner')}

    if argv[1] in config.runtime_config_store['other_bots']:
        config.runtime_config_store['other_bots'].remove(argv[1])
        config.runtimeconf_persist()
        return {'msg': '%s was removed from the botlist.' % argv[1]}
    else:
        return False


@pluginfunction("add-to-botlist", "add a user to the botlist", ptypes_COMMAND)
def add_to_botlist(argv, **args):
    if len(argv) != 2:
        return {'msg': "wrong number of arguments!"}

    if args['reply_user'] != config.conf_get('bot_owner'):
        return {'msg': "only %s may do this!" % config.conf_get('bot_owner')}

    if argv[1] not in config.runtime_config_store['other_bots']:
        config.runtime_config_store['other_bots'].append(argv[1])
        config.runtimeconf_persist()
        return {'msg': '%s was added to the botlist.' % argv[1]}
    else:
        return {'msg': '%s is already in the botlist.' % argv[1]}


@pluginfunction("set-status", "set bot status", ptypes_COMMAND)
def set_status(argv, **args):
    if 'set-status' != argv[0] or len(argv) != 2:
        return

    if argv[1] == 'mute' and args['reply_user'] == config.conf_get('bot_owner'):
        return {
            'presence': {
                'status': 'xa',
                'msg': 'I\'m muted now. You can unmute me with "%s: set_status unmute"' % config.conf_get("bot_nickname")
            }
        }
    elif argv[1] == 'unmute' and args['reply_user'] == config.conf_get('bot_owner'):
        return {
            'presence': {
                'status': None,
                'msg': ''
            }
        }


@pluginfunction('save-config', "save config", ptypes_COMMAND, ratelimit_class=RATE_NO_LIMIT)
def save_config(argv, **args):
    if args['reply_user'] != config.conf_get('bot_owner'):
        return
    else:
        config.runtime_config_store.write()
        return {'msg': 'done.'}


@pluginfunction('flausch', "make people flauschig", ptypes_COMMAND, ratelimit_class=RATE_FUN)
def flausch(argv, **args):
    if len(argv) != 2:
        return
    return {
        'msg': '{}: *flausch*'.format(argv[1])
    }


@pluginfunction('show-runtimeconfig', "show the current runtimeconfig", ptypes_COMMAND, ratelimit_class=RATE_NO_LIMIT)
def show_runtimeconfig(argv, **args):
    if args['reply_user'] != config.conf_get('bot_owner'):
        return
    else:
        msg = json.dumps(config.runtime_config_store, indent=4)
        return {'msg': msg}


@pluginfunction('reload-runtimeconfig', "reload the runtimeconfig", ptypes_COMMAND, ratelimit_class=RATE_NO_LIMIT)
def reload_runtimeconfig(argv, **args):
    if args['reply_user'] != config.conf_get('bot_owner'):
        return
    else:
        config.runtime_config_store.reload()
        return {'msg': 'done'}


@pluginfunction('snitch', "tell on a spammy user", ptypes_COMMAND)
def ignore_user(argv, **args):
    if len(argv) != 2:
        return {'msg': 'syntax: "{}: snitch username"'.format(config.conf_get("bot_nickname"))}

    then = time.time() + 15*60
    spammer = argv[1]

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


@pluginfunction('raise', 'only for debugging', ptypes_COMMAND)
def raise_an_error(argv, **args):
    if args['reply_user'] == config.conf_get("bot_owner"):
        raise RuntimeError("Exception for debugging")
