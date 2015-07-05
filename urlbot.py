#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys, re, time, pickle, random
import urllib.request, urllib.parse, urllib.error, html.parser
from common import *

try:
	from local_config import conf, set_conf
except ImportError:
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

from sleekxmpp import ClientXMPP

# rate limiting to 5 messages per 10 minutes
hist_ts = []
hist_flag = True

parser = None

def fetch_page(url):
	log.info('fetching page ' + url)
	try:
		request = urllib.request.Request(url)
		request.add_header('User-Agent', '''Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0 Iceweasel/31.0''')
		response = urllib.request.urlopen(request)
		html_text = response.read(BUFSIZ)  # ignore more than BUFSIZ
		response.close()
		return (0, html_text, response.headers)
	except Exception as e:
		log.warn('failed: %s' % e)
		return (1, str(e), 'dummy')

	return (-1, None, None)

def extract_title(url):
	global parser

	if 'repo/urlbot.git' in url:
		log.info('repo URL found: ' + url)
		return (3, 'wee, that looks like my home repo!')

	log.info('extracting title from ' + url)

	(code, html_text, headers) = fetch_page(url)

	if 1 == code:
		return (3, 'failed: %s for %s' % (html_text, url))

	if html_text:
		charset = ''
		if 'content-type' in headers:
			log.debug('content-type: ' + headers['content-type'])

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
				log.warn("invalid charset in '%s': '%s'" % (headers['content-type'], charset))

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
				log.warn('parser.unescape() expoded here: ' + str(e))
				expanded_html = match
			return (0, expanded_html)
		else:
			return (2, 'no title')

	return (-1, 'error')

def send_reply(message, msg_obj):
	set_conf('request_counter', conf('request_counter') + 1)

	if str is not type(message):
		message = '\n'.join(message)

	if debug_enabled():
		print(message)
	else:
		msg_obj.reply(body=message).send()

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
# FIXME: this is very likely broken now
				send_reply('(rate limited to %d messages in %d seconds, try again at %s)' % (conf('hist_max_count'), conf('hist_max_time'), time.strftime('%T %Z', time.localtime(hist_ts[0] + conf('hist_max_time')))))

			log.warn('rate limiting exceeded: ' + pickle.dumps(hist_ts))
			return True

	hist_flag = True
	return False

def extract_url(data, msg_obj):
	result = re.findall("(https?://[^\s>]+)", data)
	if not result:
		return

	ret = None
	out = []
	for url in result:
		ratelimit_touch()
		if ratelimit_exceeded(msg_obj):
			return False

		flag = False
		for b in conf('url_blacklist'):
			if not None is re.match(b, url):
				flag = True
				log.info('url blacklist match for ' + url)
				break

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

			message = 'Title: %s' % title
		elif 1 == status:
			if conf('image_preview'):
				# of course it's fake, but it looks interesting at least
				char = """,._-+=\|/*`~"'"""
				message = 'No text but %s, 1-bit ASCII art preview: [%c]' % (
					title, random.choice(char)
				)
			else:
				log.info('no message sent for non-text %s (%s)' % (url, title))
				continue
		elif 2 == status:
			message = '(No title)'
		elif 3 == status:
			message = title
		elif 4 == status:
			message = 'Bug triggered (%s), invalid URL/domain part: %s' % (title, url)
			log.warn(message)
		else:
			message = 'some error occurred when fetching %s' % url

		message = message.replace('\n', '\\n')

		log.info('adding to out buf: ' + message)
		out.append(message)
		ret = True

	if True == ret:
		send_reply(out, msg_obj)

	return ret

def handle_msg(msg_obj):
	content = msg_obj['body']

	if 'has set the subject to:' in content:
		return

	if sys.argv[0] in content:
		log.info('silenced, this is my own log')
		return

	if 'nospoiler' in content:
		log.info('no spoiler for: ' + content)
		return

	# don't react to itself
	if str(msg_obj['from']).startswith(conf('bot_user')):
		return

	arg_user = msg_obj['mucnick']
	blob_userpref = conf_load().get('user_pref',[])
	nospoiler = False

	if arg_user in blob_userpref:
		if 'spoiler' in blob_userpref[arg_user]:
			if not blob_userpref[arg_user]['spoiler']:
				log.info('nospoiler from conf')
				nospoiler = True

	ret = None
	if not nospoiler:
		ret = extract_url(content, msg_obj)

#	print(' '.join(["%s->%s" % (x, msg_obj[x]) for x in msg_obj.keys()]))

	if True != ret:
		plugins.data_parse_commands(msg_obj)
		plugins.data_parse_other(msg_obj)
		return

class bot(ClientXMPP):
	def __init__(self, jid, password, rooms, nick):
		ClientXMPP.__init__(self, jid, password)

		self.rooms = rooms
		self.nick = nick

		self.add_event_handler('session_start', self.session_start)
		self.add_event_handler('groupchat_message', self.muc_message)
		self.add_event_handler('message', self.message)

	def session_start(self, event):
		self.get_roster()
		self.send_presence()

		for room in self.rooms:
			log.info('joining %s' % room)
			self.plugin['xep_0045'].joinMUC(
				room,
				self.nick,
				wait=True
			)

	def muc_message(self, msg_obj):
		# don't talk to yourself
		if msg_obj['mucnick'] == self.nick:
			return

		return handle_msg(msg_obj)

	def message(self, msg_obj):
		if 'groupchat' == msg_obj['type']:
			return

#		plugins.data_parse_commands(msg_obj)
#		plugins.data_parse_other(msg_obj)

		print('msg from %s: %s' % (msg_obj['from'].bare, msg_obj))

#	def set_presence(self, msg):
#		for room in self.rooms:
#			self.send_presence(pto=room, pstatus=msg)

if '__main__' == __name__:
	log.info(VERSION)

	import plugins

	plugins.send_reply = send_reply
	plugins.ratelimit_exceeded = ratelimit_exceeded
	plugins.ratelimit_touch = ratelimit_touch

	plugins.register_all()

	logging.basicConfig(
		level=logging.INFO,
		format='%(levelname)-8s %(message)s'
	)

	xmpp = bot(
		jid=conf('jid'),
		password=conf('password'),
		rooms=conf('rooms'),
		nick=conf('bot_user')
	)

	xmpp.connect()
	xmpp.register_plugin('xep_0045')
	xmpp.process()

	while 1:
		try:
			if False == plugins.event_trigger():
				xmpp.disconnect()
				sys.exit(1)

			time.sleep(delay)
		except KeyboardInterrupt:
			print('')
			exit(130)
