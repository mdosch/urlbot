#!/usr/bin/python3
# -*- coding: utf-8 -*-

if '__main__' == __name__:
	print('''this is a plugin file, which is not meant to be executed''')
	exit(-1)

import time, random, unicodedata, re, sys, urllib.request, json
from local_config import conf, set_conf
from common import *
from urlbot import extract_title

joblist = []

plugins = {}
plugins['parse'] = []
plugins['command'] = []

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

def parse_debbug(args):
	if 'register' == args:
		return {
			'name': 'parse Debian bug numbers',
			'args': ('data',),
			'ratelimit_class': RATE_NO_SILENCE | RATE_GLOBAL
		}

	bugs = re.findall(r'#(\d{4,})', args['data'])
	if not bugs:
		return None

	url = 'https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=%s' % bugs[0]
	status, title = extract_title(url)

	if 0 == status:
		title = 'Debian Bug: %s: %s' % (title, url)
	elif 3 == status:
		pass
	else:
		return None

	logger('plugin', 'detected Debian bug')
	return {
		'msg': title
	}

def parse_cve(args):
	if 'register' == args:
		return {
			'name': 'parse a CVE handle',
			'args': ('data',),
			'ratelimit_class': RATE_NO_SILENCE | RATE_GLOBAL
		}

	cves = re.findall(r'(CVE-\d\d\d\d-\d+)', args['data'].upper())
	if not cves:
		return None

	logger('plugin', 'detected CVE handle')
	return {
		'msg': 'https://security-tracker.debian.org/tracker/%s' % cves[0]
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

def data_parse_other(msg_obj):
	data = msg_obj['body']
	reply_user = msg_obj['mucnick']

	for p in plugins['parse']:
		if ratelimit_exceeded(p['ratelimit_class']):
			continue

		args = {}

		if 'args' in list(p.keys()):
			for a in p['args']:
				if None == a:
					continue

				if 'data' == a:
					args['data'] = data
				elif 'reply_user' == a:
					args['reply_user'] = reply_user
				else:
					logger('warn', 'unknown required arg for %s: %s' % (p['name'], a))

		ret = p['func'](args)

		if None != ret:
			if 'msg' in list(ret.keys()):
				ratelimit_touch(RATE_CHAT)
				send_reply(ret['msg'], msg_obj)

def command_help(args):
	if 'register' == args:
		return {
			'name': 'help',
			'desc': 'print help for a command or all known commands',
			'args': ('argv0', 'argv1', 'reply_user', 'cmd_list'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	command = args['argv0']
	what = args['argv1']

	if 'help' != command:
		return

	if None == what:
		logger('plugin', 'empty help request, sent all commands')
		return {
			'msg': args['reply_user'] + ': known commands: ' +
			str(args['cmd_list']).strip('[]')
		}

	if not what in [p['name'] for p in plugins['command']]:
		logger('plugin', 'no help found for %s' % what)
		return {
			'msg': args['reply_user'] + ': no such command: %s' % what
		}

	for p in plugins['command']:
		if what == p['name']:
			logger('plugin', 'sent help for %s' % what)
			return {
				'msg': args['reply_user'] + ': help for %s: %s' % (
					what, p['desc']
				)
			}


def command_version(args):
	if 'register' == args:
		return {
			'name': 'version',
			'desc': 'prints version',
			'args': ('argv0', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'version' != args['argv0']:
		return

	logger('plugin', 'sent version string')
	return {
		'msg': args['reply_user'] + (''': I'm running ''' + VERSION)
	}

def command_klammer(args):
	if 'register' == args:
		return {
			'name': 'klammer',
			'desc': 'prints an anoying paper clip aka. Karl Klammer',
			'args': ('argv0', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'klammer' != args['argv0']:
		return

	logger('plugin', 'sent karl klammer')
	return {
		'msg': (
			args['reply_user'] + ',',
			r''' _, Was moechten''',
			r'''( _\_   Sie tun?''',
			r''' \0 O\          ''',
			r'''  \\ \\  [ ] ja ''',
			r'''   \`' ) [ ] noe''',
			r'''    `''         '''
		)
	}

def command_unicode(args):
	if 'register' == args:
		return {
			'name': 'unikot',
			'desc': 'prints an unicode string',
			'args': ('argv0', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'unikot' != args['argv0']:
		return

	logger('plugin', 'sent some unicode')
	return {
		'msg': (
			args['reply_user'] + ''', here's some''',
			'''┌────────┐''',
			'''│Unicode!│''',
			'''└────────┘'''
		)
	}

def command_source(args):
	if 'register' == args:
		return {
			'name': 'source',
			'desc': 'prints git URL',
			'args': ('argv0', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if not args['argv0'] in ('source', 'src'):
		return

	logger('plugin', 'sent source URL')
	return {
		'msg': 'My source code can be found at %s' % conf('src-url')
	}

def command_dice(args):
	if 'register' == args:
		return {
			'name': 'dice',
			'desc': 'rolls a dice, optional N times',
			'args': ('argv0', 'argv1', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_INTERACTIVE
		}

	if 'dice' != args['argv0']:
		return

	count = 0

	try:
		count = 1 if None is args['argv1'] else int(args['argv1'])
	except ValueError as e:
		return {
			'msg': '%s: dice: error when parsing int(%s): %s' % (
				args['reply_user'], args['argv1'], str(e)
			)
		}

	if 0 >= count or 5 <= count:
		return {
			'msg': '%s: dice: invalid arguments (0 < N < 5)' % args['reply_user']
		}

	dice_char = ['◇', '⚀', '⚁', '⚂', '⚃', '⚄', '⚅']

	msg = 'rolling %s for %s:' % (
		'a dice' if 1 == count else '%d dices' % count, args['reply_user']
	)

	for i in range(count):
		rnd = 0
		if args['reply_user'] in conf('enhanced-random-user'):
			rnd = 0  # this might confuse users. good.
			logger('plugin', 'sent random (enhanced)')
		else:
			rnd = random.randint(1, 6)
			logger('plugin', 'sent random')

		msg += ' %s (%d)' % (dice_char[rnd], rnd)

	return {
		'msg': msg
	}

def command_uptime(args):
	if 'register' == args:
		return {
			'name': 'uptime',
			'desc': 'prints uptime',
			'args': ('argv0', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'uptime' != args['argv0']:
		return

	u = int(conf('uptime') + time.time())
	plural_uptime = 's'
	plural_request = 's'

	if 1 == u:
		plural_uptime = ''
	if 1 == conf('request_counter'):
		plural_request = ''

	logger('plugin', 'sent statistics')
	return {
		'msg': args['reply_user'] + (''': happily serving for %d second%s, %d request%s so far.''' % (u, plural_uptime, conf('request_counter'), plural_request))
	}

def command_ping(args):
	if 'register' == args:
		return {
			'name': 'ping',
			'desc': 'sends pong',
			'args': ('argv0', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_INTERACTIVE
		}

	if 'ping' != args['argv0']:
		return

	rnd = random.randint(0, 3)  # 1:4
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
			'args': ('argv0', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'info' != args['argv0']:
		return

	logger('plugin', 'sent long info')
	return {
		'msg': args['reply_user'] + (''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further questions, please talk to my master %s. I'm rate limited and shouldn't post more than %d messages per %d seconds. To make me exit immediately, highlight me with 'hangup' in the message (emergency only, please). For other commands, highlight me with 'command'.''' % (conf('bot_owner'), conf('hist_max_count'), conf('hist_max_time')))
	}

def command_teatimer(args):
	if 'register' == args:
		return {
			'name': 'teatimer',
			'desc': 'sets a tea timer to $1 or currently %d seconds' % conf('tea_steep_time'),
			'args': ('reply_user', 'msg_obj', 'argv0', 'argv1'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'teatimer' != args['argv0']:
		return

	steep = conf('tea_steep_time')

	if None != args['argv1']:
		try:
			steep = int(args['argv1'])
		except Exception as e:
			return {
				'msg': args['reply_user'] + ': error when parsing int(%s): %s' % (
					args['argv1'], str(e)
				)
			}

	ready = time.time() + steep

	try:
		logger('plugin', 'tea timer set to %s' % time.strftime('%F.%T', time.localtime(ready)))
	except ValueError as e:
		return {
			'msg': args['reply_user'] + ': time format error: ' + str(e)
		}

# FIXME: this is currently broken because the msg_obj gets modified by the very
#        first reply and can't be reused to .reply() with another message
	register_event(ready, send_reply, (args['reply_user'] + ': Your tea is ready!', args['msg_obj']))

	return {
		'msg': args['reply_user'] + ': Tea timer set to %s' % time.strftime(
			'%F.%T', time.localtime(ready)
		)
	}

def command_decode(args):
	if 'register' == args:
		return {
			'name': 'decode',
			'desc': 'prints the long description of an unicode character',
			'args': ('argv0', 'argv1', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'decode' != args['argv0']:
		return

	if None == args['argv1']:
		return {
			'msg': args['reply_user'] + ': usage: decode {single character}'
		}

	char = args['argv1']
	char_esc = str(char.encode('unicode_escape'))[3:-1]
	logger('plugin', 'decode called for %s' % char)

	try:
		uni_name = unicodedata.name(char)
	except Exception as e:
		logger('plugin', 'decode(%s) failed: %s' % (char, str(e)))
		return {
			'msg': args['reply_user'] + ": can't decode %s (%s): %s" % (char, char_esc, str(e))
		}

	return {
		'msg': args['reply_user'] + ': %s (%s) is called "%s"' % (char, char_esc, uni_name)
	}

def command_show_blacklist(args):
	if 'register' == args:
		return {
			'name': 'show-blacklist',
			'desc': 'show the current URL blacklist, optionally filtered',
			'args': ('argv0', 'reply_user', 'argv1'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'show-blacklist' != args['argv0']:
		return

	logger('plugin', 'sent URL blacklist')

	return {
		'msg': [
			args['reply_user'] + ': URL blacklist%s: ' % (
				'' if not args['argv1'] else ' (limited to %s)' % args['argv1']
			)
		] + [
			b for b in conf('url_blacklist')
			if not args['argv1'] or args['argv1'] in b
		]
	}

def usersetting_get(args):
	blob = conf_load()

	arg_user = args['reply_user']
	arg_key = args['argv1']

	if not arg_user in blob['user_pref']:
		return {
			'msg': args['reply_user'] + ': user key not found'
		}

	return {
		'msg': args['reply_user'] + ': %s == %s' % (
			arg_key,
			'on' if blob['user_pref'][arg_user][arg_key] else 'off'
		)
	}


def command_usersetting(args):
	if 'register' == args:
		return {
			'name': 'set',
			'desc': 'modify a user setting',
			'args': ('reply_user', 'argv0', 'argv1', 'argv2', 'msg_obj'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'set' != args['argv0']:
		return

	settings = ['spoiler']
	arg_user = args['reply_user']
	arg_key = args['argv1']
	arg_val = args['argv2']

	if not arg_key in settings:
		return {
			'msg': args['reply_user'] + ': known settings: ' + (', '.join(settings))
		}

	if not arg_val in ['on', 'off', None]:
		return {
			'msg': args['reply_user'] + ': possible values for %s: on, off' % arg_key
		}

	if None == arg_val:
		# display current value
		return usersetting_get(args)

	if conf('persistent_locked'):
		return {
			'msg': args['reply_user'] + ''': couldn't get exclusive lock'''
		}

	set_conf('persistent_locked', True)
	blob = conf_load()

	if not arg_user in blob['user_pref']:
		blob['user_pref'][arg_user] = {}

	blob['user_pref'][arg_user][arg_key] = (
		True if 'on' == arg_val else False
	)

	conf_save(blob)
	set_conf('persistent_locked', False)

	# display value written to db
	return usersetting_get(args)

def command_cake(args):
	if 'register' == args:
		return {
			'name': 'cake',
			'desc': 'displays a cake ASCII art',
			'args': ('argv0', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'cake' != args['argv0']:
		return

	return {
		'msg': args['reply_user'] + ': no cake for you'
	}

def command_remember(args):
	if 'register' == args:
		return {
			'name': 'remember',
			'desc': 'remembers something',
			'args': ('argv0', 'argv1', 'data', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'remember' != args['argv0']:
		return

	logger('plugin', 'remember plugin called')

	if not args['argv1']:
		return {
			'msg': args['reply_user'] + ': invalid message'
		}

	print(args['data'])
	to_remember = ' '.join(args['data'].split()[2:])  # this is a little dirty. A little lot
	set_conf('data_remember', to_remember)

	return {
		'msg': args['reply_user'] + ': remembering ' + to_remember
	}

def command_recall(args):
	if 'register' == args:
		return {
			'name': 'recall',
			'desc': "recalls something previously 'remember'ed",
			'args': ('argv0', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'recall' != args['argv0']:
		return

	logger('plugin', 'recall plugin called')

	return {
		'msg': args['reply_user'] + ': recalling %s' % conf('data_remember')
	}

def command_plugin_activation(args):
	if 'register' == args:
		return {
			'name': 'plugin',
			'desc': "'disable' or 'enable' plugins",
			'args': ('argv0', 'argv1', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	command = args['argv0']
	plugin = args['argv1']

	if not command in ('enable', 'disable'):
		return

	logger('plugin', 'plugin activation plugin called')

	if None == plugin:
		return {
			'msg': args['reply_user'] + ': no plugin given'
		}
	elif 'plugin' == plugin:
		return {
			'msg': args['reply_user'] + ': not allowed'
		}

	for i, c in enumerate(plugins['command']):
		if c['name'] == plugin:
			plugins['command'][i]['is_enabled'] = \
				True if 'enable' == command else False

			return {
				'msg': args['reply_user'] + ': %sd %s' %(
					command, plugin
				)
			}

	return {
		'msg': args['reply_user'] + ': unknown plugin %s' % plugin
	}

def command_wp_en(args):
	if 'register' == args:
		return {
			'name': 'wp-en',
			'desc': 'crawl the english Wikipedia',
			'args': ('argv0', 'argv1', 'argv2', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'wp-en' != args['argv0']:
		return

	if args['argv0']:
		args['argv0'] = 'wp'

	return command_wp(args, lang='en')

def command_wp(args, lang='de'):
	if 'register' == args:
		return {
			'name': 'wp',
			'desc': 'crawl the german Wikipedia',
			'args': ('argv0', 'argv1', 'argv2', 'reply_user'),
			'is_enabled': True,
			'ratelimit_class': RATE_GLOBAL
		}

	if 'wp' != args['argv0']:
		return

	logger('plugin', 'wp plugin called')

	query = args['argv1']
	# FIXME: escaping. probably.
	api = ('https://%s.wikipedia.org/w/api.php?action=query&prop=extracts&' + \
		'explaintext&exsentences=2&rawcontinue=1&format=json&titles=%s') % (
			lang, query
		)
	link = 'https://%s.wikipedia.org/wiki/%s' % (lang, query)

	(j, short) = (None, None)
	failed = False

	try:
		response = urllib.request.urlopen(api)
		buf = response.read(BUFSIZ)
		j = json.loads(buf.decode('utf-8'))
	except Exception as e:
		logger('plugin', 'wp(%s) failed: %s' % (query, str(e)))
		return {
			'msg': args['reply_user'] + ": something failed: %s" % str(e)
		}

	# FIXME: this looks rather shitty. We're looking for
	# >>> j['query']['pages']['88112']['extract'] == str()
	if not 'query' in j:
		failed = True
	else:
		j = j['query']
		if not 'pages' in j:
			failed = True
		else:
			j = j['pages']
			flag = True
			for stuff in j:
				if 'extract' in j[stuff]:
					flag = False
					j = j[stuff]['extract']
					break
			failed = flag

	if failed:
		return {
			'msg': args['reply_user'] + ': the json object looks bad, sorry for that.'
		}
	else:
		short = str(j)

	return {
		'msg': args['reply_user'] + ': %s (<%s>)' % (
			'(nix)' if 0 == len(short.strip()) else short, link
		)
	}

#def command_dummy(args):
#	if 'register' == args:
#		return {
#			'name': 'dummy',
#			'desc': 'dummy description',
#			'args': ('argv0', 'reply_user'),
#			'is_enabled': True,
#			'ratelimit_class': RATE_GLOBAL
#		}
#
#	if 'dummy' != args['argv0']:
#		return
#
#	logger('plugin', 'dummy plugin called')
#
#	return {
#		'msg': args['reply_user'] + ': dummy plugin called'
#	}

def command_else(args):
	logger('plugin', 'sent short info')
	return {
		'msg': args['reply_user'] + ''': I'm a bot (highlight me with 'info' for more information).'''
	}

def data_parse_commands(msg_obj):
	data = msg_obj['body']
	words = data.split(' ')

	if 2 > len(words):  # need at least two words
		return None

	# don't reply if beginning of the text matches bot_user
	if not data.startswith(conf('bot_user')):
		return None

	if 'hangup' in data:
		logger('warn', 'received hangup: ' + data)
		sys.exit(1)
		return None

	reply_user = msg_obj['mucnick']
	(argv0, argv1, argv2) = (None, None, None)
	if 1 < len(words):
		argv0 = words[1]
	if 2 < len(words):
		argv1 = words[2]
	if 3 < len(words):
		argv2 = words[3]

	for p in plugins['command']:
		if ratelimit_exceeded(p['ratelimit_class']):
			continue

		if not p['is_enabled']:
			continue

		args = {}

		if 'args' in list(p.keys()):
			for a in p['args']:
				if None == a:
					continue

				if 'data' == a:
					args['data'] = data
				elif 'cmd_list' == a:
					cmds = [c['name'] for c in plugins['command']]
					cmds.sort()
					args['cmd_list'] = cmds
				elif 'reply_user' == a:
					args['reply_user'] = reply_user
				elif 'msg_obj' == a:
					args['msg_obj'] = msg_obj
				elif 'argv0' == a:
					args['argv0'] = argv0
				elif 'argv1' == a:
					args['argv1'] = argv1
				elif 'argv2' == a:
					args['argv2'] = argv2
				else:
					logger('warn', 'unknown required arg for %s: %s' % (p['name'], a))

		ret = p['func'](args)

		if None != ret:
			if 'msg' in list(ret.keys()):
				ratelimit_touch(RATE_CHAT)
				if ratelimit_exceeded(RATE_CHAT):
					return False

				send_reply(ret['msg'], msg_obj)

			return None

	ret = command_else({'reply_user': reply_user})
	if None != ret:
		if ratelimit_exceeded(RATE_GLOBAL):
			return False

		if 'msg' in list(ret.keys()):
			send_reply(ret['msg'], msg_obj)

funcs = {}
funcs['parse'] = (parse_mental_ill, parse_skynet, parse_debbug, parse_cve)
funcs['command'] = (
	command_help, command_version, command_unicode, command_klammer,
	command_source, command_dice, command_uptime, command_ping, command_info,
	command_teatimer, command_decode, command_show_blacklist, command_usersetting,
	command_cake, command_remember, command_recall, command_plugin_activation,
	command_wp, command_wp_en
)

_dir = dir()

if debug_enabled():
	def _send_reply(a, msg_obj):
		logger('send_reply[%s]' % msg_obj, a)

	def _conf(ignored):
		return 'bot'

	def _ratelimit_exceeded(ignored=None):
		return False

	def _ratelimit_touch(ignored=None):
		return True

	try:
		send_reply
	except NameError:
		send_reply = _send_reply

	try:
		conf
	except NameError:
		conf = _conf

	try:
		ratelimit_exceeded
	except NameError:
		ratelimit_exceeded = _ratelimit_exceeded

	try:
		ratelimit_touch
	except NameError:
		ratelimit_touch = _ratelimit_touch

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
				logger('warn', 'auto-registering %s failed: %s' % (f, e))

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

	for (i, (t, callback, args)) in enumerate(joblist):
		if t < now:
			callback(*args)
			del(joblist[i])
