#!/usr/bin/python3
# -*- coding: utf-8 -*-

if '__main__' == __name__:
	print('''this is a library file, which is not meant to be executed''')
	exit(-1)

import sys, time, pickle, os, logging
from local_config import conf

RATE_GLOBAL = 0x01
RATE_NO_SILENCE = 0x02
RATE_INTERACTIVE = 0x04
RATE_CHAT = 0x08
RATE_URL = 0x10

BUFSIZ = 8192
EVENTLOOP_DELAY = 0.100  # seconds
USER_AGENT = '''Mozilla/5.0 (X11; Linux x86_64; rv:31.0) Gecko/20100101 Firefox/31.0 Iceweasel/31.0'''

basedir = '.'
if 2 == len(sys.argv):
	basedir = sys.argv[1]

logging.basicConfig(
	level=logging.INFO,
	format=sys.argv[0]+' %(asctime)s %(levelname).1s %(funcName)-15s %(message)s'
)
log = logging.getLogger()
log.plugin = log.info  # ... probably fix this sometime (FIXME)

def debug_enabled():
#	return True
	return False

def conf_save(obj):
	with open(conf('persistent_storage'), 'wb') as fd:
		return pickle.dump(obj, fd)

def conf_load():
	path = conf('persistent_storage')
	if os.path.isfile(path):
		with open(path, 'rb') as fd:
			fd.seek(0)
			return pickle.load(fd)
	else:
		return {}

def get_version_git():
	import subprocess

	cmd = ['git', 'log', '--oneline', '--abbrev-commit']

	p = subprocess.Popen(cmd, bufsize=1, stdout=subprocess.PIPE)
	first_line = p.stdout.readline()
	line_count = len(p.stdout.readlines()) + 1

	if 0 == p.wait():
		# skip this 1st, 2nd, 3rd stuff and use always [0-9]th
		return "version (Git, %dth rev) '%s'" % (
			line_count, str(first_line.strip(), encoding='utf8')
		)
	else:
		return "(unknown version)"

VERSION = get_version_git()
