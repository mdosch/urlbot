#!/usr/bin/python3
# -*- coding: utf-8 -*-

if '__main__' == __name__:
	print('''this is a plugin file, which is not meant to be executed''')
	exit(-1)

import time, random, unicodedata, re, sys, urllib.request, json
import types
import traceback
from local_config import conf, set_conf
from common import *
from urlbot import extract_title
from enum import Enum
from functools import wraps

ptypes = Enum("plugin_types", "PARSE COMMAND")

joblist = []

plugins = {p : [] for p in ptypes}

def pluginfunction(name, desc, plugin_type, ratelimit_class = RATE_GLOBAL, enabled = True):
	""" A decorator to make a plugin out of a function """
	if plugin_type not in ptypes:
		raise TypeError("Illegal plugin_type: %s" % plugin_type)

	def decorate(f):
		f.is_plugin = True
		f.is_enabled = True
		f.plugin_name = name
		f.plugin_desc = desc
		f.plugin_type = plugin_type
		f.ratelimit_class = ratelimit_class
		return f
	return decorate

def register_event(t, callback, args):
	joblist.append((t, callback, args))

@pluginfunction("mental_ill", "parse mental illness", ptypes.PARSE, ratelimit_class = RATE_NO_SILENCE | RATE_GLOBAL)
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

@pluginfunction("debbug", "parse Debian bug numbers", ptypes.PARSE, ratelimit_class = RATE_NO_SILENCE | RATE_GLOBAL)
def parse_debbug(**args):
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

@pluginfunction("cve", "parse a CVE handle", ptypes.PARSE, ratelimit_class = RATE_NO_SILENCE | RATE_GLOBAL)
def parse_cve(**args):
	cves = re.findall(r'(CVE-\d\d\d\d-\d+)', args['data'].upper())
	if not cves:
		return None

	logger('plugin', 'detected CVE handle')
	return {
		'msg': 'https://security-tracker.debian.org/tracker/%s' % cves[0]
	}

@pluginfunction("skynet", "parse skynet", ptypes.PARSE) 
def parse_skynet(**args):
	if 'skynet' in args['data'].lower():
		logger('plugin', 'sent skynet reply')
		return {
			'msg': '''I'm an independent bot and have nothing to do with other artificial intelligence systems!'''
		}

def data_parse_other(msg_obj):
	data = msg_obj['body']
	reply_user = msg_obj['mucnick']

	for p in plugins[ptypes.PARSE]:
		if ratelimit_exceeded(p.ratelimit_class):
			continue

		ret = p(reply_user=reply_user, data=data)

		if None != ret:
			if 'msg' in list(ret.keys()):
				ratelimit_touch(RATE_CHAT)
				send_reply(ret['msg'], msg_obj)

@pluginfunction("help", "print help for a command or all known commands", ptypes.COMMAND)  
def command_help(argv,**args):
	command = argv[0]
	what = argv[1] if len(argv) > 1 else None

	if 'help' != command:
		return

	if None == what:
		logger('plugin', 'empty help request, sent all commands')
		return {
			'msg': args['reply_user'] + ': known commands: ' +
			str(args['cmd_list']).strip('[]')
		}

	if not what in [p.plugin_name for p in plugins[ptypes.COMMAND]]:
		logger('plugin', 'no help found for %s' % what)
		return {
			'msg': args['reply_user'] + ': no such command: %s' % what
		}

	for p in plugins[ptypes.COMMAND]:
		if what == p.plugin_name:
			logger('plugin', 'sent help for %s' % what)
			return {
				'msg': args['reply_user'] + ': help for %s: %s' % (
					what, p.plugin_desc
				)
			}

@pluginfunction("version", "prints version", ptypes.COMMAND)
def command_version(argv,**args):
	if 'version' != argv[0]:
		return

	logger('plugin', 'sent version string')
	return {
		'msg': args['reply_user'] + (''': I'm running ''' + VERSION)
	}

@pluginfunction("klammer", "prints an anoying paper clip aka. Karl Klammer", ptypes.COMMAND)
def command_klammer(argv,**args):
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

@pluginfunction("unikot", "prints an unicode string", ptypes.COMMAND)
def command_unicode(argv,**args):
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

@pluginfunction("source", "prints git URL", ptypes.COMMAND)
def command_source(argv,**args):
	if not argv[0] in ('source', 'src'):
		return

	logger('plugin', 'sent source URL')
	return {
		'msg': 'My source code can be found at %s' % conf('src-url')
	}

@pluginfunction("dice", "rolls a dice, optional N times", ptypes.COMMAND, ratelimit_class = RATE_INTERACTIVE)
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

		msg += ' %s (%d)' % (dice_char[rnd], rnd)

	return {
		'msg': msg
	}

@pluginfunction("uptime", "prints uptime", ptypes.COMMAND)
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

@pluginfunction("ping", "sends pong", ptypes.COMMAND, ratelimit_class = RATE_INTERACTIVE)
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

