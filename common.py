# -*- coding: utf-8 -*-
""" Common functions for urlbot """
import html.parser
import logging
import os
import pickle
import re
import sys
import time
import urllib.request
from collections import namedtuple
import config

RATE_NO_LIMIT = 0x00
RATE_GLOBAL = 0x01
RATE_NO_SILENCE = 0x02
RATE_INTERACTIVE = 0x04
RATE_CHAT = 0x08
RATE_URL = 0x10
RATE_EVENT = 0x20
RATE_FUN = 0x40

BUFSIZ = 8192
EVENTLOOP_DELAY = 0.100  # seconds
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:31.0) ' \
             'Gecko/20100101 Firefox/31.0 Iceweasel/31.0'


def conf_save(obj):
    with open(config.get('persistent_storage'), 'wb') as config_file:
        return pickle.dump(obj, config_file)


def conf_load():
    path = config.get('persistent_storage')
    if os.path.isfile(path):
        with open(path, 'rb') as fd:
            fd.seek(0)
            return pickle.load(fd)
    else:
        return {}


def conf_set(key, value):
    blob = conf_load()
    blob[key] = value
    conf_save(blob)


def conf_get(key, default=None):
    blob = conf_load()
    return blob.get(key, default)

Bucket = namedtuple("BucketConfig", ["history", "period", "max_hist_len"])

buckets = {
    # everything else
    RATE_GLOBAL: Bucket(history=[], period=60, max_hist_len=10),
    # bot writes with no visible stimuli
    RATE_NO_SILENCE: Bucket(history=[], period=10, max_hist_len=5),
    # interactive stuff like ping
    RATE_INTERACTIVE: Bucket(history=[], period=30, max_hist_len=5),
    # chitty-chat, master volume control
    RATE_CHAT: Bucket(history=[], period=10, max_hist_len=5),
    # reacting on URLs
    RATE_URL: Bucket(history=[], period=10, max_hist_len=5),
    # triggering events
    RATE_EVENT: Bucket(history=[], period=60, max_hist_len=10),
    # bot blames people, produces cake and entertains
    RATE_FUN: Bucket(history=[], period=180, max_hist_len=5),
}

rate_limit_classes = buckets.keys()


def rate_limit(rate_class=RATE_GLOBAL):
    """
    Remember N timestamps,
    if N[0] newer than now()-T then do not output, do not append.
    else pop(0); append()

    :param rate_class: the type of message to verify
    :return: False if blocked, True if allowed
    """
    if rate_class not in rate_limit_classes:
        return all(rate_limit(c) for c in rate_limit_classes if c & rate_class)

    now = time.time()
    bucket = buckets[rate_class]
    logging.getLogger(__name__).debug(
        "[ratelimit][bucket=%x][time=%s]%s",
        rate_class, now, bucket.history
    )

    if len(bucket.history) >= bucket.max_hist_len and bucket.history[0] > (now - bucket.period):
        # print("blocked")
        return False
    else:
        if bucket.history and len(bucket.history) > bucket.max_hist_len:
            bucket.history.pop(0)
        bucket.history.append(now)
        return True


def rate_limited(max_per_second):
    """
    very simple flow control context manager
    :param max_per_second: how many events per second may be executed - more are delayed
    :return:
    """
    min_interval = 1.0 / float(max_per_second)

    def decorate(func):
        lasttimecalled = [0.0]

        def ratelimitedfunction(*args, **kargs):
            elapsed = time.clock() - lasttimecalled[0]
            lefttowait = min_interval - elapsed
            if lefttowait > 0:
                time.sleep(lefttowait)
            ret = func(*args, **kargs)
            lasttimecalled[0] = time.clock()
            return ret

        return ratelimitedfunction

    return decorate


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
    try:
        request = urllib.request.Request(url)
        request.add_header('User-Agent', USER_AGENT)
        response = urllib.request.urlopen(request)
        html_text = response.read(BUFSIZ)  # ignore more than BUFSIZ
        if html_text[0] == 0x1f and html_text[1] == 0x8b:
            import zlib
            try:
                gzip_data = zlib.decompress(html_text, zlib.MAX_WBITS | 16)
            except:
                pass
            else:
                html_text = gzip_data
        response.close()
        return 0, html_text, response.headers
    except Exception as e:
        log.warn('failed: %s' % e)
        return 1, str(e), 'dummy'


def extract_title(url):
    log = logging.getLogger(__name__)
    global parser

    if 'repo/urlbot-native.git' in url:
        log.info('repo URL found: ' + url)
        return 3, 'wee, that looks like my home repo!'

    log.info('extracting title from ' + url)

    (code, html_text, headers) = fetch_page(url)

    if 1 == code:
        return 3, 'failed: %s for %s' % (html_text, url)

    if not html_text:
        return -1, 'error'

    charset = ''
    if 'content-type' in headers:
        log.debug('content-type: ' + headers['content-type'])

        if 'text/' != headers['content-type'][:len('text/')]:
            return 1, headers['content-type']

        charset = re.sub(
            r'.*charset=(?P<charset>\S+).*',
            r'\g<charset>', headers['content-type'], re.IGNORECASE
        )

    if '' != charset:
        try:
            html_text = html_text.decode(charset)
        except LookupError:
            log.warn("invalid charset in '%s': '%s'" % (headers['content-type'], charset))

    if str != type(html_text):
        html_text = str(html_text)

    result = re.match(r'.*?<title.*?>(.*?)</title>.*?', html_text, re.S | re.M | re.IGNORECASE)
    if result:
        match = result.groups()[0]

        parser = html.parser.HTMLParser()
        try:
            expanded_html = parser.unescape(match)
        except UnicodeDecodeError as e:  # idk why this can happen, but it does
            log.warn('parser.unescape() expoded here: ' + str(e))
            expanded_html = match
        return 0, expanded_html
    else:
        return 2, 'no title'
