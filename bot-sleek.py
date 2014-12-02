#!/usr/bin/python3

import logging

from sleekxmpp import ClientXMPP

try:
	from local_config import conf
except ImportError:
	import sys
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

	sys.exit(-1)

import time
t = -time.time()

class bot(ClientXMPP):
	def __init__(self, jid, password, room, nick):
		ClientXMPP.__init__(self, jid, password)

		self.room = room
		self.nick = nick

		self.add_event_handler('session_start', self.session_start)
		self.add_event_handler('message', self.message)

	def session_start(self, event):
		self.get_roster()
		self.send_presence()

		self.plugin['xep_0045'].joinMUC(
			self.room,
			self.nick,
			wait=True
		)

	def message(self, event):
		print((t + time.time()) + ': ' + str(msg))

#		if msg['type'] in ['chat', 'normal']:
#			msg.reply('pong[%s]' % msg).send()


if '__main__' == __name__:
	logging.basicConfig(
		level=logging.DEBUG,
		format='%(levelname)-8s %(message)s'
	)

	xmpp = bot(
		jid=conf('jid'),
		password=conf('password'),
		room=conf('room'),
		nick=conf('bot_user')
	)

	xmpp.connect()
	xmpp.register_plugin('xep_0045')
	xmpp.process()
