#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys, os, stat, re, time, pickle, random
import urllib.request, urllib.parse, urllib.error, html.parser
from common import *
from strsim import str_sim

try:
	from local_config import conf, set_conf
except ImportError:
	import sys
	sys.stderr.write('''
%s: E: local_config.py isn't tracked because of included secrets and
%s     site specific configurations. Rename local_config.py.skel and
%s     adjust to you needs.
'''[1:] % (
		sys.argv[0],
		' ' * len(sys.argv[0]),
		' ' * len(sys.argv[0])
	)
	)

	sys.exit(-1)

import logging

from sleekxmpp import ClientXMPP

# rate limiting to 5 messages per 10 minutes
hist_ts = []
hist_flag = True

parser = None
xmpp = None

def fetch_page(url):
	logger('info', 'fetching page ' + url)
	try:
		request = urllib.request.Request(url)
		request.add_header('User-Agent', '''Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0 Iceweasel/31.0''')
		response = urllib.request.urlopen(request)
		html_text = response.read(BUFSIZ)  # ignore more than BUFSIZ
		response.close()
		return (0, html_text, response.headers)
	except Exception as e:
		logger('warn', 'failed: ' + str(e))
		return (1, str(e), 'dummy')

	return (-1, None, None)

def extract_title(url):
	global parser

	if 'repo/urlbot.git' in url:
		logger('info', 'repo URL found: ' + url)
		return (3, 'wee, that looks like my home repo!')

	logger('info', 'extracting title from ' + url)

	(code, html_text, headers) = fetch_page(url)

	if 1 == code:
		return (3, 'failed: %s for %s' %(html_text, url))

	if html_text:
		charset = ''
		if 'content-type' in headers:
			logger('debug', 'content-type: ' + headers['content-type'])

			if 'text/' != headers['content-type'][:len('text/')]:
				return (1, headers['content-type'])

			charset = re.sub(
				'.*charset=(?P<charset>\S+).*',
				'\g<charset>', headers['content-type'], re.IGNORECASE
			)

		if '' != charset:
			try:
				html_text = html_text.decode(charset)
			except LookupError:
				logger('warn', 'invalid charset in ' + headers['content-type'])

		if str != type(html_text):
			html_text = str(html_text)

		result = re.match(r'.*?<title.*?>(.*?)</title>.*?', html_text, re.S | re.M | re.IGNORECASE)
		if result:
			match = result.groups()[0]

			if None == parser:
				parser = html.parser.HTMLParser()

			try:
				expanded_html = parser.unescape(match)
			except UnicodeDecodeError as e:  # idk why this can happen, but it does
				logger('warn', 'parser.unescape() expoded here: ' + str(e))
				expanded_html = match
			return (0, expanded_html)
		else:
			return (2, 'no title')

	return (-1, 'error')

def chat_write(message):
	set_conf('request_counter', conf('request_counter') + 1)

	for m in message:
		if 0x20 > ord(m):
			logger('warn', 'strange char 0x%02x in chat_write(message), skipping' % ord(m))
			return False

	if debug_enabled():
		print(message)
	else:
		xmpp.send_message(
			mto=conf('room'),
			mbody=message,
			mtype='groupchat'
		)

def ratelimit_touch(ignored=None):  # FIXME: separate counters
	hist_ts.append(time.time())

	if conf('hist_max_count') < len(hist_ts):
		hist_ts.pop(0)


def ratelimit_exceeded(ignored=None):  # FIXME: separate counters
	global hist_flag

	if conf('hist_max_count') < len(hist_ts):
		first = hist_ts.pop(0)
		if (time.time() - first) < conf('hist_max_time'):
			if hist_flag:
				hist_flag = False
				chat_write('(rate limited to %d messages in %d seconds, try again at %s)' %(conf('hist_max_count'), conf('hist_max_time'), time.strftime('%T %Z', time.localtime(hist_ts[0] + conf('hist_max_time')))))

			logger('warn', 'rate limiting exceeded: ' + pickle.dumps(hist_ts))
			return True

	hist_flag = True
	return False

