#!/usr/bin/python3
# -*- coding: utf-8 -*-

if '__main__' == __name__:
	print('''this is a plugin file, which is not meant to be executed''')
	exit(-1)

import time, random, unicodedata, re, sys, urllib.request, json
import types
import traceback
import urllib.parse
from local_config import conf, set_conf
from common import *
from excuses import excuses
from urlbot import extract_title
from functools import wraps

ptypes_PARSE = 0
ptypes_COMMAND = 1
ptypes = [ptypes_PARSE, ptypes_COMMAND]

joblist = []

plugins = {p : [] for p in ptypes}

def pluginfunction(name, desc, plugin_type, ratelimit_class = RATE_GLOBAL, enabled = True):
	''' A decorator to make a plugin out of a function '''
	if plugin_type not in ptypes:
		raise TypeError('Illegal plugin_type: %s' % plugin_type)

	def decorate(f):
		f.is_plugin = True
		f.is_enabled = enabled
		f.plugin_name = name
		f.plugin_desc = desc
		f.plugin_type = plugin_type
		f.ratelimit_class = ratelimit_class
		return f
	return decorate

def register_event(t, callback, args):
	joblist.append((t, callback, args))

@pluginfunction('mental_ill', 'parse mental illness', ptypes_PARSE, ratelimit_class = RATE_NO_SILENCE | RATE_GLOBAL)
def parse_mental_ill(**args):
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

@pluginfunction('debbug', 'parse Debian bug numbers', ptypes_PARSE, ratelimit_class = RATE_NO_SILENCE | RATE_GLOBAL)
def parse_debbug(**args):
	bugs = re.findall(r'#(\d{4,})', args['data'])
	if not bugs:
		return None

	out = []
	for b in bugs:
		logger('plugin', 'detected Debian bug #%s' % b)

		url = 'https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=%s' % b
		status, title = extract_title(url)

		if 0 == status:
			out.append('Debian Bug: %s: %s' % (title, url))
		elif 3 == status:
			out.append('error for #%s: %s' % (b, title))
		else:
			logger('plugin', 'parse_debbug(): unknown status %d' % status)

	return {
		'msg': out
	}

@pluginfunction('cve', 'parse a CVE handle', ptypes_PARSE, ratelimit_class = RATE_NO_SILENCE | RATE_GLOBAL)
def parse_cve(**args):
	cves = re.findall(r'(CVE-\d\d\d\d-\d+)', args['data'].upper())
	if not cves:
		return None

	logger('plugin', 'detected CVE handle')
	return {
		'msg': ['https://security-tracker.debian.org/tracker/%s' % c for c in cves] 
	}

@pluginfunction('dsa', 'parse a DSA handle', ptypes_PARSE, ratelimit_class = RATE_NO_SILENCE | RATE_GLOBAL)
def parse_dsa(**args):
	dsas = re.findall(r'(DSA-\d\d\d\d-\d+)', args['data'].upper())
	if not dsas:
		return None

	logger('plugin', 'detected DSA handle')
	return {
		'msg': ['https://security-tracker.debian.org/tracker/%s' % d for d in dsas] 
	}

@pluginfunction('skynet', 'parse skynet', ptypes_PARSE)
def parse_skynet(**args):
	if 'skynet' in args['data'].lower():
		logger('plugin', 'sent skynet reply')
		return {
			'msg': '''I'm an independent bot and have nothing to do with other artificial intelligence systems!'''
		}

@pluginfunction('latex', r'reacts on \LaTeX', ptypes_PARSE)
def parse_latex(**args):
	if r'\LaTeX' in args['data']:
		return {
			'msg': '''LaTeX is way too complex for me, I'm happy with fmt(1)'''
		}

@pluginfunction('/me', 'reacts to /me.*%{bot_user}', ptypes_PARSE)
def parse_slash_me(**args):
	if args['data'].lower().startswith('/me') and (conf('bot_user') in args['data'].lower()):
		logger('plugin', 'sent /me reply')

		me_replys = [
			'are you that rude to everybody?',
			'oh, thank you...',
			'do you really think that was nice?',
			'that sounds very interesting...',
			"excuse me, but I'm already late for an appointment"
		]

		return {
			'msg': args['reply_user'] + ': %s' % (random.sample(me_replys, 1)[0])
		}

#@pluginfunction('dummy_parser', 'dummy_parser desc', ptypes_PARSE)
#def parse_skynet(**args):
#	if 'dummy_parser' in args['data'].lower():
#		logger('plugin', 'dummy_parser triggered')
#		return {
#			'msg': 'dummy_parser triggered'
#		}

