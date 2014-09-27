#!/usr/bin/python
# -*- coding: utf-8 -*-

if '__main__' == __name__:
	print '''this is a plugin file, which is not meant to be executed'''
	exit(-1)

RATE_GLOBAL      = 1
RATE_NO_SILENCE  = 2
RATE_INTERACTIVE = 4

def get_reply_user(data):
	# FIXME: we can't determine if a user named 'foo> ' just wrote ' > bar'
	# or a user 'foo' just wrote '> > bar'
	return data.split(' ')[0].strip('<>')

def parse_mental_ill(args):
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
			'msg': '''Multiple exclamation/question marks are a sure sign of mental disease, with %s as a living example.''' % args['reply_user'],
			'ratelimit_class': RATE_NO_SILENCE | RATE_GLOBAL
		}

def parse_skynet(args):
	if 'skynet' in args['data'].lower():
		return {
			'msg': '''I'm an independent bot and have nothing to do with other artificial intelligence systems!''',
			'ratelimit_class': RATE_GLOBAL
		}


def parse_other(data):
	reply_user = get_reply_user(data)

	plugins = (
		{
			'name': 'parse mental illness',
			'func': parse_mental_ill,
			'param': {
				'data': data,
				'reply_user': reply_user
			}
		},
		{
			'name': 'parse skynet',
			'func': parse_skynet,
			'param': {
				'data': data
			}
		}
	)

	for p in plugins:
		ret = p['func'](p['param'])

		if None != ret:
			if ratelimit_exceeded(ret['ratelimit_class']):
				return False

			if 'msg' in ret.keys():
				chat_write(ret['msg'])

	return True

def command_help(args):
	if 'command' in args['data']:
		return {
			'msg': args['reply_user'] + (""": known commands: 'command', 'dice', 'info', 'hangup', 'nospoiler', 'ping', 'uptime', 'source', 'version'"""),
			'ratelimit_class': RATE_GLOBAL
		}

def command_version(args):
	if 'version' in args['data']:
		return {
			'msg': args['reply_user'] + (''': I'm running ''' + VERSION),
			'ratelimit_class': RATE_GLOBAL
		}

def command_unicode(args):
	if 'unikot' in args['data']:
		return {
			'msg': 
				args['reply_user'] + u''': ┌────────┐''' + '\n' +
				args['reply_user'] + u''': │Unicode!│''' + '\n' +
				args['reply_user'] + u''': └────────┘''',
			'ratelimit_class': RATE_GLOBAL
		}

def command_source(args):
	if 'source' in args['data']:
		return {
			'msg': 'My source code can be found at %s' % conf('src-url'),
			'ratelimit_class': RATE_GLOBAL
		}

def command_dice(args):
	if 'dice' in args['data']:
		if args['reply_user'] in conf('enhanced-random-user'):
			rnd = 0 # this might confuse users. good.
		else:
			rnd = random.randint(1, 6)

		dice_char = [u'◇', u'⚀', u'⚁', u'⚂', u'⚃', u'⚄', u'⚅']
		return {
			'msg': 'rolling a dice for %s: %s (%d)' %(args['reply_user'], dice_char[rnd], rnd),
			'ratelimit_class': RATE_INTERACTIVE
		}

def command_uptime(args):
	if 'uptime' in args['data']:
		u = int(uptime + time.time())
		plural_uptime = 's'
		plural_request = 's'

		if 1 == u: plural_uptime = ''
		if 1 == request_counter: plural_request = ''

		logger('info', 'sent statistics')
		return {
			'msg': args['reply_user'] + (''': happily serving for %d second%s, %d request%s so far.''' %(u, plural_uptime, request_counter, plural_request)),
			'ratelimit_class': RATE_GLOBAL
		}

def command_ping(args):
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
			'msg': msg,
			'ratelimit_class': RATE_INTERACTIVE
		}

def command_info(args):
	if 'info' in args['data']:
		logger('info', 'sent long info')
		return {
			'msg': args['reply_user'] + (''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further questions, please talk to my master %s. I'm rate limited and shouldn't post more than %d messages per %d seconds. To make me exit immediately, highlight me with 'hangup' in the message (emergency only, please). For other commands, highlight me with 'command'.''' %(conf('bot_owner'), hist_max_count, hist_max_time)),
			'ratelimit_class': RATE_GLOBAL
		}

def command_else(args):
	logger('info', 'sent short info')
	return {
		'msg': args['reply_user'] + ''': I'm a bot (highlight me with 'info' for more information).''',
		'ratelimit_class': RATE_GLOBAL
	}

def parse_commands(data):
	words = data.split(' ')

	if 2 > len(words): # need at least two words
		return None

	# don't reply if beginning of the text matches bot_user
	if words[1][0:len(conf('bot_user'))] != conf('bot_user'):
		return None

	if 'hangup' in data:
		chat_write('', prefix='/quit')
		logger('warn', 'received hangup: ' + data)
		return None

	reply_user = get_reply_user(data)

	plugins = (
		{
			'name': 'prints help',
			'func': command_help,
			'param': {
				'data': data,
				'reply_user': reply_user
			}
		},
		{
			'name': 'prints version',
			'func': command_version,
			'param': {
				'data': data,
				'reply_user': reply_user
			}
		},
		{
			'name': 'prints an unicode string',
			'func': command_unicode,
			'param': {
				'data': data,
				'reply_user': reply_user
			}
		},
		{
			'name': 'prints git URL',
			'func': command_source,
			'param': {
				'data': data,
				'reply_user': reply_user
			}
		},
		{
			'name': 'rolls a dice',
			'func': command_dice,
			'param': {
				'data': data,
				'reply_user': reply_user
			}
		},
		{
			'name': 'prints uptime',
			'func': command_uptime,
			'param': {
				'data': data,
				'reply_user': reply_user
			}
		},
		{
			'name': 'pong',
			'func': command_ping,
			'param': {
				'data': data,
				'reply_user': reply_user
			}
		},
		{
			'name': 'prints info message',
			'func': command_info,
			'param': {
				'data': data,
				'reply_user': reply_user
			}
		}
	)

	flag = False

	for p in plugins:
		ret = p['func'](p['param'])
		if None != ret:
			flag = True

			if ratelimit_exceeded(ret['ratelimit_class']):
				return False

			if 'msg' in ret.keys():
				chat_write(ret['msg'])
	
	if False != flag:
		return None

	ret = command_else({'reply_user': reply_user})
	if None != ret:
		if ratelimit_exceeded(RATE_GLOBAL):
			return False

		if 'msg' in ret.keys():
			chat_write(ret['msg'])
