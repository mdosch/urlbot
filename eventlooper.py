#!/usr/bin/python

import sys, os, re, time, urllib, pickle

BUFSIZ = 8192
delay = 0.100 # seconds
bot_user = 'urlbot'

basedir = '.'
if 2 == len(sys.argv): basedir = sys.argv[1]

event_files_dir = os.path.join(basedir, 'event_files')
fifo_path = os.path.join(basedir, 'cmdfifo')

# rate limiting to 5 messages per 10 minutes
hist_max_count = 5
hist_max_time  = 10 * 60
hist_ts = []
hist_flag = True
uptime = -time.time()
request_counter = 0

def debug_enabled():
#	return True
	return False

def e(data):
	if data:
		return data.encode('string-escape')
	else:
		return "''"

def logger(severity, message):
#	sev = ( 'err', 'warn', 'info' )
#	if severity in sev:
	sys.stderr.write(e('%s: %s: %s' %(sys.argv[0], severity, message)) + '\n')

def fetch_page(url):
	logger('info', 'fetching page ' + url)
	try:
		response = urllib.urlopen(url)
		html = response.read(BUFSIZ) # ignore more than BUFSIZ
		response.close()
		return (html, response.headers)
	except IOError as e:
		logger('warn', 'failed: ' + e.errno)

def extract_title(url):
	logger('info', 'extracting title from ' + url)

	(html, headers) = fetch_page(url)
	if html:
		if 'content-type' in headers:
			if 'text/' != headers['content-type'][:len('text/')]:
				return (1, headers['content-type'])

		result = re.match(r'.*?<title.*?>(.*?)</title>.*?', html, re.S|re.M)
		if result:
			return (0, result.groups()[0])
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
			fd.write(prefix + message)
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
	result = re.findall("(https?://[^\s>]+)", data)
	if result:
		for r in result:
			if ratelimit_exceeded():
				return False

			(status, title) = extract_title(r)

			if 0 == status:
				message = 'Title: %s: %s' % (title.strip(), e(r))
			elif 1 == status:
				# of course it's fake, but it looks interesting at least
				char = """,._-+=\|/*`~"'"""
				message = 'No text but %s, 1-bit ASCII art preview: [%c] %s' %(
					e(title),
					char[int(time.time() % len(char))],
					e(r)
				)
			elif 2 == status:
				message = 'No title: %s' % (e(r))
			else:
				message = 'some error occurred when fetching %s' % e(r)

			message = message.replace('\n', '\\n')

			logger('info', 'printing ' + message)
			chat_write(message)

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
		if ratelimit_exceeded(): return False
		chat_write('''Multiple exclamation/question marks are a sure sign of mental disease, with %s as a living example.''' % reply_user)

	return True

def parse_commands(data):
	words = data.split(' ')

	if 2 > len(words): # need at least two words
		return

	# reply if beginning of the text matches bot_user
	if words[1][0:len(bot_user)] == bot_user:
		reply_user = words[0].strip('<>')

		if 'hangup' in data:
			chat_write('', prefix='/quit')
			logger('warn', 'received hangup: ' + data)
		elif 'uptime' in data:
			if ratelimit_exceeded(): return False

			u = int(uptime + time.time())
			plural_uptime = 's'
			plural_request = 's'

			if 1 == u: plural_uptime = ''
			if 1 == request_counter: plural_request = ''

			chat_write(reply_user + (''': happily serving for %d second%s, %d request%s so far.''' %(u, plural_uptime, request_counter, plural_request)))
			logger('info', 'sent statistics')
		elif 'ping' in data:
			if ratelimit_exceeded(): return False
			if (0 == (int(time.time()) & 3)): # 1:4
				chat_write(reply_user + ''': peng (You're dead now.)''')
				logger('info', 'sent pong (variant)')
			else:
				chat_write(reply_user + ''': pong''')
				logger('info', 'sent pong')
		else:
			if ratelimit_exceeded(): return False
			chat_write(reply_user + (''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further questions, please talk to my master Cae. I'm rate limited and shouldn't post more than %d messages per %d seconds. To make me exit immediately, highlight me with 'hangup' in the message (emergency only, please).''' %(hist_max_count, hist_max_time)))
			logger('info', 'sent info')

def parse_delete(filepath):
	try:
		fd = open(filepath, 'rb')
	except IOError:
		logger('err', 'file has vanished: ' + filepath)
		return False

	content = fd.read(BUFSIZ) # ignore more than BUFSIZ

	if content[1:1+len(bot_user)] != bot_user:
		if not 'Willkommen bei debianforum.de' in content:
			extract_url(content)
			parse_commands(content)
			parse_other(content)

	fd.close()

	os.remove(filepath) # probably better crash here

def print_version_git():
	import subprocess, sys

	cmd = ['git', 'log', '-n', '1', '--oneline', '--abbrev-commit']

	p = subprocess.Popen(cmd, bufsize=1, stdout=subprocess.PIPE)
	first_line = p.stdout.readline()

	if 0 == p.wait():
		print sys.argv[0] + " version (Git) '%s'" % first_line.strip()
	else:
		print sys.argv[0] + " (unknown version)"

print_version_git()

while 1:
	try:
		for f in os.listdir(event_files_dir):
			if 'mcabber-' == f[:8]:
				parse_delete(os.path.join(event_files_dir, f))

		time.sleep(delay)
	except KeyboardInterrupt:
		exit(130)
