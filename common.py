#!/usr/bin/python3
# -*- coding: utf-8 -*-

if '__main__' == __name__:
	print('''this is a library file, which is not meant to be executed''')
	exit(-1)

import sys, os, time, pickle
from local_config import conf

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

def logger(severity, message):
#	sev = ( 'err', 'warn', 'info' )
#	if severity in sev:
	args = (sys.argv[0], time.strftime('%Y-%m-%d.%H:%M:%S'), severity, message)
	sys.stderr.write('%s %s %s: %s\n' % args)

def conf_save(obj):
	with open(conf('persistent_storage'), 'wb') as fd:
		return pickle.dump(obj, fd)

def conf_load():
	with open(conf('persistent_storage'), 'rb') as fd:
		fd.seek(0)
		return pickle.load(fd)

def get_version_git():
	import subprocess

	cmd = ['git', 'log', '-n', '1', '--oneline', '--abbrev-commit']

	p = subprocess.Popen(cmd, bufsize=1, stdout=subprocess.PIPE)
	first_line = p.stdout.readline()

	if 0 == p.wait():
		return "version (Git) '%s'" % str(first_line.strip(), encoding='utf8')
	else:
		return "(unknown version)"

VERSION = get_version_git()
