# -*- coding: utf-8 -*-
import html.parser
import logging
import os
import pickle
import re
import sys
import urllib.request

from local_config import conf

RATE_GLOBAL = 0x01
RATE_NO_SILENCE = 0x02
RATE_INTERACTIVE = 0x04
RATE_CHAT = 0x08
RATE_URL = 0x10

BUFSIZ = 8192
EVENTLOOP_DELAY = 0.100  # seconds
USER_AGENT = '''Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0 Iceweasel/31.0'''

basedir = '.'
if 2 == len(sys.argv):
	basedir = sys.argv[1]


def conf_save(obj):
	with open(conf('persistent_storage'), 'wb') as fd:
		return pickle.dump(obj, fd)


def conf_load():
	path = conf('persistent_storage')
	if os.path.isfile(path):
		with open(path, 'rb') as fd:
			fd.seek(0)
			return pickle.load(fd)
	else:
		return {}


def get_version_git():
	import subprocess

	cmd = ['git', 'log', '--oneline', '--abbrev-commit']

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


VERSION = get_version_git()


def fetch_page(url):
	log = logging.getLogger(__name__)
	log.info('fetching page ' + url)
	try:
		request = urllib.request.Request(url)
		request.add_header('User-Agent', USER_AGENT)
		response = urllib.request.urlopen(request)
		html_text = response.read(BUFSIZ)  # ignore more than BUFSIZ
		response.close()
		return 0, html_text, response.headers
	except Exception as e:
		log.warn('failed: %s' % e)
		return 1, str(e), 'dummy'


def extract_title(url):
	log = logging.getLogger(__name__)
	global parser

	if 'repo/urlbot.git' in url:
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

		if not parser:
			parser = html.parser.HTMLParser()
		try:
			expanded_html = parser.unescape(match)
		except UnicodeDecodeError as e:  # idk why this can happen, but it does
			log.warn('parser.unescape() expoded here: ' + str(e))
			expanded_html = match
		return 0, expanded_html
	else:
		return 2, 'no title'