def data_parse_other(msg_obj):
	data = msg_obj['body']
	reply_user = msg_obj['mucnick']

	for p in plugins[ptypes_PARSE]:
		if ratelimit_exceeded(p.ratelimit_class):
			continue

		ret = p(reply_user=reply_user, data=data)

		if None != ret:
			if 'msg' in list(ret.keys()):
				ratelimit_touch(RATE_CHAT)
				send_reply(ret['msg'], msg_obj)

@pluginfunction('help', 'print help for a command or all known commands', ptypes_COMMAND)
def command_help(argv, **args):
	command = argv[0]
	what = argv[1] if len(argv) > 1 else None

	if 'help' != command:
		return

	if None == what:
		logger('plugin', 'empty help request, sent all commands')
		commands = args['cmd_list']
		commands.sort()
		return {
			'msg': args['reply_user'] + ': known commands: ' +
			str(commands).strip('[]')
		}

	if not what in [p.plugin_name for p in plugins[ptypes_COMMAND]]:
		logger('plugin', 'no help found for %s' % what)
		return {
			'msg': args['reply_user'] + ': no such command: %s' % what
		}

	for p in plugins[ptypes_COMMAND]:
		if what == p.plugin_name:
			logger('plugin', 'sent help for %s' % what)
			return {
				'msg': args['reply_user'] + ': help for %s: %s' % (
					what, p.plugin_desc
				)
			}

@pluginfunction('version', 'prints version', ptypes_COMMAND)
def command_version(argv, **args):
	if 'version' != argv[0]:
		return

	logger('plugin', 'sent version string')
	return {
		'msg': args['reply_user'] + (''': I'm running ''' + VERSION)
	}

@pluginfunction('klammer', 'prints an anoying paper clip aka. Karl Klammer', ptypes_COMMAND)
def command_klammer(argv, **args):
	if 'klammer' != argv[0]:
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

@pluginfunction('unikot', 'prints an unicode string', ptypes_COMMAND)
def command_unicode(argv, **args):
	if 'unikot' != argv[0]:
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

@pluginfunction('source', 'prints git URL', ptypes_COMMAND)
def command_source(argv, **args):
	if not argv[0] in ('source', 'src'):
		return

	logger('plugin', 'sent source URL')
	return {
		'msg': 'My source code can be found at %s' % conf('src-url')
	}

