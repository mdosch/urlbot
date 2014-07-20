#!/usr/bin/python

import sys, os, re, time, urllib

BUFSIZ = 8192
delay = 0.100 # seconds
ignore_user = 'urlbot'

basedir = '.'
if 2 == len(sys.argv): basedir = sys.argv[1]

event_files_dir = os.path.join(basedir, 'event_files')
fifo_path = os.path.join(basedir, 'cmdfifo')

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
	response = urllib.urlopen(url)
	html = response.read(BUFSIZ)
	response.close()
	return html

def extract_title(url):
	logger('info', 'extracting title from ' + url)
	html = fetch_page(url)
	result = re.match(r'.*?<title.*?>(.*?)</title>.*?', html, re.S|re.M)
	if result:
		return result.groups()[0]

def extract_url(data):
	result = re.findall("(https?://[^\s]+)", data)
	if result:
		for r in result:
			title = extract_title(r)

			message = '/say Title: %s: %s' % (title, e(r))
			logger('info', 'printing ' + message)

			if debug_enabled():
				print message
			else:
				try:
					fd = open(fifo_path, 'wb')
					fd.write(message)
					fd.close()
				except IOError:
					logger('err', "couldn't print to fifo " + fifo_path)

def parse_delete(filepath):
	try:
		fd = open(filepath, 'rb')
	except:
		logger('err', 'file has vanished: ' + filepath)
		return -1

	content = fd.read(BUFSIZ) # ignore more than BUFSIZ

	if content[1:1+len(ignore_user)] != ignore_user:
		extract_url(content)

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
