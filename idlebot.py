#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import time

import sys

from common import VERSION, EVENTLOOP_DELAY

try:
	from local_config import conf, set_conf
except ImportError:
	sys.stderr.write('''
%s: E: local_config.py isn't tracked because of included secrets and
%s     site specific configurations. Rename local_config.py.skel and
%s     adjust to you needs.
'''[1:] % (
		sys.argv[0],
		' ' * len(sys.argv[0]),
		' ' * len(sys.argv[0])
	)
	)
	sys.exit(1)

from sleekxmpp import ClientXMPP

got_hangup = False


class IdleBot(ClientXMPP):
	def __init__(self, jid, password, rooms, nick):
		ClientXMPP.__init__(self, jid, password)

		self.rooms = rooms
		self.nick = nick

		self.add_event_handler('session_start', self.session_start)
		self.add_event_handler('groupchat_message', self.muc_message)

		self.logger = logging.getLogger(__name__)

	def session_start(self, _):
		self.get_roster()
		self.send_presence()

		for room in self.rooms:
			self.logger.info('%s: joining' % room)
			ret = self.plugin['xep_0045'].joinMUC(
				room,
				self.nick,
				wait=True
			)
			self.logger.info('%s: joined with code %s' % (room, ret))

	def muc_message(self, msg_obj):
		"""
		Handle muc messages, return if irrelevant content or die by hangup.
		:param msg_obj:
		:return:
		"""
		# don't talk to yourself
		if msg_obj['mucnick'] == self.nick:
			return

		if 'groupchat' != msg_obj['type']:
			return

		if msg_obj['body'].startswith(conf('bot_user')) and 'hangup' in msg_obj['body']:
			self.logger.warn("got 'hangup' from '%s': '%s'" % (
				msg_obj['mucnick'], msg_obj['body']
			))
			global got_hangup
			got_hangup = True
			return


def start(botclass, active=False):
	logging.basicConfig(
		level=logging.INFO,
		format=sys.argv[0] + ' %(asctime)s %(levelname).1s %(funcName)-15s %(message)s'
	)
	logger = logging.getLogger(__name__)
	logger.info(VERSION)

	bot = botclass(
		jid=conf('jid'),
		password=conf('password'),
		rooms=conf('rooms'),
		nick=conf('bot_user')
	)
	import plugins

	if active:
		plugins.register_all()
		if plugins.plugin_enabled_get(plugins.command_dsa_watcher):
			# first result is lost.
			plugins.command_dsa_watcher(['dsa-watcher', 'crawl'])

	bot.connect()
	bot.register_plugin('xep_0045')
	bot.process()
	global got_hangup

	while 1:
		try:
			if got_hangup or not plugins.event_trigger():
				bot.disconnect()
				sys.exit(1)

			time.sleep(EVENTLOOP_DELAY)
		except KeyboardInterrupt:
			print('')
			exit(130)


if '__main__' == __name__:
	start(IdleBot)
