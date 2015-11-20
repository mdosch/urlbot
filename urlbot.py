#!/usr/bin/python3
# -*- coding: utf-8 -*-

import random
import re
import sys
import time

from common import conf_load, conf_save, \
	extract_title, RATE_GLOBAL, RATE_CHAT
from idlebot import IdleBot, start
from plugins import (
	ptypes as plugin_ptypes,
	plugins as plugin_storage,
	ptypes_COMMAND,
	plugin_enabled_get,
	ptypes_PARSE,
	register_event,
	else_command
)

try:
	from local_config import conf, set_conf
except ImportError:
	sys.stderr.write('''
%s: E: local_config.py isn't tracked because of included secrets and
%s     site specific configurations. Rename local_config.py.skel and
%s     adjust to your needs.
'''[1:] % (
		sys.argv[0],
		' ' * len(sys.argv[0]),
		' ' * len(sys.argv[0])
	))
	sys.exit(1)


class UrlBot(IdleBot):
	def __init__(self, jid, password, rooms, nick):
		super(UrlBot, self).__init__(jid, password, rooms, nick)

		self.hist_ts = {p: [] for p in plugin_ptypes}
		self.hist_flag = {p: True for p in plugin_ptypes}

		self.add_event_handler('message', self.message)

		for r in self.rooms:
			self.add_event_handler('muc::%s::got_online' % r, self.muc_online)

	def muc_message(self, msg_obj):
		super(UrlBot, self).muc_message(msg_obj)
		return self.handle_msg(msg_obj)

	def message(self, msg_obj):
		if 'groupchat' == msg_obj['type']:
			return
		else:
			self.logger.info("Got the following PM: %s" % str(msg_obj))

	def muc_online(self, msg_obj):
		"""
		Hook for muc event "user joins"
		"""
		# don't react to yourself
		if msg_obj['muc']['nick'] == self.nick:
			return

		# TODO: move this to a undirected plugin, maybe new plugin type
		arg_user = msg_obj['muc']['nick']
		arg_user_key = arg_user.lower()
		blob_userrecords = conf_load().get('user_records', {})

		if arg_user_key in blob_userrecords:
			records = blob_userrecords[arg_user_key]

			if not records:
				return

			self.send_message(
				mto=msg_obj['from'].bare,
				mbody='%s, there %s %d message%s for you:\n%s' % (
					arg_user,
					'is' if 1 == len(records) else 'are',
					len(records),
					'' if 1 == len(records) else 's',
					'\n'.join(records)
				),
				mtype='groupchat'
			)
			self.logger.info('sent %d offline records to room %s' % (
				len(records), msg_obj['from'].bare
			))

			if conf('persistent_locked'):
				self.logger.warn("couldn't get exclusive lock")
				return False

			set_conf('persistent_locked', True)
			blob = conf_load()

			if 'user_records' not in blob:
				blob['user_records'] = {}

			if arg_user_key in blob['user_records']:
				blob['user_records'].pop(arg_user_key)

			conf_save(blob)
			set_conf('persistent_locked', False)

	def send_reply(self, message, msg_obj=None):
		"""
		Send a reply to a message
		"""
		set_conf('request_counter', conf('request_counter') + 1)

		if str is not type(message):
			message = '\n'.join(message)

		if conf('debug_mode'):
			print(message)
		else:
			if msg_obj:
				self.send_message(
					mto=msg_obj['from'].bare,
					mbody=message,
					mtype='groupchat'
				)
			else:  # unset msg_obj == broadcast
				for room in self.rooms:
					self.send_message(
						mto=room,
						mbody=message,
						mtype='groupchat'
					)

	# TODO: plugin?
	def extract_url(self, data, msg_obj):
		result = re.findall(r'(https?://[^\s>]+)', data)
		if not result:
			return

		ret = None
		out = []
		for url in result:
			self.push_ratelimit()
			if self.check_ratelimit(msg_obj):
				return False

			flag = False
			for b in conf('url_blacklist'):
				if re.match(b, url):
					flag = True
					self.logger.info('url blacklist match for ' + url)
					break

			if flag:
				# an URL has matched the blacklist, continue to the next URL
				continue

			# urllib.request is broken:
			# >>> '.'.encode('idna')
			# ....
			# UnicodeError: label empty or too long
			# >>> '.a.'.encode('idna')
			# ....
			# UnicodeError: label empty or too long
			# >>> 'a.a.'.encode('idna')
			# b'a.a.'

			try:
				(status, title) = extract_title(url)
			except UnicodeError as e:
				(status, title) = (4, str(e))

			if 0 == status:
				title = title.strip()
				message = 'Title: %s' % title
			elif 1 == status:
				if conf('image_preview'):
					# of course it's fake, but it looks interesting at least
					char = r""",._-+=\|/*`~"'"""
					message = 'No text but %s, 1-bit ASCII art preview: [%c]' % (
						title, random.choice(char)
					)
				else:
					self.logger.info('no message sent for non-text %s (%s)' % (url, title))
					continue
			elif 2 == status:
				message = '(No title)'
			elif 3 == status:
				message = title
			elif 4 == status:
				message = 'Bug triggered (%s), invalid URL/domain part: %s' % (title, url)
				self.logger.warn(message)
			else:
				message = 'some error occurred when fetching %s' % url

			message = message.replace('\n', '\\n')

			self.logger.info('adding to out buf: ' + message)
			out.append(message)
			ret = True

		if ret:
			self.send_reply(out, msg_obj)
		return ret

	def handle_msg(self, msg_obj):
		"""
		called for incoming messages
		:param msg_obj:
		:returns nothing
		"""
		content = msg_obj['body']

		if 'has set the subject to:' in content:
			return

		if sys.argv[0] in content:
			self.logger.info('silenced, this is my own log')
			return

		if 'nospoiler' in content:
			self.logger.info('no spoiler for: ' + content)
			return

		arg_user = msg_obj['mucnick']
		blob_userpref = conf_load().get('user_pref', [])
		nospoiler = False

		if arg_user in blob_userpref:
			if 'spoiler' in blob_userpref[arg_user]:
				if not blob_userpref[arg_user]['spoiler']:
					self.logger.info('nospoiler from conf')
					nospoiler = True

		if not nospoiler:
			# TODO: why not make this a plugin?
			self.extract_url(content, msg_obj)

		self.data_parse_commands(msg_obj)
		self.data_parse_other(msg_obj)

	def push_ratelimit(self, ratelimit_class=RATE_GLOBAL):  # FIXME: separate counters
		local_history = self.hist_ts[ratelimit_class]
		local_history.append(time.time())

		if conf('hist_max_count') < len(local_history):
			local_history.pop(0)
		self.hist_ts[ratelimit_class] = local_history

	def check_ratelimit(self, ratelimit_class=RATE_GLOBAL):  # FIXME: separate counters

		local_history = self.hist_ts[ratelimit_class]

		if conf('hist_max_count') < len(local_history):
			first = local_history.pop(0)
			self.hist_ts[ratelimit_class] = local_history

			if (time.time() - first) < conf('hist_max_time'):
				if self.hist_flag[ratelimit_class]:
					self.hist_flag[ratelimit_class] = False
					# FIXME: this is very likely broken now
					self.send_reply('(rate limited to %d messages in %d seconds, try again at %s)' % (
							conf('hist_max_count'),
							conf('hist_max_time'),
							time.strftime('%T %Z', time.localtime(local_history[0] + conf('hist_max_time')))
						)
					)

				self.logger.warn('rate limiting exceeded: ' + local_history)
				return True

		self.hist_flag[ratelimit_class] = True
		return False

	def data_parse_commands(self, msg_obj):
		"""
		react to a message with the bots nick
		:param msg_obj: dictionary with incoming message parameters

		:returns: nothing
		"""
		global got_hangup

		data = msg_obj['body']
		words = data.split()

		if 2 > len(words):  # need at least two words
			return None

		# don't reply if beginning of the text matches bot_user
		if not data.startswith(conf('bot_user')):
			return None

		if 'hangup' in data:
			self.logger.warn('received hangup: ' + data)
			got_hangup = True
			sys.exit(1)

		reply_user = msg_obj['mucnick']

		# TODO: check how several commands/plugins in a single message behave (also with rate limiting)
		for p in plugin_storage[ptypes_COMMAND]:
			if self.check_ratelimit(p.ratelimit_class):
				continue

			if not plugin_enabled_get(p):
				continue

			ret = p(
				data=data,
				cmd_list=[pl.plugin_name for pl in plugin_storage[ptypes_COMMAND]],
				parser_list=[pl.plugin_name for pl in plugin_storage[ptypes_PARSE]],
				reply_user=reply_user,
				msg_obj=msg_obj,
				argv=words[1:]
			)

			if ret:
				if 'event' in ret:
					event = ret["event"]
					if 'msg' in event:
						register_event(event["time"], self.send_reply, event['msg'])
					elif 'command' in event:
						command = event["command"]
						register_event(event["time"], command[0], command[1])
				if 'msg' in list(ret.keys()):
					self.push_ratelimit(RATE_CHAT)
					if self.check_ratelimit(RATE_CHAT):
						return False

					self.send_reply(ret['msg'], msg_obj)

				return None

		ret = else_command({'reply_user': reply_user})
		if ret:
			if self.check_ratelimit(RATE_GLOBAL):
				return False

			if 'msg' in list(ret.keys()):
				self.send_reply(ret['msg'], msg_obj)

	def data_parse_other(self, msg_obj):
		"""
		react to any message

		:param msg_obj: incoming message parameters
		:return:
		"""
		data = msg_obj['body']
		reply_user = msg_obj['mucnick']

		for p in plugin_storage[ptypes_PARSE]:
			if self.check_ratelimit(p.ratelimit_class):
				continue

			if not plugin_enabled_get(p):
				continue

			ret = p(reply_user=reply_user, data=data)

			if ret:
				if 'msg' in list(ret.keys()):
					self.push_ratelimit(RATE_CHAT)
					self.send_reply(ret['msg'], msg_obj)


if '__main__' == __name__:
	start(UrlBot, True)

