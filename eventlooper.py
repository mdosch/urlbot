#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys, os, re, time, urllib, pickle, random, HTMLParser
from local_config import conf

BUFSIZ = 8192
delay = 0.100 # seconds
bot_user = 'urlbot'

basedir = '.'
if 2 == len(sys.argv): basedir = sys.argv[1]

event_files_dir = os.path.join(basedir, 'event_files')
fifo_path = os.path.join(basedir, 'cmdfifo')

# rate limiting to 5 messages per 10 minutes
hist_max_count = 5
hist_max_time = 10 * 60
hist_ts = []
hist_flag = True
uptime = -time.time()
request_counter = 0

parser = None

def debug_enabled():
#	return True
	return False

def e(data):
	if data:
		if unicode == type(data):
			return data.encode('utf8')
		elif str == type(data):
			return data.encode('string-escape')
		else:
			return data
	else:
		return "''"

def logger(severity, message):
#	sev = ( 'err', 'warn', 'info' )
#	if severity in sev:
	args = (sys.argv[0], time.strftime('%Y-%m-%d.%H:%M:%S'), severity, message)
	sys.stderr.write(e('%s %s %s: %s' % args) + '\n')

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
	global request_counter
	request_counter += 1

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

def ratelimit_exceeded():
	global hist_flag

	now = time.time()
	hist_ts.append(now)

	if hist_max_count < len(hist_ts):
		first = hist_ts.pop(0)
		if (now - first) < hist_max_time:
			if hist_flag:
				hist_flag = False
				chat_write('(rate limited to %d messages in %d seconds, try again at %s)' %(hist_max_count, hist_max_time, time.strftime('%T %Z', time.localtime(hist_ts[0] + hist_max_time))))

			logger('warn', 'rate limiting exceeded: ' + pickle.dumps(hist_ts))
			return True

	hist_flag = True
	return False

def extract_url(data):
	ret = None
	result = re.findall("(https?://[^\s>]+)", data)
	if result:
		for r in result:
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

def mental_ill(data):
	min_ill = 3
	c = 0

	# return True for min_ill '!' in a row
	for d in data:
		if '!' == d or '?' == d:
			c += 1
		else:
			c = 0
		if (min_ill <= c):
			return True

	return False

def parse_other(data):
	reply_user = data.split(' ')[0].strip('<>')

	if True == mental_ill(data):
		if ratelimit_exceeded():
			return False
		chat_write('''Multiple exclamation/question marks are a sure sign of mental disease, with %s as a living example.''' % reply_user)

	return True

def parse_pn(data):
	## reply_user = data.split(' ')[0].strip('<>')
	# since we can't determine if a user named 'foo> ' just wrote ' > bar'
	# or a user 'foo' just wrote '> > bar', we can't safely answer here
	logger('warn', 'received PN: ' + data)
	return False

def parse_commands(data):
	words = data.split(' ')

	if 2 > len(words): # need at least two words
		return None

	# reply if beginning of the text matches bot_user
	if words[1][0:len(bot_user)] == bot_user:
		reply_user = words[0].strip('<>')

		if 'hangup' in data:
			chat_write('', prefix='/quit')
			logger('warn', 'received hangup: ' + data)
			return None

		if ratelimit_exceeded():
			return False

		if 'command' in data:
			chat_write(reply_user + (""": known commands: 'command', 'dice', 'info', 'hangup', 'nospoiler', 'ping', 'uptime', 'source', 'version'"""))
		elif 'version' in data:
			chat_write(reply_user + (''': I'm running ''' + VERSION))
		elif 'unikot' in data:
			chat_write(reply_user + (u''': ┌────────┐'''))
			chat_write(reply_user + (u''': │Unicode!│'''))
			chat_write(reply_user + (u''': └────────┘'''))
		elif 'source' in data:
			chat_write('My source code can be found at %s' % conf('src-url'))
		elif 'dice' in data:
			rnd = random.randint(1, 6)
			dice_char = [u'⚀', u'⚁', u'⚂', u'⚃', u'⚄', u'⚅']
			chat_write('rolling a dice for %s: %s (%d)' %(reply_user, dice_char[rnd-1], rnd))
		elif 'uptime' in data:
			u = int(uptime + time.time())
			plural_uptime = 's'
			plural_request = 's'

			if 1 == u: plural_uptime = ''
			if 1 == request_counter: plural_request = ''

			chat_write(reply_user + (''': happily serving for %d second%s, %d request%s so far.''' %(u, plural_uptime, request_counter, plural_request)))
			logger('info', 'sent statistics')
		elif 'ping' in data:
			rnd = random.randint(0, 3) # 1:4
			if 0 == rnd:
				chat_write(reply_user + ''': peng (You're dead now.)''')
				logger('info', 'sent pong (variant)')
			elif 1 == rnd:
				chat_write(reply_user + ''': I don't like you, leave me alone.''')
				logger('info', 'sent pong (dontlike)')
			else:
				chat_write(reply_user + ''': pong''')
				logger('info', 'sent pong')
		elif 'info' in data:
			chat_write(reply_user + (''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further questions, please talk to my master Cae. I'm rate limited and shouldn't post more than %d messages per %d seconds. To make me exit immediately, highlight me with 'hangup' in the message (emergency only, please). For other commands, highlight me with 'command'.''' %(hist_max_count, hist_max_time)))
			logger('info', 'sent long info')
		else:
			chat_write(reply_user + (''': I'm a bot (highlight me with 'info' for more information).'''))
			logger('info', 'sent short info')

def parse_delete(filepath):
	try:
		fd = open(filepath, 'rb')
	except IOError:
		logger('err', 'file has vanished: ' + filepath)
		return False

	content = fd.read(BUFSIZ) # ignore more than BUFSIZ
	fd.close()
	os.remove(filepath) # probably better crash here

	if content[1:1+len(bot_user)] == bot_user:
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
		parse_commands(content)
		parse_other(content)
		return

def get_version_git():
	import subprocess

	cmd = ['git', 'log', '-n', '1', '--oneline', '--abbrev-commit']

	p = subprocess.Popen(cmd, bufsize=1, stdout=subprocess.PIPE)
	first_line = p.stdout.readline()

	if 0 == p.wait():
		return "version (Git) '%s'" % e(first_line.strip())
	else:
		return "(unknown version)"

if '__main__' == __name__:
	VERSION = get_version_git()
	print sys.argv[0] + ' ' + VERSION

	while 1:
		try:
			for f in os.listdir(event_files_dir):
				if 'mcabber-' == f[:8]:
					parse_delete(os.path.join(event_files_dir, f))

			time.sleep(delay)
		except KeyboardInterrupt:
			print ""
			exit(130)
