#!/usr/bin/python3
# -*- coding: utf-8 -*-

from common import *

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

import logging
from sleekxmpp import ClientXMPP

got_hangup = False

class bot(ClientXMPP):
	def __init__(self, jid, password, rooms, nick):
		ClientXMPP.__init__(self, jid, password)

		self.rooms = rooms
		self.nick = nick

		self.add_event_handler('session_start', self.session_start)
		self.add_event_handler('groupchat_message', self.muc_message)

	def session_start(self, event):
		self.get_roster()
		self.send_presence()

		for room in self.rooms:
			logger('info', 'joining %s' % room)
			self.plugin['xep_0045'].joinMUC(
				room,
				self.nick,
				wait=True
			)

	def muc_message(self, msg_obj):
		global got_hangup

		# don't talk to yourself
		if msg_obj['mucnick'] == self.nick:
			return

		if 'groupchat' != msg_obj['type']:
			return

		if msg_obj['body'].startswith(conf('bot_user')) and 'hangup' in msg_obj['body']:
			logger('warn', "got 'hangup' from '%s': '%s'" % (
				msg_obj['mucnick'], msg_obj['body']
			))
			got_hangup = True
			sys.exit(1)


if '__main__' == __name__:
	print(sys.argv[0] + ' ' + VERSION)

	logging.basicConfig(
		level=logging.INFO,
		format='%(levelname)-8s %(message)s'
	)

	xmpp = bot(
		jid=conf('jid'),
		password=conf('password'),
		rooms=conf('rooms'),
		nick=conf('bot_user')
	)

	xmpp.connect()
	xmpp.register_plugin('xep_0045')
	xmpp.process()

	while 1:
		try:
			# do nothing here, just idle
			if got_hangup:
				xmpp.disconnect()
				sys.exit(1)

			time.sleep(delay)
		except KeyboardInterrupt:
			print('')
			exit(130)
