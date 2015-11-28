# -*- coding: utf-8 -*-
import json
import logging
import random
import re
import time
import traceback
import types
import unicodedata
import urllib.parse
import urllib.request
# from common import *

from common import conf_load, conf_save, RATE_GLOBAL, RATE_NO_SILENCE, VERSION, RATE_INTERACTIVE, BUFSIZ, \
	USER_AGENT, extract_title, RATE_FUN, RATE_NO_LIMIT
from local_config import set_conf, conf
from string_constants import excuses, moin_strings_hi, moin_strings_bye, cakes

ptypes_PARSE = 'parser'
ptypes_COMMAND = 'command'
ptypes = [ptypes_PARSE, ptypes_COMMAND]

joblist = []

plugins = {p: [] for p in ptypes}

log = logging.getLogger(__name__)


def plugin_enabled_get(urlbot_plugin):
	blob = conf_load()

	if 'plugin_conf' in blob:
		if urlbot_plugin.plugin_name in blob['plugin_conf']:
			return blob['plugin_conf'][urlbot_plugin.plugin_name].get('enabled', urlbot_plugin.is_enabled)

	return urlbot_plugin.is_enabled


def plugin_enabled_set(plugin, enabled):
	if conf('persistent_locked'):
		log.warn("couldn't get exclusive lock")
		return False

	set_conf('persistent_locked', True)
	blob = conf_load()

	if 'plugin_conf' not in blob:
		blob['plugin_conf'] = {}

	if plugin.plugin_name not in blob['plugin_conf']:
		blob['plugin_conf'][plugin.plugin_name] = {}

	blob['plugin_conf'][plugin.plugin_name]['enabled'] = enabled

	conf_save(blob)
	set_conf('persistent_locked', False)

	return True


def pluginfunction(name, desc, plugin_type, ratelimit_class=RATE_GLOBAL, enabled=True):
	"""A decorator to make a plugin out of a function
	:param enabled:
	:param ratelimit_class:
	:param plugin_type:
	:param desc:
	:param name:
	"""
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


