#!/usr/bin/python
# -*- coding: utf-8 -*-

if '__main__' == __name__:
	print '''this is a library file, which is not meant to be executed'''
	exit(-1)

import sys, os, time

RATE_GLOBAL      = 0x01
RATE_NO_SILENCE  = 0x02
RATE_INTERACTIVE = 0x04
RATE_CHAT        = 0x08
RATE_URL         = 0x10

BUFSIZ = 8192
delay = 0.100 # seconds

basedir = '.'
if 2 == len(sys.argv): basedir = sys.argv[1]

event_files_dir = os.path.join(basedir, 'event_files')
fifo_path = os.path.join(basedir, 'cmdfifo')

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
