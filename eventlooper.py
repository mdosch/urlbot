#!/usr/bin/python

import sys, os, re, time

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
	return data.encode('string-escape')

def logger(severity, message):
	if \
	'err'  == severity or \
	'warn' == severity or \
	'info' == severity:
		sys.stderr.write(e(sys.argv[0] + ': ' + message) + '\n')

def extract_url(data):
	result = re.findall("(https?://[^\s]+)", data)
	if result:
		for r in result:
			message = '/say yeah, URL found: %s' % e(r)
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