@pluginfunction('mental_ill', 'parse mental illness', ptypes_PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
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
		if min_ill <= c:
			flag = True
			break

	if flag:
		log.info('sent mental illness reply')
		return {
			'msg': (
				'''Multiple exclamation/question marks are a sure sign of mental disease, with %s as a living example.''' %
				args['reply_user']
			)
		}


@pluginfunction('debbug', 'parse Debian bug numbers', ptypes_PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
def parse_debbug(**args):
	bugs = re.findall(r'#(\d{4,})', args['data'])
	if not bugs:
		return None

	out = []
	for b in bugs:
		log.info('detected Debian bug #%s' % b)

		url = 'https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=%s' % b
		status, title = extract_title(url)

		if 0 == status:
			out.append('Debian Bug: %s: %s' % (title, url))
		elif 3 == status:
			out.append('error for #%s: %s' % (b, title))
		else:
			log.info('unknown status %d' % status)

	return {
		'msg': out
	}


@pluginfunction('cve', 'parse a CVE handle', ptypes_PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
def parse_cve(**args):
	cves = re.findall(r'(CVE-\d\d\d\d-\d+)', args['data'].upper())
	if not cves:
		return None

	log.info('detected CVE handle')
	return {
		'msg': ['https://security-tracker.debian.org/tracker/%s' % c for c in cves]
	}


@pluginfunction('dsa', 'parse a DSA handle', ptypes_PARSE, ratelimit_class=RATE_NO_SILENCE | RATE_GLOBAL)
def parse_dsa(**args):
	dsas = re.findall(r'(DSA-\d\d\d\d-\d+)', args['data'].upper())
	if not dsas:
		return None

	log.info('detected DSA handle')
	return {
		'msg': ['https://security-tracker.debian.org/tracker/%s' % d for d in dsas]
	}


@pluginfunction('skynet', 'parse skynet', ptypes_PARSE, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def parse_skynet(**args):
	if 'skynet' in args['data'].lower():
		return {
			'msg': 'I\'ll be back.'
		}


@pluginfunction('moin', 'parse hi/bye', ptypes_PARSE)
def parse_moin(**args):
	for direction in [moin_strings_hi, moin_strings_bye]:
		for d in direction:
			words = re.split(r'\W+', args['data'])

			# assumption: longer sentences are not greetings
			if 3 < len(args['data'].split()):
				continue

			for w in words:
				if d.lower() == w.lower():
					if args['reply_user'] in conf('moin-disabled-user'):
						log.info('moin blacklist match')
						return

					if args['reply_user'] in conf('moin-modified-user'):
						log.info('being "quiet" for %s' % w)
						return {
							'msg': '/me %s' % random.choice([
								"doesn't say anything at all",
								'whistles uninterested',
								'just ignores this incident'
							])
						}

					log.info('sent %s reply for %s' % (
						'hi' if direction is moin_strings_hi else 'bye', w
					))
					return {
						'msg': '''%s, %s''' % (
							random.choice(direction),
							args['reply_user']
						)
					}


@pluginfunction('latex', r'reacts on \LaTeX', ptypes_PARSE, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def parse_latex(**args):
	if r'\LaTeX' in args['data']:
		return {
			'msg': '''LaTeX is way too complex for me, I'm happy with fmt(1)'''
		}


@pluginfunction('me-action', 'reacts to /me.*%{bot_user}', ptypes_PARSE, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def parse_slash_me(**args):
	if args['data'].lower().startswith('/me') and (conf('bot_user') in args['data'].lower()):
		log.info('sent /me reply')

		me_replys = [
			'are you that rude to everybody?',
			'oh, thank you...',
			'do you really think that was nice?',
			'that sounds very interesting...',
			"excuse me, but I'm already late for an appointment"
		]

		return {
			'msg': args['reply_user'] + ': %s' % random.choice(me_replys)
		}


@pluginfunction('help', 'print help for a command or all known commands', ptypes_COMMAND)
def command_help(argv, **args):
	command = argv[0]
	what = argv[1] if len(argv) > 1 else None

	if 'help' != command:
		return

	if not what:
		log.info('empty help request, sent all commands')
		commands = args['cmd_list']
		commands.sort()
		parsers = args['parser_list']
		parsers.sort()
		return {
			'msg': [
				'%s: known commands: %s' % (
					args['reply_user'], ', '.join(commands)
				),
				'known parsers: %s' % ', '.join(parsers)
			]
		}

	for p in plugins[ptypes_COMMAND] + plugins[ptypes_PARSE]:
		if what == p.plugin_name:
			log.info('sent help for %s' % what)
			return {
				'msg': args['reply_user'] + ': help for %s %s %s: %s' % (
					'enabled' if plugin_enabled_get(p) else 'disabled',
					'parser' if p.plugin_type == ptypes_PARSE else 'command',
					what, p.plugin_desc
				)
			}
	log.info('no help found for %s' % what)
	return {
		'msg': args['reply_user'] + ': no such command: %s' % what
	}


@pluginfunction('version', 'prints version', ptypes_COMMAND)
def command_version(argv, **args):
	if 'version' != argv[0]:
		return

	log.info('sent version string')
	return {
		'msg': args['reply_user'] + (''': I'm running ''' + VERSION)
	}


@pluginfunction('klammer', 'prints an anoying paper clip aka. Karl Klammer', ptypes_COMMAND,
				ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_klammer(argv, **args):
	if 'klammer' != argv[0]:
		return

	log.info('sent karl klammer')
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


@pluginfunction('unikot', 'prints an unicode string', ptypes_COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_unicode(argv, **args):
	if 'unikot' != argv[0]:
		return

	log.info('sent some unicode')
	return {
		'msg': (
			args['reply_user'] + ''', here's some''',
			'''┌────────┐''',
			'''│Unicode!│''',
			'''└────────┘'''
		)
	}


@pluginfunction('source', 'prints git URL', ptypes_COMMAND)
def command_source(argv, **_):
	if argv[0] not in ('source', 'src'):
		return

	log.info('sent source URL')
	return {
		'msg': 'My source code can be found at %s' % conf('src-url')
	}


@pluginfunction('dice', 'rolls a dice, optional N times', ptypes_COMMAND, ratelimit_class=RATE_INTERACTIVE)
def command_dice(argv, **args):
	if 'dice' != argv[0]:
		return
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
		if args['reply_user'] in conf('enhanced-random-user'):
			rnd = 0  # this might confuse users. good.
			log.info('sent random (enhanced)')
		else:
			rnd = random.randint(1, 6)
			log.info('sent random')

		# the \u200b chars ('ZERO WIDTH SPACE') avoid interpreting stuff as smileys
		# by some strange clients
		msg += ' %s (\u200b%d\u200b)' % (dice_char[rnd], rnd)

	return {
		'msg': msg
	}


@pluginfunction('choose', 'chooses randomly between arguments', ptypes_COMMAND, ratelimit_class=RATE_INTERACTIVE)
def command_choose(argv, **args):
	if 'choose' != argv[0]:
		return

	alternatives = argv[1:]

	if 2 > len(alternatives):
		return {
			'msg': '%s: choosing between one or less things is pointless' % args['reply_user']
		}

	choice = random.choice(alternatives)

	log.info('sent random choice')
	return {
		'msg': '%s: I prefer %s!' % (args['reply_user'], choice)
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

	log.info('sent statistics')
	return {
		'msg': args['reply_user'] + (''': happily serving for %d second%s, %d request%s so far.''' % (
			u, plural_uptime, int(conf('request_counter')), plural_request))
	}


@pluginfunction('ping', 'sends pong', ptypes_COMMAND, ratelimit_class=RATE_INTERACTIVE)
def command_ping(argv, **args):
	if 'ping' != argv[0]:
		return

	rnd = random.randint(0, 3)  # 1:4
	if 0 == rnd:
		msg = args['reply_user'] + ''': peng (You're dead now.)'''
		log.info('sent pong (variant)')
	elif 1 == rnd:
		msg = args['reply_user'] + ''': I don't like you, leave me alone.'''
		log.info('sent pong (dontlike)')
	else:
		msg = args['reply_user'] + ''': pong'''
		log.info('sent pong')

	return {
		'msg': msg
	}


@pluginfunction('info', 'prints info message', ptypes_COMMAND)
def command_info(argv, **args):
	if 'info' != argv[0]:
		return

	log.info('sent long info')
	return {
		'msg': args['reply_user'] + (
			''': I'm a bot, my job is to extract <title> tags from posted URLs. In case I'm annoying or for further
			questions, please talk to my master %s. I'm rate limited.
			To make me exit immediately, highlight me with 'hangup' in the message
			(emergency only, please). For other commands, highlight me with 'help'.''' % (
				conf('bot_owner')))
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
		log.info('tea timer set to %s' % time.strftime('%F.%T', time.localtime(ready)))
	except (ValueError, OverflowError) as e:
		return {
			'msg': args['reply_user'] + ': time format error: ' + str(e)
		}

	return {
		'msg': args['reply_user'] + ': Tea timer set to %s' % time.strftime(
			'%F.%T', time.localtime(ready)
		),
		'event': {
			'time': ready,
			'msg': (args['reply_user'] + ': Your tea is ready!')
		}
	}


@pluginfunction('decode', 'prints the long description of an unicode character', ptypes_COMMAND,
				ratelimit_class=RATE_INTERACTIVE)
def command_decode(argv, **args):
	if 'decode' != argv[0]:
		return

	if len(argv) <= 1:
		return {
			'msg': args['reply_user'] + ': usage: decode {single character}'
		}

	log.info('decode called for %s' % argv[1])

	out = []
	for i, char in enumerate(argv[1]):
		if i > 9:
			out.append('... limit reached.')
			break

		char_esc = str(char.encode('unicode_escape'))[3:-1]

		if 0 == len(char_esc):
			char_esc = ''
		else:
			char_esc = ' (%s)' % char_esc

		try:
			uni_name = unicodedata.name(char)
		except Exception as e:
			log.info('decode(%s) failed: %s' % (char, e))
			out.append("can't decode %s%s: %s" % (char, char_esc, e))
			continue

		out.append('%s%s is called "%s"' % (char, char_esc, uni_name))

	if 1 == len(out):
		return {
			'msg': args['reply_user'] + ': %s' % out[0]
		}
	else:
		return {
			'msg': [args['reply_user'] + ': decoding %s:' % argv[1]] + out
		}


@pluginfunction('show-blacklist', 'show the current URL blacklist, optionally filtered', ptypes_COMMAND)
def command_show_blacklist(argv, **args):
	if 'show-blacklist' != argv[0]:
		return

	log.info('sent URL blacklist')

	argv1 = None if len(argv) < 2 else argv[1]

	return {
		'msg': [
				   args['reply_user'] + ': URL blacklist%s: ' % (
					   '' if not argv1 else ' (limited to %s)' % argv1
				   )
			   ] + [
				   b for b in conf('url_blacklist') if not argv1 or argv1 in b
				   ]
	}


def usersetting_get(argv, args):
	blob = conf_load()

	arg_user = args['reply_user']
	arg_key = argv[1]

	if arg_user not in blob['user_pref']:
		return {
			'msg': args['reply_user'] + ': user key not found'
		}

	return {
		'msg': args['reply_user'] + ': %s == %s' % (
			arg_key,
			'on' if blob['user_pref'][arg_user][arg_key] else 'off'
		)
	}


@pluginfunction('set', 'modify a user setting', ptypes_COMMAND, ratelimit_class=RATE_NO_LIMIT)
def command_usersetting(argv, **args):
	if 'set' != argv[0]:
		return

	settings = ['spoiler']
	arg_user = args['reply_user']
	arg_key = argv[1] if len(argv) > 1 else None
	arg_val = argv[2] if len(argv) > 2 else None

	if arg_key not in settings:
		return {
			'msg': args['reply_user'] + ': known settings: ' + (', '.join(settings))
		}

	if arg_val not in ['on', 'off', None]:
		return {
			'msg': args['reply_user'] + ': possible values for %s: on, off' % arg_key
		}

	if not arg_val:
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

	if arg_user not in blob['user_pref']:
		blob['user_pref'][arg_user] = {}

	blob['user_pref'][arg_user][arg_key] = 'on' == arg_val

	conf_save(blob)
	set_conf('persistent_locked', False)

	# display value written to db
	return usersetting_get(argv, args)


@pluginfunction('cake', 'displays a cake ASCII art', ptypes_COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_cake(argv, **args):
	if 'cake' != argv[0]:
		return

	return {
		'msg': args['reply_user'] + ': %s' % (random.sample(cakes, 1)[0])
	}


# TODO: send a hint if someone types plugin as command
@pluginfunction('plugin', "'disable' or 'enable' plugins", ptypes_COMMAND)
def command_plugin_activation(argv, **args):
	command = argv[0]
	plugin = argv[1] if len(argv) > 1 else None

	if command not in ('enable', 'disable'):
		return

	log.info('plugin activation plugin called')

	if not plugin:
		return {
			'msg': args['reply_user'] + ': no plugin given'
		}
	elif command_plugin_activation.plugin_name == plugin:
		return {
			'msg': args['reply_user'] + ': not allowed'
		}

	for p in plugins[ptypes_COMMAND] + plugins[ptypes_PARSE]:
		if p.plugin_name == plugin:
			plugin_enabled_set(p, 'enable' == command)

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

	log.info('fetching %s' % apiurl)

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
		log.info('wp(%s) failed: %s, %s' % (query, e, traceback.format_exc()))
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
def command_excuse(argv, **args):
	if 'excuse' != argv[0]:
		return

	log.info('BOFH plugin called')

	excuse = random.sample(excuses, 1)[0]

	return {
		'msg': args['reply_user'] + ': ' + excuse
	}


@pluginfunction('show-moinlist', 'show the current moin reply list, optionally filtered', ptypes_COMMAND)
def command_show_moinlist(argv, **args):
	if 'show-moinlist' != argv[0]:
		return

	log.info('sent moin reply list')

	argv1 = None if len(argv) < 2 else argv[1]

	return {
		'msg':
			'%s: moin reply list%s: %s' % (
				args['reply_user'],
				'' if not argv1 else ' (limited to %s)' % argv1,
				', '.join([
							  b for b in moin_strings_hi + moin_strings_bye
							  if not argv1 or argv1.lower() in b.lower()
							  ])
			)
	}


@pluginfunction('list', 'list plugin and parser status', ptypes_COMMAND)
def command_list(argv, **args):
	if 'list' != argv[0]:
		return

	log.info('list plugin called')

	if 'enabled' in argv and 'disabled' in argv:
		return {
			'msg': args['reply_user'] + ": both 'enabled' and 'disabled' makes no sense"
		}

	# if not given, asume both
	if 'command' not in argv and 'parser' not in argv:
		argv.append('command')
		argv.append('parser')

	out_command = []
	out_parser = []
	if 'command' in argv:
		out_command = plugins[ptypes_COMMAND]
	if 'parser' in argv:
		out_parser = plugins[ptypes_PARSE]
	if 'enabled' in argv:
		out_command = [p for p in out_command if plugin_enabled_get(p)]
		out_parser = [p for p in out_parser if plugin_enabled_get(p)]
	if 'disabled' in argv:
		out_command = [p for p in out_command if not plugin_enabled_get(p)]
		out_parser = [p for p in out_parser if not plugin_enabled_get(p)]

	msg = [args['reply_user'] + ': list of plugins:']

	if out_command:
		msg.append('commands: %s' % ', '.join([p.plugin_name for p in out_command]))
	if out_parser:
		msg.append('parsers: %s' % ', '.join([p.plugin_name for p in out_parser]))
	return {'msg': msg}


@pluginfunction(
	'record', 'record a message for a now offline user (usage: record {user} {some message})', ptypes_COMMAND)
def command_record(argv, **args):
	if 'record' != argv[0]:
		return

	if 3 > len(argv):
		return {
			'msg': '%s: usage: record {user} {some message}' % args['reply_user']
		}

	target_user = argv[1].lower()
	message = '%s (%s): ' % (args['reply_user'], time.strftime('%F.%T'))
	message += ' '.join(argv[2:])

	if conf('persistent_locked'):
		return {
			'msg': "%s: couldn't get exclusive lock" % args['reply_user']
		}

	set_conf('persistent_locked', True)
	blob = conf_load()

	if 'user_records' not in blob:
		blob['user_records'] = {}

	if target_user not in blob['user_records']:
		blob['user_records'][target_user] = []

	blob['user_records'][target_user].append(message)

	conf_save(blob)
	set_conf('persistent_locked', False)

	return {
		'msg': '%s: message saved for %s' % (args['reply_user'], target_user)
	}


@pluginfunction('show-records', 'show current offline records', ptypes_COMMAND)
def command_show_recordlist(argv, **args):
	if 'show-records' != argv[0]:
		return

	log.info('sent offline records list')

	argv1 = None if len(argv) < 2 else argv[1]

	return {
		'msg':
			'%s: offline records%s: %s' % (
				args['reply_user'],
				'' if not argv1 else ' (limited to %s)' % argv1,
				', '.join([
							  '%s (%d)' % (key, len(val)) for key, val in conf_load().get('user_records').items()
							  if not argv1 or argv1.lower() in key.lower()
							  ])
			)
	}


@pluginfunction('dsa-watcher', 'automatically crawls for newly published Debian Security Announces', ptypes_COMMAND,
				ratelimit_class=RATE_NO_SILENCE)
def command_dsa_watcher(argv, **_):
	"""
	TODO: rewrite so that a last_dsa_date is used instead, then all DSAs since then printed and the date set to now()
	"""
	if 'dsa-watcher' != argv[0]:
		return

	if 2 != len(argv):
		msg = 'wrong number of arguments'
		log.warn(msg)
		return {'msg': msg}

	if 'crawl' == argv[1]:
		out = []
		dsa = conf_load().get('plugin_conf', {}).get('last_dsa', 1000)

		url = 'https://security-tracker.debian.org/tracker/DSA-%d-1' % dsa

		try:
			request = urllib.request.Request(url)
			request.add_header('User-Agent', USER_AGENT)
			response = urllib.request.urlopen(request)
			html_text = response.read(BUFSIZ)  # ignore more than BUFSIZ
		except Exception as e:
			err = e
			if '404' not in str(err):
				msg = 'error for %s: %s' % (url, err)
				log.warn(msg)
				out.append(msg)
		else:
			if str != type(html_text):
				html_text = str(html_text)

			result = re.match(r'.*?Description</b></td><td>(.*?)</td>.*?', html_text, re.S | re.M | re.IGNORECASE)

			package = 'error extracting package name'
			if result:
				package = result.groups()[0]

			if conf('persistent_locked'):
				msg = "couldn't get exclusive lock"
				log.warn(msg)
				out.append(msg)
			else:
				set_conf('persistent_locked', True)
				blob = conf_load()

				if 'plugin_conf' not in blob:
					blob['plugin_conf'] = {}

				if 'last_dsa' not in blob['plugin_conf']:
					blob['plugin_conf']['last_dsa'] = 3308  # FIXME: fixed value

				blob['plugin_conf']['last_dsa'] += 1

				conf_save(blob)
				set_conf('persistent_locked', False)

			msg = ('new Debian Security Announce found (%s): %s' % (str(package).replace(' - security update', ''), url))
			out.append(msg)

			log.info('no dsa for %d, trying again...' % dsa)
		# that's good, no error, just 404 -> DSA not released yet

		crawl_at = time.time() + conf('dsa_watcher_interval')
		# register_event(crawl_at, command_dsa_watcher, (['dsa-watcher', 'crawl'],))

		msg = 'next crawl set to %s' % time.strftime('%F.%T', time.localtime(crawl_at))
		out.append(msg)
		return {
			'msg': out,
			'event': {
				'time': crawl_at,
				'command': (command_dsa_watcher, (['dsa-watcher', 'crawl'],))
			}
		}
	else:
		msg = 'wrong argument'
		log.warn(msg)
		return {'msg': msg}


@pluginfunction("provoke_bots", "search for other bots", ptypes_COMMAND)
def provoke_bots(argv, **args):
	if 'provoke_bots' == argv[0]:
		return {
			'msg': 'Searching for other less intelligent lifeforms... skynet? You here?'
		}


@pluginfunction("recognize_bots", "got ya", ptypes_PARSE)
def recognize_bots(**args):
	if 'independent bot and have nothing to do with other artificial intelligence systems' in args['data']:

		blob = conf_load()

		if 'other_bots' not in blob:
			blob['other_bots'] = []
		if args['reply_user'] not in blob['other_bots']:
			blob['other_bots'].append(args['reply_user'])
		conf_save(blob)
		return {
			'event': {
				'time': time.time() + 3,
				'msg': 'Making notes...'
			}
		}


@pluginfunction("set_status", "set bot status", ptypes_COMMAND)
def set_status(argv, **args):
	if 'set_status' != argv[0]:
		return
	if argv[1] == 'mute' and args['reply_user'] == conf('bot_owner'):
		return {
			'presence': {
				'status': 'xa',
				'message': 'I\'m muted now. You can unmute me with "%s: set_status unmute"' % conf("bot_user")
			}
		}
	elif argv[1] == 'unmute' and args['reply_user'] == conf('bot_owner'):
		return {
			'presence': {
				'status': None,
				'message': ''
			}
		}


def else_command(args):
	log.info('sent short info')
	return {
		'msg': args['reply_user'] + ''': I'm a bot (highlight me with 'info' for more information).'''
	}


def register(func_type):
	"""
	Register plugins.

	:param func_type: plugin functions with this type (ptypes) will be loaded
	"""

	functions = [
		f for ignored, f in globals().items() if
		isinstance(f, types.FunctionType) and
		all([
			f.__dict__.get('is_plugin', False),
			getattr(f, 'plugin_type', None) == func_type
		])
		]

	log.info('auto-reg %s: %s' % (func_type, ', '.join(
		f.plugin_name for f in functions
	)))

	for f in functions:
		register_plugin(f, func_type)


def register_plugin(function, func_type):
	try:
		plugins[func_type].append(function)
	except Exception as e:
		log.warn('registering %s failed: %s, %s' % (function, e, traceback.format_exc()))


def register_all():
	register(ptypes_PARSE)
	register(ptypes_COMMAND)


def event_trigger():
	if 0 == len(joblist):
		return True

	now = time.time()

	for (i, (t, callback, args)) in enumerate(joblist):
		if t < now:
			callback(*args)
			del (joblist[i])
	return True
