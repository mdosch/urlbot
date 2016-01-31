import logging
import random
import re
import time

import config
from common import RATE_NO_SILENCE, RATE_GLOBAL, extract_title, RATE_FUN, RATE_URL, pluginfunction, ptypes_PARSE
from config import runtimeconf_get
from plugins import ptypes_PARSE, quiz
from string_constants import moin_strings_hi, moin_strings_bye

log = logging.getLogger(__name__)


@pluginfunction('mental_ill', 'parse mental illness', ptypes_PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
def parse_mental_ill(**args):
    min_ill = 3
    c = 0
    flag = False

    # return True for min_ill '!' in a row
    for d in args['data']:
        if '!' == d or '?' == d:
            c += 1
        else:
            c = 0
        if min_ill <= c:
            flag = True
            break

    if flag:
        log.info('sent mental illness reply')
        return {
            'msg': (
                'Multiple exclamation/question marks are a sure sign of mental disease, with %s as a living example.' %
                args['reply_user']
            )
        }


@pluginfunction('debbug', 'parse Debian bug numbers', ptypes_PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
def parse_debbug(**args):
    bugs = re.findall(r'#(\d{4,})', args['data'])
    if not bugs:
        return None

    out = []
    for b in bugs:
        log.info('detected Debian bug #%s' % b)

        url = 'https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=%s' % b
        status, title = extract_title(url)

        if 0 == status:
            out.append('Debian Bug: %s: %s' % (title, url))
        elif 3 == status:
            out.append('error for #%s: %s' % (b, title))
        else:
            log.info('unknown status %d' % status)

    return {
        'msg': out
    }


@pluginfunction('cve', 'parse a CVE handle', ptypes_PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
def parse_cve(**args):
    cves = re.findall(r'(CVE-\d\d\d\d-\d+)', args['data'].upper())
    if not cves:
        return None

    log.info('detected CVE handle')
    return {
        'msg': ['https://security-tracker.debian.org/tracker/%s' % c for c in cves]
    }


@pluginfunction('dsa', 'parse a DSA handle', ptypes_PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
def parse_dsa(**args):
    dsas = re.findall(r'(DSA-\d\d\d\d-\d+)', args['data'].upper())
    if not dsas:
        return None

    log.info('detected DSA handle')
    return {
        'msg': ['https://security-tracker.debian.org/tracker/%s' % d for d in dsas]
    }


@pluginfunction('skynet', 'parse skynet', ptypes_PARSE, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def parse_skynet(**args):
    if 'skynet' in args['data'].lower():
        return {
            'msg': 'I\'ll be back.'
        }


@pluginfunction('moin', 'parse hi/bye', ptypes_PARSE, enabled=False)
def parse_moin(**args):
    for direction in [moin_strings_hi, moin_strings_bye]:
        for d in direction:
            words = re.split(r'\W+', args['data'])

            # assumption: longer sentences are not greetings
            if 3 < len(args['data'].split()):
                continue

            for w in words:
                if d.lower() == w.lower():
                    if args['reply_user'] in config.conf_get('moin-disabled-user'):
                        log.info('moin blacklist match')
                        return

                    if args['reply_user'] in config.conf_get('moin-modified-user'):
                        log.info('being "quiet" for %s' % w)
                        return {
                            'msg': '/me %s' % random.choice([
                                "doesn't say anything at all",
                                'whistles uninterested',
                                'just ignores this incident'
                            ])
                        }

                    log.info('sent %s reply for %s' % (
                        'hi' if direction is moin_strings_hi else 'bye', w
                    ))
                    return {
                        'msg': '''%s, %s''' % (
                            random.choice(direction),
                            args['reply_user']
                        )
                    }


@pluginfunction('latex', r'reacts on \LaTeX', ptypes_PARSE, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def parse_latex(**args):
    if r'\LaTeX' in args['data']:
        return {
            'msg': '''LaTeX is way too complex for me, I'm happy with fmt(1)'''
        }


@pluginfunction('me-action', 'reacts to /me.*%{bot_nickname}', ptypes_PARSE, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def parse_slash_me(**args):
    if args['data'].lower().startswith('/me') and (config.conf_get('bot_nickname') in args['data'].lower()):
        log.info('sent /me reply')

        me_replys = [
            'are you that rude to everybody?',
            'oh, thank you...',
            'do you really think that was nice?',
            'that sounds very interesting...',
            "excuse me, but I'm already late for an appointment"
        ]

        return {
            'msg': args['reply_user'] + ': %s' % random.choice(me_replys)
        }


@pluginfunction("recognize_bots", "got ya", ptypes_PARSE)
def recognize_bots(**args):
    unique_standard_phrases = (
        'independent bot and have nothing to do with other artificial intelligence systems',
        'new Debian Security Announce',
        'I\'m a bot (highlight me',
    )

    def _add_to_list(username, message):
        if username not in config.runtime_config_store['other_bots']:
            config.runtime_config_store['other_bots'].append(username)
            config.runtimeconf_persist()
            log.info("Adding {} to the list of bots (now {})".format(username, config.runtime_config_store['other_bots']))
            return {
                'event': {
                    'time': time.time() + 3,
                    'msg': message
                }
            }

    if any([phrase in args['data'] for phrase in unique_standard_phrases]):
        return _add_to_list(args['reply_user'], 'Making notes...')
    elif 'I\'ll be back' in args['data']:
        return _add_to_list(args['reply_user'], 'Hey there, buddy!')


@pluginfunction('resolve-url-title', 'extract titles from urls', ptypes_PARSE, ratelimit_class=RATE_URL)
def resolve_url_title(**args):
    user = args['reply_user']
    user_pref_nospoiler = runtimeconf_get('user_pref', {}).get(user, {}).get('spoiler', False)
    if user_pref_nospoiler:
        log.info('nospoiler in userconf')
        return

    result = re.findall(r'(https?://[^\s>]+)', args['data'])
    if not result:
        return

    url_blacklist = config.runtime_config_store['url_blacklist'].values()

    out = []
    for url in result:
        if any([re.match(b, url) for b in url_blacklist]):
            log.info('url blacklist match for ' + url)
            break
        try:
            title = extract_title(url)
        except UnicodeError as e:
            message = 'Bug triggered (%s), invalid URL/domain part: %s' % (str(e), url)
            log.warn(message)
            return {'msg': message}

        if title:
            title = title.strip()
            message = 'Title: %s' % title
            message = message.replace('\n', '\\n')
            out.append(message)

    return {
        'msg': out
    }


@pluginfunction('quizparser', 'react on chat during quiz games', ptypes_PARSE)
def quizparser(**args):
    with config.plugin_config('quiz') as quizcfg:
        current_quiz_question = quiz.get_current_question(quizcfg)
        if current_quiz_question is None:
            return
        else:
            return quiz.rate(quizcfg, args['data'], args['reply_user'])
