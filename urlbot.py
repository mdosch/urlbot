#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, re, time, urllib, pickle, HTMLParser, stat
from local_config import conf, set_conf
from common import *

# rate limiting to 5 messages per 10 minutes
hist_ts = []
hist_flag = True

parser = None

class urllib_user_agent_wrapper(urllib.FancyURLopener):
	version = '''Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0 Iceweasel/31.0'''

def fetch_page(url):
	logger('info', 'fetching page ' + url)
	try:
		urllib._urlopener = urllib_user_agent_wrapper()
		response = urllib.urlopen(url)
		html = response.read(BUFSIZ) # ignore more than BUFSIZ
		response.close()
		return (html, response.headers)
	except IOError as e:
		logger('warn', 'failed: ' + e.errno)

	return (None, None)

def extract_title(url):
	global parser

	if 'repo/urlbot.git' in url:
		logger('info', 'repo URL found: ' + url)
		return (3, 'wee, that looks like my home repo!')

	logger('info', 'extracting title from ' + url)

	(html, headers) = fetch_page(url)
	if html:
		charset = ''
		if 'content-type' in headers:
			logger('debug', 'content-type: ' + headers['content-type'])

			if 'text/' != headers['content-type'][:len('text/')]:
				return (1, headers['content-type'])

			charset = re.sub('.*charset=(?P<charset>\S+).*',
				'\g<charset>', headers['content-type'], re.IGNORECASE)

		result = re.match(r'.*?<title.*?>(.*?)</title>.*?', html, re.S | re.M | re.IGNORECASE)
		if result:
			match = result.groups()[0]

#			if 'charset=UTF-8' in headers['content-type']:
#				match = unicode(match)

			if None == parser:
				parser = HTMLParser.HTMLParser()

			if '' != charset:
				try:
					match = match.decode(charset)
				except LookupError:
					logger('warn', 'invalid charset in ' + headers['content-type'])

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

	if debug_enabled():
		print message
	else:
		try:
			fd = open(fifo_path, 'wb')

			# FIXME: somehow, unicode chars can end up inside a <str> message,
			# which seems to make both unicode() and ''.encode('utf8') fail.
			try:
				msg = unicode(prefix) + unicode(message) + '\n'
				msg = msg.encode('utf8')
			except UnicodeDecodeError:
				msg = prefix + message + '\n'

			fd.write(msg)
			fd.close()
		except IOError:
			logger('err', "couldn't print to fifo " + fifo_path)

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
		for r in result:
			ratelimit_touch()
			if ratelimit_exceeded():
				return False

			(status, title) = extract_title(r)

			if 0 == status:
				message = 'Title: %s: %s' % (title.strip(), e(r))
			elif 1 == status:
				logger('info', 'no message sent for non-text %s (%s)' %(r, title))
				continue
			elif 2 == status:
				message = 'No title: %s' % (e(r))
			elif 3 == status:
				message = title
			else:
				message = 'some error occurred when fetching %s' % e(r)

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
		fd = open(filepath, 'rb')
	except IOError:
		logger('err', 'file has vanished: ' + filepath)
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
		logger('info', "no spoiler for: " + content)
		return

	if True != extract_url(content):
		plugins.data_parse_commands(content)
		plugins.data_parse_other(content)
		return

import plugins

plugins.chat_write = chat_write
plugins.ratelimit_exceeded = ratelimit_exceeded
plugins.ratelimit_touch = ratelimit_touch

plugins.register_all()

if '__main__' == __name__:
	print sys.argv[0] + ' ' + VERSION

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

			time.sleep(delay)
		except KeyboardInterrupt:
			print ""
			exit(130)
