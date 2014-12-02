#!/usr/bin/python3
# -*- coding: utf-8 -*-

if '__main__' == __name__:
	print('''this is a library file, which is not meant to be executed''')
	exit(-1)

import sys, os, time, pickle
from local_config import conf

RATE_GLOBAL = 0x01
RATE_NO_SILENCE = 0x02
RATE_INTERACTIVE = 0x04
RATE_CHAT = 0x08
RATE_URL = 0x10

BUFSIZ = 8192
delay = 0.100  # seconds

basedir = '.'
if 2 == len(sys.argv):
	basedir = sys.argv[1]

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

def levenshtein(a, b, return_table=False):
	'''returns the levenshtein distance between a and b'''
	# initialisize a table with 0, but the 0-rows/cols with their index
	d = [[(i if 0 == j else j if 0 == i else 0) for j in range(len(b)+1)] for i in range(len(a)+1)]

	i = j = 0
	for i in range(1, len(a)+1):
		for j in range(1, len(b)+1):
			if a[i-1] == b[j-1]:
				d[i][j] = d[i-1][j-1]
			else:
				d[i][j] = min(
					d[i-1][j] + 1,    # deletion
					d[i][j-1] + 1,    # insertion
					d[i-1][j-1] + 1,  # substitution
				)

	if return_table:
		return (d, d[i][j])
	else:
		return d[i][j]

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