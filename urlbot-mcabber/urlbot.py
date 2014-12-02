#!/usr/bin/python3
# -*- coding: utf-8 -*-

import sys, os, stat, re, time, pickle, random
import urllib.request, urllib.parse, urllib.error, html.parser
from local_config import conf, set_conf
from common import *
from strsim import str_sim

# rate limiting to 5 messages per 10 minutes
hist_ts = []
hist_flag = True

parser = None

def fetch_page(url):
	logger('info', 'fetching page ' + url)
	try:
		request = urllib.request.Request(url)
		request.add_header('User-Agent', '''Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0 Iceweasel/31.0''')
		response = urllib.request.urlopen(request)
		html_text = response.read(BUFSIZ) # ignore more than BUFSIZ
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

			charset = re.sub('.*charset=(?P<charset>\S+).*',
				'\g<charset>', headers['content-type'], re.IGNORECASE)

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
			except UnicodeDecodeError as e: # idk why this can happen, but it does
				logger('warn', 'parser.unescape() expoded here: ' + str(e))
				expanded_html = match
			return (0, expanded_html)
		else:
			return (2, 'no title')

	return (-1, 'error')

def chat_write(message, prefix='/say '):
	set_conf('request_counter', conf('request_counter') + 1)

	for m in message:
		if 0x20 > ord(m):
			logger('warn', 'strange char 0x%02x in chat_write(message), skipping' % ord(m))
			return False

	if debug_enabled():
		print(message)
	else:
		try:
			fd = open(fifo_path, 'wb')
# FIXME 2to3
			# FIXME: somehow, unicode chars can end up inside a <str> message,
			# which seems to make both unicode() and ''.encode('utf8') fail.
			try:
				msg = str(prefix) + str(message) + '\n'
				msg = msg.encode('utf8')
			except UnicodeDecodeError as e:
				logger('warn', 'encoding msg failed: ' + str(e))
				msg = prefix + message + '\n'

			fd.write(msg)
			fd.close()
		except IOError as e:
			logger('err', "couldn't print to fifo %s: %s" % (fifo_path, str(e)))

def ratelimit_touch(ignored=None): # FIXME: separate counters
	hist_ts.append(time.time())

	if conf('hist_max_count') < len(hist_ts):
		hist_ts.pop(0)


def ratelimit_exceeded(ignored=None): # FIXME: separate counters
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
	## reply_user = data.split(' ')[0].strip('<>')
	# since we can't determine if a user named 'foo> ' just wrote ' > bar'
	# or a user 'foo' just wrote '> > bar', we can't safely answer here
	logger('warn', 'received PN: ' + data)
	return False

def parse_delete(filepath):
	try:
		fd = open(filepath, 'r')
	except IOError as e:
		logger('err', 'file has vanished: %s: %s' % (filepath, e))
		return False

	content = fd.read(BUFSIZ) # ignore more than BUFSIZ
	fd.close()
	os.remove(filepath) # probably better crash here

	if content[1:1+len(conf('bot_user'))] == conf('bot_user'):
		return

	if 'has set the subject to:' in content:
		return
	
	if content.startswith('PRIV#'):
		parse_pn(content)
		return

	if 'nospoiler' in content:
#		logger('info', "no spoiler for: " + content)
		return

	if sys.argv[0] in content:
		logger('info', 'silenced, this is my own log')
		return

	if True != extract_url(content):
		plugins.data_parse_commands(content)
		plugins.data_parse_other(content)
		return

if '__main__' == __name__:
	import plugins

	plugins.chat_write = chat_write
	plugins.ratelimit_exceeded = ratelimit_exceeded
	plugins.ratelimit_touch = ratelimit_touch

	plugins.register_all()

	print(sys.argv[0] + ' ' + VERSION)

	if not os.path.exists(fifo_path):
		logger('error', 'fifo_path "%s" does not exist, exiting' % fifo_path)
		exit(1)

	if not stat.S_ISFIFO(os.stat(fifo_path).st_mode):
		logger('error', 'fifo_path "%s" is not a FIFO, exiting' % fifo_path)
		exit(1)

	while 1:
		try:
			for f in os.listdir(event_files_dir):
				if 'mcabber-' == f[:8]:
					parse_delete(os.path.join(event_files_dir, f))

			plugins.event_trigger()

			time.sleep(delay)
		except KeyboardInterrupt:
			print('')
			exit(130)
