# -*- coding: utf-8 -*-
""" Common functions for urlbot """
import html.parser
import logging
import re
import requests
from urllib.error import URLError
import sleekxmpp

BUFSIZ = 8192
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:31.0) ' \
             'Gecko/20100101 Firefox/31.0 Iceweasel/31.0'


def get_version_git():
    import subprocess

    cmd = ['git', 'log', '--oneline', '--abbrev-commit']

    try:
        p = subprocess.Popen(cmd, bufsize=1, stdout=subprocess.PIPE)
        first_line = p.stdout.readline()
        line_count = len(p.stdout.readlines()) + 1

        if 0 == p.wait():
            # skip this 1st, 2nd, 3rd stuff and use always [0-9]th
            return "version (Git, %dth rev) '%s'" % (
                line_count, str(first_line.strip(), encoding='utf8')
            )
        else:
            return "(unknown version)"
    except:
        return "cannot determine version"


VERSION = get_version_git()


def fetch_page(url):
    log = logging.getLogger(__name__)
    log.info('fetching page ' + url)
    response = requests.get(url, headers={'User-Agent': USER_AGENT}, stream=True, timeout=15)
    content = response.raw.read(BUFSIZ, decode_content=True)
    return content.decode(response.encoding or 'utf-8'), response.headers


def extract_title(url):
    log = logging.getLogger(__name__)
    global parser

    if 'repo/urlbot-native.git' in url:
        log.info('repo URL found: ' + url)
        return 'wee, that looks like my home repo!', []

    log.info('extracting title from ' + url)

    try:
        (html_text, headers) = fetch_page(url)
    except URLError as e:
        return None
    except UnicodeDecodeError:
        return None
    except Exception as e:
        return 'failed: %s for %s' % (str(e), url)

    if 'content-type' in headers:
        log.debug('content-type: ' + headers['content-type'])

        if 'text/' != headers['content-type'][:len('text/')]:
            return 1, headers['content-type']

    result = re.match(r'.*?<title.*?>(.*?)</title>.*?', html_text, re.S | re.M | re.IGNORECASE)
    if result:
        match = result.groups()[0]

        parser = html.parser.HTMLParser()
        try:
            expanded_html = parser.unescape(match)
        except UnicodeDecodeError as e:  # idk why this can happen, but it does
            log.warn('parser.unescape() expoded here: ' + str(e))
            expanded_html = match
        return expanded_html
    else:
        return None


def giphy(subject, api_key):
    url = 'http://api.giphy.com/v1/gifs/random?tag={}&api_key={}&limit=1&offset=0'.format(subject, api_key)
    response = requests.get(url)
    giphy_url = None
    try:
        data = response.json()
        giphy_url = data['data']['image_url']
    except:
        pass
    return giphy_url


def get_nick_from_object(message_obj):

    if isinstance(message_obj, sleekxmpp.Message):
        msg_type = message_obj.getType()

        if msg_type == "groupchat":
            return message_obj.getMucnick()
        elif msg_type == "chat":
            jid = message_obj.getFrom()
            return jid.resource
        else:
            raise Exception("Message, but not groupchat/chat")

    elif isinstance(message_obj, sleekxmpp.Presence):
        jid = message_obj.getFrom()
        return jid.resource

    else:
        raise Exception("Message type is: " + str(type(message_obj)))


def else_command(args):
    log = logging.getLogger(__name__)
    log.info('sent short info')
    return {
        'msg': args['reply_user'] + ''': I'm a bot (highlight me with 'info' for more information).'''
    }

