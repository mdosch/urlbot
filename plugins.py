#!/usr/bin/python
# -*- coding: utf-8 -*-

if '__main__' == __name__:
	print '''this is a plugin file, which is not meant to be executed'''
	exit(-1)

RATE_GLOBAL      = 0x01
RATE_NO_SILENCE  = 0x02
RATE_INTERACTIVE = 0x04
RATE_CHAT        = 0x08
RATE_URL         = 0x10

plugins = {}
plugins['parse'] = []
plugins['command'] = []

def get_reply_user(data):
	# FIXME: we can't determine if a user named 'foo> ' just wrote ' > bar'
	# or a user 'foo' just wrote '> > bar'
	return data.split(' ')[0].strip('<>')

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
		return {
			'msg': '''I'm an independent bot and have nothing to do with other artificial intelligence systems!'''
		}

def data_parse_other(data):
	reply_user = get_reply_user(data)

	for p in plugins['parse']:
		if ratelimit_exceeded(p['ratelimit_class']):
			continue

		args = {}

		if 'args' in p.keys():
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
			if 'msg' in ret.keys():
				ratelimit_touch(RATE_CHAT)
				chat_write(ret['msg'])

def command_help(args):
	if 'register' == args:
		return {
			'name': 'prints help',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'command' in args['data']:
		return {
			'msg': args['reply_user'] + (""": known commands: 'command', 'dice', 'info', 'hangup', 'nospoiler', 'ping', 'uptime', 'source', 'version'""")
		}

def command_version(args):
	if 'register' == args:
		return {
			'name': 'prints version',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'version' in args['data']:
		return {
			'msg': args['reply_user'] + (''': I'm running ''' + conf('version'))
		}

def command_unicode(args):
	if 'register' == args:
		return {
			'name': 'prints an unicode string',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'unikot' in args['data']:
		return {
			'msg': 
				args['reply_user'] + u''': ┌────────┐''' + '\n' +
				args['reply_user'] + u''': │Unicode!│''' + '\n' +
				args['reply_user'] + u''': └────────┘'''
		}

def command_source(args):
	if 'register' == args:
		return {
			'name': 'prints git URL',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'source' in args['data']:
		return {
			'msg': 'My source code can be found at %s' % conf('src-url')
		}

def command_dice(args):
	if 'register' == args:
		return {
			'name': 'rolls a dice',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_INTERACTIVE
		}

	if 'dice' in args['data']:
		if args['reply_user'] in conf('enhanced-random-user'):
			rnd = 0 # this might confuse users. good.
		else:
			rnd = random.randint(1, 6)

		dice_char = [u'◇', u'⚀', u'⚁', u'⚂', u'⚃', u'⚄', u'⚅']
		return {
			'msg': 'rolling a dice for %s: %s (%d)' %(args['reply_user'], dice_char[rnd], rnd)
		}

def command_uptime(args):
	if 'register' == args:
		return {
			'name': 'prints uptime',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'uptime' in args['data']:
		u = int(conf('uptime') + time.time())
		plural_uptime = 's'
		plural_request = 's'

		if 1 == u: plural_uptime = ''
		if 1 == conf('request_counter'): plural_request = ''

		logger('info', 'sent statistics')
		return {
			'msg': args['reply_user'] + (''': happily serving for %d second%s, %d request%s so far.''' %(u, plural_uptime, conf('request_counter'), plural_request))
		}

def command_ping(args):
	if 'register' == args:
		return {
			'name': 'pong',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_INTERACTIVE
		}

	if 'ping' in args['data']:
		rnd = random.randint(0, 3) # 1:4
		if 0 == rnd:
			msg = args['reply_user'] + ''': peng (You're dead now.)'''
			logger('info', 'sent pong (variant)')
		elif 1 == rnd:
			msg = args['reply_user'] + ''': I don't like you, leave me alone.'''
			logger('info', 'sent pong (dontlike)')
		else:
			msg = args['reply_user'] + ''': pong'''
			logger('info', 'sent pong')

		return {
			'msg': msg
		}

def command_info(args):
	if 'register' == args:
		return {
			'name': 'prints info message',
			'args': ('data', 'reply_user'),
			'ratelimit_class': RATE_GLOBAL
		}

	if 'info' in args['data']:
		logger('info', 'sent long info')
		return {
			'msg': args['reply_user'] + (''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further questions, please talk to my master %s. I'm rate limited and shouldn't post more than %d messages per %d seconds. To make me exit immediately, highlight me with 'hangup' in the message (emergency only, please). For other commands, highlight me with 'command'.''' %(conf('bot_owner'), conf('hist_max_count'), conf('hist_max_time')))
		}

def command_else(args):
	logger('info', 'sent short info')
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

	flag = False

	for p in plugins['command']:
		if ratelimit_exceeded(p['ratelimit_class']):
			continue

		args = {}

		if 'args' in p.keys():
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
			flag = True
			if 'msg' in ret.keys():
				ratelimit_touch(RATE_CHAT)
				chat_write(ret['msg'])

	if False != flag:
		return None

	ret = command_else({'reply_user': reply_user})
	if None != ret:
		if ratelimit_exceeded(RATE_GLOBAL):
			return False

		if 'msg' in ret.keys():
			chat_write(ret['msg'])

funcs = {}
funcs['parse'] = (parse_mental_ill, parse_skynet)
funcs['command'] = (
	command_help, command_version, command_unicode, command_source,
	command_dice, command_uptime, command_ping, command_info
)

_dir = dir()

debug = False
if debug:
	def _chat_write(a): _logger('chat_write', a)
	def _conf(a): return 'bot'
	def _logger(a, b): print 'logger: %s::%s' %(a, b)
	def _ratelimit_exceeded(ignored=None): return False
	def _ratelimit_touch(ignored=None): return True

	try: chat_write
	except NameError: chat_write = _chat_write
	try: conf
	except NameError: conf = _conf
	try: logger
	except NameError: logger = _logger
	try: ratelimit_exceeded
	except NameError: ratelimit_exceeded = _ratelimit_exceeded
	try: ratelimit_touch
	except NameError: ratelimit_touch = _ratelimit_touch
	try: random
	except NameError: import random

def register(func_type, auto=False):
	plugins[func_type] = []

	if auto:
		# FIXME: this is broken. dir() returns str, but not
		# the addr of the functions which we'd need here.
		for f in _dir:
			print 'testing(%s)' % f
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