@pluginfunction("info", "prints info message", ptypes.COMMAND)
def command_info(argv,**args):
	if 'info' != argv[0]:
		return

	logger('plugin', 'sent long info')
	return {
		'msg': args['reply_user'] + (''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further questions, please talk to my master %s. I'm rate limited and shouldn't post more than %d messages per %d seconds. To make me exit immediately, highlight me with 'hangup' in the message (emergency only, please). For other commands, highlight me with 'help'.''' % (conf('bot_owner'), conf('hist_max_count'), conf('hist_max_time')))
	}

@pluginfunction("teatimer", 'sets a tea timer to $1 or currently %d seconds' % conf('tea_steep_time'), ptypes.COMMAND)
def command_teatimer(argv,**args):
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

@pluginfunction("decode", "prints the long description of an unicode character", ptypes.COMMAND)
def command_decode(argv,**args):
	if 'decode' != argv[0]:
		return

	if len(argv) < 1:
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

@pluginfunction("show-blacklist", "show the current URL blacklist, optionally filtered", ptypes.COMMAND)
def command_show_blacklist(argv,**args):
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

def usersetting_get(argv,args):
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

@pluginfunction("set", "modify a user setting", ptypes.COMMAND)
def command_usersetting(argv,**args):
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

	if not arg_user in blob['user_pref']:
		blob['user_pref'][arg_user] = {}

	blob['user_pref'][arg_user][arg_key] = (
		True if 'on' == arg_val else False
	)

	conf_save(blob)
	set_conf('persistent_locked', False)

	# display value written to db
	return usersetting_get(argv,args)

@pluginfunction("cake", "displays a cake ASCII art", ptypes.COMMAND)
def command_cake(argv, **args):
	if 'cake' != argv[0]:
		return

	return {
		'msg': args['reply_user'] + ': no cake for you'
	}

@pluginfunction("remember", "remembers something", ptypes.COMMAND)
def command_remember(argv,**args):
	if 'remember' != argv[0]:
		return

	logger('plugin', 'remember plugin called')

	if not len(argv) > 1:
		return {
			'msg': args['reply_user'] + ': invalid message'
		}

	print(args['data'])
	to_remember = ' '.join(args['data'].split()[2:])  # this is a little dirty. A little lot
	set_conf('data_remember', to_remember)

	return {
		'msg': args['reply_user'] + ': remembering ' + to_remember
	}

@pluginfunction("recall", "recalls something previously 'remember'ed", ptypes.COMMAND)
def command_recall(argv,**args):
	if 'recall' != argv[0]:
		return

	logger('plugin', 'recall plugin called')

	return {
		'msg': args['reply_user'] + ': recalling %s' % conf('data_remember')
	}

#TODO: send a hint if someone types plugin as command
@pluginfunction("plugin", "disable' or 'enable' plugins", ptypes.COMMAND)
def command_plugin_activation(argv,**args):
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

	for c in plugins[ptypes.COMMAND]:
		if c.plugin_name == plugin:
			c.is_enabled = 'enable' == command 

			return {
				'msg': args['reply_user'] + ': %sd %s' %(
					command, plugin
				)
			}

	return {
		'msg': args['reply_user'] + ': unknown plugin %s' % plugin
	}

@pluginfunction("wp-en", "crawl the english Wikipedia", ptypes.COMMAND)
def command_wp_en(argv,**args):
	if 'wp-en' != argv[0]:
		return

	if argv[0]:
		argv[0] = 'wp'

	return command_wp(argv, lang="en", **args)

@pluginfunction("wp", "crawl the german Wikipedia", ptypes.COMMAND)
def command_wp(argv,lang="de",**args):
	if 'wp' != argv[0]:
		return

	logger('plugin', 'wp plugin called')

	query = " ".join(argv[1:])

	if query == "":
		return {
            'msg': args['reply_user'] + ": You must enter a query" 
        }

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

	for p in plugins[ptypes.COMMAND]:
		if ratelimit_exceeded(p.ratelimit_class):
			continue

		if not p.is_enabled:
			continue

		ret = p(data = data, 
				cmd_list = [pl.plugin_name for pl in plugins[ptypes.COMMAND]],
				reply_user = reply_user, 
				msg_obj = msg_obj, 
				argv = words[1:])


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
	"""
	Register plugins.
	
	Arguments:
	func_type -- plugin functions with this type (ptypes) will be loaded
	"""

	functions = [f for n,f in globals().items() if type(f) == types.FunctionType 
                    and f.__dict__.get('is_plugin', False) 
                    and f.plugin_type == func_type]
	
	logger('info', 'auto registering plugins: %s' % (", ".join(f.plugin_name for f in functions)))

	for f in functions:
		register_plugin(f, func_type)

def register_plugin(function, func_type):
	try:
		plugins[func_type].append(function)
	except Exception as e:
		logger('warn', 'registering %s failed: %s, %s' % 
			(function, e, traceback.format_exc()))

def register_all():
	register(ptypes.PARSE)
	register(ptypes.COMMAND)

def event_trigger():
	if 0 == len(joblist):
		return

	now = time.time()

	for (i, (t, callback, args)) in enumerate(joblist):
		if t < now:
			callback(*args)
			del(joblist[i])