def extract_url(data):
	ret = None
	result = re.findall("(https?://[^\s>]+)", data)
	if result:
		for url in result:
			ratelimit_touch()
			if ratelimit_exceeded():
				return False

			flag = False
			for b in conf('url_blacklist'):
				if not None is re.match(b, url):
					flag = True
					logger('info', 'url blacklist match for ' + url)

			if flag:
				# an URL has matched the blacklist, continue to the next URL
				continue

# urllib.request is broken:
# >>> '.'.encode('idna')
# ....
# UnicodeError: label empty or too long
# >>> '.a.'.encode('idna')
# ....
# UnicodeError: label empty or too long
# >>> 'a.a.'.encode('idna')
# b'a.a.'

			try:
				(status, title) = extract_title(url)
			except UnicodeError as e:
				(status, title) = (4, str(e))

			if 0 == status:
				title = title.strip()
				lev_url = re.sub(r'https?://[^/]*/', '', url)
				lev_res = levenshtein(lev_url, title)

				sim = str_sim(title, lev_url)
				sim_len_title = len(sim)
				sim_len_url = len(sim[0])
				sim_sum = sum([sum(a) for a in sim])

				obj = conf_load()
				obj['lev'].append((lev_res, title, url))
				obj['sim'].append((sim_sum, sim_len_title, sim_len_url, title, url))
				conf_save(obj)

				message = 'Title: %s: %s' %(title, url)
			elif 1 == status:
				if conf('image_preview'):
					# of course it's fake, but it looks interesting at least
					char = """,._-+=\|/*`~"'"""
					message = 'No text but %s, 1-bit ASCII art preview: [%c] %s' %(
						title, random.choice(char), url
					)
				else:
					logger('info', 'no message sent for non-text %s (%s)' %(url, title))
					continue
			elif 2 == status:
				message = 'No title: %s' % url
			elif 3 == status:
				message = title
			elif 4 == status:
				message = 'Bug triggered (%s), invalid URL/domain part: %s' % (title, url)
				logger('warn', message)
			else:
				message = 'some error occurred when fetching %s' % url

			message = message.replace('\n', '\\n')

			logger('info', 'printing ' + message)
			chat_write(message)
			ret = True
	return ret

def parse_pn(data):
# FIXME: changed
	## reply_user = data.split(' ')[0].strip('<>')
	# since we can't determine if a user named 'foo> ' just wrote ' > bar'
	# or a user 'foo' just wrote '> > bar', we can't safely answer here
	logger('warn', 'received PN: ' + data)
	return False

def handle_msg(msg):
	content = msg['body']

# FIXME: still needed?
	if 'has set the subject to:' in content:
		return

	if 'nospoiler' in content:
		logger('info', "no spoiler for: " + content)
		return

	if sys.argv[0] in content:
		logger('info', 'silenced, this is my own log')
		return

	if True != extract_url(content):
		plugins.data_parse_commands(msg)
		plugins.data_parse_other(msg)
		return

class bot(ClientXMPP):
	def __init__(self, jid, password, room, nick):
		ClientXMPP.__init__(self, jid, password)

		self.room = room
		self.nick = nick

		self.add_event_handler('session_start', self.session_start)
		self.add_event_handler('groupchat_message', self.muc_message)

	def session_start(self, event):
		self.get_roster()
		self.send_presence()

		self.plugin['xep_0045'].joinMUC(
			self.room,
			self.nick,
			wait=True
		)

	def muc_message(self, msg):
		print('%10s: %s' % (msg['mucnick'], msg['body']))

		# don't talk to yourself
		if msg['mucnick'] == self.nick:
			return

		return handle_msg(msg)

if '__main__' == __name__:
	import plugins

	plugins.chat_write = chat_write
	plugins.ratelimit_exceeded = ratelimit_exceeded
	plugins.ratelimit_touch = ratelimit_touch

	plugins.register_all()

	print(sys.argv[0] + ' ' + VERSION)

	logging.basicConfig(
		level=logging.INFO,
		format='%(levelname)-8s %(message)s'
	)

	xmpp = bot(
		jid=conf('jid'),
		password=conf('password'),
		room=conf('room'),
		nick=conf('bot_user')
	)

	xmpp.connect()
	xmpp.register_plugin('xep_0045')
	xmpp.process(threaded=False)

	while 1:
		try:
# FIXME: find a way to trigger them
			plugins.event_trigger()

			time.sleep(delay)
		except KeyboardInterrupt:
			print('')
			exit(130)