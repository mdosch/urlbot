#!/usr/bin/python3
# -*- coding: utf-8 -*-

if '__main__' == __name__:
	print('''this is a plugin file, which is not meant to be executed''')
	exit(-1)

import time, random
from local_config import conf
from common import *

joblist = []

plugins = {}
plugins['parse'] = []
plugins['command'] = []

def get_reply_user(data):
	# FIXME: we can't determine if a user named 'foo> ' just wrote ' > bar'
	# or a user 'foo' just wrote '> > bar'
	return data.split(' ')[0].strip('<>')

def register_event(t, callback, args):
	joblist.append((t, callback, args))

def parse_mental_ill(args):
	if 'register' == args:
		return {
			'name': 'parse mental illness',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_NO_SILENCE | RATE_GLOBAL
		}

	min_ill = 3
	c = 0
	flag = False

	# return True for min_ill '!' in a row
	for d in args['data']:
		if '!' == d or '?' == d:
			c += 1
		else:
			c = 0
		if (min_ill <= c):
			flag = True
			break

	if True == flag:
		logger('plugin', 'sent mental illness reply')
		return {
			'msg': '''Multiple exclamation/question marks are a sure sign of mental disease, with %s as a living example.''' % args['reply_user']
		}

def parse_skynet(args):
	if 'register' == args:
		return {
			'name': 'parse skynet',
			'args': ('data',),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'skynet' in args['data'].lower():
		logger('plugin', 'sent skynet reply')
		return {
			'msg': '''I'm an independent bot and have nothing to do with other artificial intelligence systems!'''
		}

def data_parse_other(data):
	reply_user = get_reply_user(data)

	for p in plugins['parse']:
		if ratelimit_exceeded(p['ratelimit_class']):
			continue

		args = {}

		if 'args' in list(p.keys()):
			for a in p['args']:
				if None == a: continue

				if 'data' == a:
					args['data'] = data
				elif 'reply_user' == a:
					args['reply_user'] = reply_user
				else:
					logger('warn', 'unknown required arg for %s: %s' %(f, a))

		ret = p['func'](args)

		if None != ret:
			if 'msg' in list(ret.keys()):
				ratelimit_touch(RATE_CHAT)
				chat_write(ret['msg'])

def command_command(args):
	if 'register' == args:
		return {
			'name': 'command',
			'desc': 'lists commands',
			'args': ('data', 'reply_user', 'cmd_list'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'command' in args['data']:
		logger('plugin', 'sent command list')
		return {
			'msg': args['reply_user'] + ': known commands: ' + str(args['cmd_list']).strip('[]')
		}

def command_help(args):
	if 'register' == args:
		return {
			'name': 'help',
			'desc': 'print help for a command',
			'args': ('data', 'reply_user', 'cmd_list'),
			'ratelimit_class': RATE_GLOBAL
		}


	cmd = None
	flag = False

	for word in args['data'].split():
		if True == flag:
			cmd = word
			break

		if 'help' == word:
			flag = True

	if False == flag: # no match on 'help'
		return None

	if None == cmd:
		logger('plugin', 'empty help request')
		return {
			'msg': args['reply_user'] + ': no command given'
		}

	if not cmd in [p['name'] for p in plugins['command']]:
		logger('plugin', 'no help found for %s' % cmd)
		return {
			'msg': args['reply_user'] + ': no such command: %s' % cmd
		}

	for p in plugins['command']:
		if cmd == p['name']:
			logger('plugin', 'sent help for %s' % cmd)
			return {
				'msg': args['reply_user'] + ': help for %s: %s' %(cmd, p['desc'])
			}


def command_version(args):
	if 'register' == args:
		return {
			'name': 'version',
			'desc': 'prints version',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'version' in args['data']:
		logger('plugin', 'sent version string')
		return {
			'msg': args['reply_user'] + (''': I'm running ''' + VERSION)
		}

def command_unicode(args):
	if 'register' == args:
		return {
			'name': 'unikot',
			'desc': 'prints an unicode string',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'unikot' in args['data']:
		logger('plugin', 'sent some unicode')
		return {
			'msg': 
				(
					args['reply_user'] + ''': ┌────────┐''',
					args['reply_user'] + ''': │Unicode!│''',
					args['reply_user'] + ''': └────────┘'''
				)
		}

def command_source(args):
	if 'register' == args:
		return {
			'name': 'source',
			'desc': 'prints git URL',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'source' in args['data']:
		logger('plugin', 'sent source URL')
		return {
			'msg': 'My source code can be found at %s' % conf('src-url')
		}

def command_dice(args):
	if 'register' == args:
		return {
			'name': 'dice',
			'desc': 'rolls a dice',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_INTERACTIVE
		}

	if 'dice' in args['data']:
		if args['reply_user'] in conf('enhanced-random-user'):
			rnd = 0 # this might confuse users. good.
			logger('plugin', 'sent random (enhanced)')
		else:
			rnd = random.randint(1, 6)
			logger('plugin', 'sent random')

		dice_char = ['◇', '⚀', '⚁', '⚂', '⚃', '⚄', '⚅']
		return {
			'msg': 'rolling a dice for %s: %s (%d)' %(args['reply_user'], dice_char[rnd], rnd)
		}

def command_uptime(args):
	if 'register' == args:
		return {
			'name': 'uptime',
			'desc': 'prints uptime',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'uptime' in args['data']:
		u = int(conf('uptime') + time.time())
		plural_uptime = 's'
		plural_request = 's'

		if 1 == u: plural_uptime = ''
		if 1 == conf('request_counter'): plural_request = ''

		logger('plugin', 'sent statistics')
		return {
			'msg': args['reply_user'] + (''': happily serving for %d second%s, %d request%s so far.''' %(u, plural_uptime, conf('request_counter'), plural_request))
		}

def command_ping(args):
	if 'register' == args:
		return {
			'name': 'ping',
			'desc': 'sends pong',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_INTERACTIVE
		}

	if 'ping' in args['data']:
		rnd = random.randint(0, 3) # 1:4
		if 0 == rnd:
			msg = args['reply_user'] + ''': peng (You're dead now.)'''
			logger('plugin', 'sent pong (variant)')
		elif 1 == rnd:
			msg = args['reply_user'] + ''': I don't like you, leave me alone.'''
			logger('plugin', 'sent pong (dontlike)')
		else:
			msg = args['reply_user'] + ''': pong'''
			logger('plugin', 'sent pong')

		return {
			'msg': msg
		}

def command_info(args):
	if 'register' == args:
		return {
			'name': 'info',
			'desc': 'prints info message',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'info' in args['data']:
		logger('plugin', 'sent long info')
		return {
			'msg': args['reply_user'] + (''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further questions, please talk to my master %s. I'm rate limited and shouldn't post more than %d messages per %d seconds. To make me exit immediately, highlight me with 'hangup' in the message (emergency only, please). For other commands, highlight me with 'command'.''' %(conf('bot_owner'), conf('hist_max_count'), conf('hist_max_time')))
		}

def command_teatimer(args):
	if 'register' == args:
		return {
			'name': 'teatimer',
			'desc': 'sets a tea timer to currently %d seconds' % conf('tea_steep_time'),
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'teatimer' in args['data']:
		ready = time.time() + conf('tea_steep_time')

		logger('plugin', 'tea timer set to %s' % time.strftime('%F.%T', time.localtime(ready)))
		register_event(ready, chat_write, args['reply_user'] + ': Your tea is ready!')
		
		return {
			'msg': args['reply_user'] + ': Tea timer set to %s' % time.strftime(
				'%F.%T', time.localtime(ready)
			)
		}

def command_else(args):
	logger('plugin', 'sent short info')
	return {
		'msg': args['reply_user'] + ''': I'm a bot (highlight me with 'info' for more information).'''
	}

def data_parse_commands(data):
	words = data.split(' ')

	if 2 > len(words): # need at least two words
		return None

	# don't reply if beginning of the text matches bot_user
	if not words[1].startswith(conf('bot_user')):
		return None

	if 'hangup' in data:
		chat_write('', prefix='/quit')
		logger('warn', 'received hangup: ' + data)
		return None

	reply_user = get_reply_user(data)

	for p in plugins['command']:
		if ratelimit_exceeded(p['ratelimit_class']):
			continue

		args = {}

		if 'args' in list(p.keys()):
			for a in p['args']:
				if None == a: continue

				if 'data' == a:
					args['data'] = data
				elif 'cmd_list' == a:
					cmds = [c['name'] for c in plugins['command']]
					cmds.sort()
					args['cmd_list'] = cmds
				elif 'reply_user' == a:
					args['reply_user'] = reply_user
				else:
					logger('warn', 'unknown required arg for %s: %s' %(f, a))

		ret = p['func'](args)

		if None != ret:
			if 'msg' in list(ret.keys()):
				if str == type(ret['msg']): # FIXME 2to3
					ratelimit_touch(RATE_CHAT)
					if ratelimit_exceeded(RATE_CHAT):
						return False

					chat_write(ret['msg'])
				else:
					for line in ret['msg']:
						ratelimit_touch(RATE_CHAT)
						if ratelimit_exceeded(RATE_CHAT):
							return False

						chat_write(line)

			return None

	ret = command_else({'reply_user': reply_user})
	if None != ret:
		if ratelimit_exceeded(RATE_GLOBAL):
			return False

		if 'msg' in list(ret.keys()):
			chat_write(ret['msg'])

funcs = {}
funcs['parse'] = (parse_mental_ill, parse_skynet)
funcs['command'] = (
	command_command, command_help, command_version, command_unicode,
	command_source, command_dice, command_uptime, command_ping, command_info,
	command_teatimer
)

_dir = dir()

if debug_enabled():
	def _chat_write(a): logger('chat_write', a)
	def _conf(a): return 'bot'
	def _ratelimit_exceeded(ignored=None): return False
	def _ratelimit_touch(ignored=None): return True

	try: chat_write
	except NameError: chat_write = _chat_write
	try: conf
	except NameError: conf = _conf
	try: ratelimit_exceeded
	except NameError: ratelimit_exceeded = _ratelimit_exceeded
	try: ratelimit_touch
	except NameError: ratelimit_touch = _ratelimit_touch

	logger('info', 'debugging enabled')

def register(func_type, auto=False):
	plugins[func_type] = []

	if auto:
		# FIXME: this is broken. dir() returns str, but not
		# the addr of the functions which we'd need here.
		for f in _dir:
			print('testing(%s)' % f)
			if not f.startswith(func_type + '_'):
				continue

			try:
				ret = f('register')
				ret['func'] = f
				plugins[func_type].append(ret)
			except Exception as e:
				logger('warn', 'auto-registering %s failed: %s' %(f, e))

	else:
		for f in funcs[func_type]:
			ret = f('register')
			ret['func'] = f
			plugins[func_type].append(ret)

def register_all():
	register('parse')
	register('command')

def event_trigger():
	if 0 == len(joblist):
		return

	now = time.time()

	i = 0
	for (t, callback, args) in joblist:
		if t < now:
			callback(args)
			del(joblist[i])

		i += 1
