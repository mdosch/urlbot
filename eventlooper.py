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
		return html
	except IOError as e:
		logger('warn', 'failed: ' + e.errno)

def extract_title(url):
	logger('info', 'extracting title from ' + url)

	html = fetch_page(url)
	if html:
		result = re.match(r'.*?<title.*?>(.*?)</title>.*?', html, re.S|re.M)
		if result:
			return result.groups()[0]

def chat_write(message):
	if debug_enabled():
		print message
	else:
		try:
			fd = open(fifo_path, 'wb')
			fd.write('/say ' + message)
			fd.close()
		except IOError:
			logger('err', "couldn't print to fifo " + fifo_path)

def ratelimit_exceeded():
	now = time.time()
	hist_ts.append(now)

	if hist_max_count < len(hist_ts):
		first = hist_ts.pop(0)
		if (now - first) < hist_max_time:
			logger('warn', 'rate limiting exceeded: ' + pickle.dumps(hist_ts))
			return True

	return False

def extract_url(data):
	result = re.findall("(https?://[^\s]+)", data)
	if result:
		for r in result:
			if ratelimit_exceeded():
				return False

			title = extract_title(r)

			if title:
				message = 'Title: %s: %s' % (title, e(r))
			else:
				message = 'some error occured when fetching %s' % e(r)

			logger('info', 'printing ' + message)
			chat_write(message)

def parse_commands(data):
	words = data.split(' ')

	if 3 > len(words): # need at least two words
		return

	# reply if beginning of the text matches bot_user
	if words[1][0:len(bot_user)] == bot_user:
		chat_write(words[0][1:-1] + ''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further questions, please talk to my master Cae.''')

def parse_delete(filepath):
	try:
		fd = open(filepath, 'rb')
	except IOError:
		logger('err', 'file has vanished: ' + filepath)
		return False

	content = fd.read(BUFSIZ) # ignore more than BUFSIZ

	if content[1:1+len(bot_user)] != bot_user:
		extract_url(content)
		parse_commands(content)

	fd.close()

	os.remove(filepath) # probably better crash here

while 1:
	try:
		for f in os.listdir(event_files_dir):
			if 'mcabber-' == f[:8]:
				parse_delete(os.path.join(event_files_dir, f))

		time.sleep(delay)
	except KeyboardInterrupt:
		exit(130)