@pluginfunction('dice', 'rolls a dice, optional N times', ptypes_COMMAND, ratelimit_class = RATE_INTERACTIVE)
def command_dice(argv, **args):
	if 'dice' != argv[0]:
		return

	count = 0

	try:
		count = 1 if len(argv) < 2 else int(argv[1])
	except ValueError as e:
		return {
			'msg': '%s: dice: error when parsing int(%s): %s' % (
				args['reply_user'], argv[1], str(e)
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

		# the \u200b chars ('ZERO WIDTH SPACE') avoid interpreting stuff as smileys
		# by some strange clients
		msg += ' %s (\u200b%d\u200b)' % (dice_char[rnd], rnd)

	return {
		'msg': msg
	}

@pluginfunction('uptime', 'prints uptime', ptypes_COMMAND)
def command_uptime(argv, **args):
	if 'uptime' != argv[0]:
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

@pluginfunction('ping', 'sends pong', ptypes_COMMAND, ratelimit_class = RATE_INTERACTIVE)
def command_ping(argv, **args):
	if 'ping' != argv[0]:
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

@pluginfunction('info', 'prints info message', ptypes_COMMAND)
def command_info(argv, **args):
	if 'info' != argv[0]:
		return

	logger('plugin', 'sent long info')
	return {
		'msg': args['reply_user'] + (''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further questions, please talk to my master %s. I'm rate limited and shouldn't post more than %d messages per %d seconds. To make me exit immediately, highlight me with 'hangup' in the message (emergency only, please). For other commands, highlight me with 'help'.''' % (conf('bot_owner'), conf('hist_max_count'), conf('hist_max_time')))
	}

@pluginfunction('teatimer', 'sets a tea timer to $1 or currently %d seconds' % conf('tea_steep_time'), ptypes_COMMAND)
def command_teatimer(argv, **args):
	if 'teatimer' != argv[0]:
		return

	steep = conf('tea_steep_time')

	if len(argv) > 1:
		try:
			steep = int(argv[1])
		except Exception as e:
			return {
				'msg': args['reply_user'] + ': error when parsing int(%s): %s' % (
					argv[1], str(e)
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

@pluginfunction('decode', 'prints the long description of an unicode character', ptypes_COMMAND)
def command_decode(argv, **args):
	if 'decode' != argv[0]:
		return

	if len(argv) <= 1:
		return {
			'msg': args['reply_user'] + ': usage: decode {single character}'
		}

	char = argv[1]
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

@pluginfunction('show-blacklist', 'show the current URL blacklist, optionally filtered', ptypes_COMMAND)
def command_show_blacklist(argv, **args):
	if 'show-blacklist' != argv[0]:
		return

	logger('plugin', 'sent URL blacklist')

	argv1 = None if len(argv) < 2 else argv[1]

	return {
		'msg': [
			args['reply_user'] + ': URL blacklist%s: ' % (
				'' if not argv1 else ' (limited to %s)' % argv1
			)
		] + [
			b for b in conf('url_blacklist')
			if not argv1 or argv1 in b
		]
	}

def usersetting_get(argv, args):
	blob = conf_load()

	arg_user = args['reply_user']
	arg_key = argv[1]

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

@pluginfunction('set', 'modify a user setting', ptypes_COMMAND)
def command_usersetting(argv, **args):
	if 'set' != argv[0]:
		return

	settings = ['spoiler']
	arg_user = args['reply_user']
	arg_key = argv[1] if len(argv) > 1 else None
	arg_val = argv[2] if len(argv) > 2 else None

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
		return usersetting_get(argv, args)

	if conf('persistent_locked'):
		return {
			'msg': args['reply_user'] + ''': couldn't get exclusive lock'''
		}

	set_conf('persistent_locked', True)
	blob = conf_load()
	
	if 'user_pref' not in blob:
		blob['user_pref'] = {}

	if not arg_user in blob['user_pref']:
		blob['user_pref'][arg_user] = {}

	blob['user_pref'][arg_user][arg_key] = 'on' == arg_val

	conf_save(blob)
	set_conf('persistent_locked', False)

	# display value written to db
	return usersetting_get(argv, args)

@pluginfunction('cake', 'displays a cake ASCII art', ptypes_COMMAND)
def command_cake(argv, **args):
	if 'cake' != argv[0]:
		return

	cakes = [ "No cake for you!",
			("The Enrichment Center is required to remind you "
			"that you will be baked, and then there will be cake."),
			"The cake is a lie!",
			("This is your fault. I'm going to kill you. "
			"And all the cake is gone. You don't even care, do you?"),
			"Quit now and cake will be served immediately.",
			("Enrichment Center regulations require both hands to be "
			"empty before any cake..."),
			("Uh oh. Somebody cut the cake. I told them to wait for "
			"you, but they did it anyway. There is still some left, "
			"though, if you hurry back."),
			"I'm going to kill you, and all the cake is gone.",
			"Who's gonna make the cake when I'm gone? You?"	]

	return {
		'msg': args['reply_user'] + ': %s' % (random.sample(cakes, 1)[0])
	}

@pluginfunction('remember', 'remembers something', ptypes_COMMAND)
def command_remember(argv, **args):
	if 'remember' != argv[0]:
		return

	logger('plugin', 'remember plugin called')

	if not len(argv) > 1:
		return {
			'msg': args['reply_user'] + ': invalid message'
		}

	to_remember = ' '.join(args['data'].split()[2:])  # this is a little dirty. A little lot
	set_conf('data_remember', to_remember)

	return {
		'msg': args['reply_user'] + ': remembering ' + to_remember
	}

@pluginfunction('recall', "recalls something previously 'remember'ed", ptypes_COMMAND)
def command_recall(argv, **args):
	if 'recall' != argv[0]:
		return

	logger('plugin', 'recall plugin called')

	return {
		'msg': args['reply_user'] + ': recalling %s' % conf('data_remember')
	}

#TODO: send a hint if someone types plugin as command
@pluginfunction('plugin', "'disable' or 'enable' plugins", ptypes_COMMAND)
def command_plugin_activation(argv, **args):
	command = argv[0]
	plugin = argv[1] if len(argv) > 1 else None

	if not command in ('enable', 'disable'):
		return

	logger('plugin', 'plugin activation plugin called')

	if None == plugin:
		return {
			'msg': args['reply_user'] + ': no plugin given'
		}
	elif command_plugin_activation.plugin_name == plugin:
		return {
			'msg': args['reply_user'] + ': not allowed'
		}

	for c in plugins[ptypes_COMMAND]:
		if c.plugin_name == plugin:
			c.is_enabled = 'enable' == command

			return {
				'msg': args['reply_user'] + ': %sd %s' % (
					command, plugin
				)
			}

	return {
		'msg': args['reply_user'] + ': unknown plugin %s' % plugin
	}

@pluginfunction('wp-en', 'crawl the english Wikipedia', ptypes_COMMAND)
def command_wp_en(argv, **args):
	if 'wp-en' != argv[0]:
		return

	if argv[0]:
		argv[0] = 'wp'

	return command_wp(argv, lang='en', **args)

@pluginfunction('wp', 'crawl the german Wikipedia', ptypes_COMMAND)
def command_wp(argv, lang='de', **args):
	if 'wp' != argv[0]:
		return

	logger('plugin', 'wp plugin called')

	query = ' '.join(argv[1:])

	if query == '':
		return {
			'msg': args['reply_user'] + ': no query given'
		}

	api = {
		'action': 'query',
		'prop': 'extracts',
		'explaintext': '',
		'redirects': '',
		'exsentences': 2,
		'continue': '',
		'format': 'json',
		'titles': query
	}
	apiurl = 'https://%s.wikipedia.org/w/api.php?%s' % (
		lang, urllib.parse.urlencode(api)
	)

	logger('plugin', 'wp: fetching %s' % apiurl)

	try:
		response = urllib.request.urlopen(apiurl)
		buf = response.read(BUFSIZ)
		j = json.loads(buf.decode('utf8'))

		page = next(iter(j['query']['pages'].values()))
		short = page.get('extract', None)
		linktitle = page.get('title', query).replace(' ', '_')
		link = 'https://%s.wikipedia.org/wiki/%s' % (
			lang, urllib.parse.quote(linktitle)
		)
	except Exception as e:
		logger('plugin', 'wp(%s) failed: %s, %s' % (query, e, traceback.format_exc()))
		return {
			'msg': args['reply_user'] + ': something failed: %s' % e
		}

	if short is not None:
		return {
			'msg': args['reply_user'] + ': %s (<%s>)' % (
				short if short.strip() else '(nix)', link
			)
		}
	elif 'missing' in page:
		return {
			'msg': 'Article "%s" not found' % page.get('title', query)
		}
	else:
		return {
			'msg': 'json data seem to be broken'
		}

@pluginfunction('excuse', 'prints BOFH style excuses', ptypes_COMMAND)
def command_dummy(argv, **args):
	if 'excuse' != argv[0]:
		return

	logger('plugin', 'BOFH plugin called')

	excuse = random.sample(excuses, 1)[0]

	return {
		'msg': args['reply_user'] + ': ' + excuse
	}

#@pluginfunction('dummy', 'dummy description', ptypes_COMMAND)
#def command_dummy(argv, **args):
#	if 'dummy' != argv[0]:
#		return
#
#	logger('plugin', 'dummy plugin called')
#
#	return {
#		'msg': args['reply_user'] + ': dummy plugin called'
#	}

def else_command(args):
	logger('plugin', 'sent short info')
	return {
		'msg': args['reply_user'] + ''': I'm a bot (highlight me with 'info' for more information).'''
	}

def data_parse_commands(msg_obj):
	data = msg_obj['body']
	words = data.split()

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

	for p in plugins[ptypes_COMMAND]:
		if ratelimit_exceeded(p.ratelimit_class):
			continue

		if not p.is_enabled:
			continue

		ret = p(
			data = data,
			cmd_list = [pl.plugin_name for pl in plugins[ptypes_COMMAND]],
			reply_user = reply_user,
			msg_obj = msg_obj,
			argv = words[1:]
		)

		if None != ret:
			if 'msg' in list(ret.keys()):
				ratelimit_touch(RATE_CHAT)
				if ratelimit_exceeded(RATE_CHAT):
					return False

				send_reply(ret['msg'], msg_obj)

			return None

	ret = else_command({'reply_user': reply_user})
	if None != ret:
		if ratelimit_exceeded(RATE_GLOBAL):
			return False

		if 'msg' in list(ret.keys()):
			send_reply(ret['msg'], msg_obj)

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

def register(func_type):
	'''
	Register plugins.

	Arguments:
	func_type -- plugin functions with this type (ptypes) will be loaded
	'''

	functions = [
		f for ignored, f in globals().items()
			if
				type(f) == types.FunctionType
				and f.__dict__.get('is_plugin', False)
				and f.plugin_type == func_type
	]

	logger('info', 'auto registering plugins: %s' % (', '.join(
		f.plugin_name for f in functions
	)))

	for f in functions:
		register_plugin(f, func_type)

def register_plugin(function, func_type):
	try:
		plugins[func_type].append(function)
	except Exception as e:
		logger('warn', 'registering %s failed: %s, %s' %
			(function, e, traceback.format_exc()))

def register_all():
	register(ptypes_PARSE)
	register(ptypes_COMMAND)

def event_trigger():
	if 0 == len(joblist):
		return

	now = time.time()

	for (i, (t, callback, args)) in enumerate(joblist):
		if t < now:
			callback(*args)
			del(joblist[i])
