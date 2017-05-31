# -*- coding: utf-8 -*-
import logging

import random
import re
import time

import config
from common import extract_title 
from rate_limit import RATE_NO_SILENCE, RATE_GLOBAL, RATE_FUN, RATE_URL
from config import runtimeconf_get
from plugin_system import pluginfunction, ptypes
log = logging.getLogger(__name__)


@pluginfunction('mental_ill', 'parse mental illness', ptypes.PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
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


@pluginfunction('woof', '*puts sunglasses on*', ptypes.PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
def command_woof(**args):
    if 'who let the bots out' in args['data']:
        return {
            'msg': 'beeep! beep! beep! beep! beep!'
        }


@pluginfunction('debbug', 'parse Debian bug numbers', ptypes.PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
def parse_debbug(**args):
    bugs = re.findall(r'#(\d{4,})', args['data'])
    if not bugs:
        return None

    out = []
    for b in bugs:
        log.info('detected Debian bug #%s' % b)

        url = 'https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=%s' % b

        title = extract_title(url)

        if title:
            out.append('Debian Bug: %s: %s' % (title, url))

    return {
        'msg': out
    }


@pluginfunction('cve', 'parse a CVE handle', ptypes.PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
def parse_cve(**args):
    cves = re.findall(r'(CVE-\d\d\d\d-\d+)', args['data'].upper())
    if not cves:
        return None

    log.info('detected CVE handle')
    return {
        'msg': ['https://security-tracker.debian.org/tracker/%s' % c for c in cves]
    }


@pluginfunction('dsa', 'parse a DSA handle', ptypes.PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
def parse_dsa(**args):
    dsas = re.findall(r'(DSA-\d\d\d\d-\d+)', args['data'].upper())
    if not dsas:
        return None

    log.info('detected DSA handle')
    return {
        'msg': ['https://security-tracker.debian.org/tracker/%s' % d for d in dsas]
    }


@pluginfunction('skynet', 'parse skynet', ptypes.PARSE, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def parse_skynet(**args):
    if 'skynet' in args['data'].lower():
        return {
            'msg': 'I\'ll be back.'
        }


@pluginfunction('latex', r'reacts on \LaTeX', ptypes.PARSE, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def parse_latex(**args):
    if r'\LaTeX' in args['data']:
        return {
            'msg': '''LaTeX is way too complex for me, I'm happy with fmt(1)'''
        }


@pluginfunction('me-action', 'reacts to /me.*%{bot_nickname}', ptypes.PARSE, ratelimit_class=RATE_FUN | RATE_GLOBAL)
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


@pluginfunction('resolve-url-title', 'extract titles from urls', ptypes.PARSE, ratelimit_class=RATE_URL)
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
    for url in result[:10]:
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


@pluginfunction('doctor', 'parse doctor', ptypes.PARSE, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def parse_doctor(**args):
    if 'doctor' in args['data'].lower() or 'doktor' in args['data'].lower():
        return {
            'msg': 'ELIMINIEREN! ELIMINIEREN!'
        }
