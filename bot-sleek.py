#!/usr/bin/python3

from sleekxmpp import ClientXMPP
from local_config import conf

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
	xmpp = bot(
		jid=conf('jid'),
		password=conf('password'),
		room=conf('room'),
		nick=conf('bot_user')
	)

	xmpp.connect()
	xmpp.register_plugin('xep_0045')
	xmpp.process()
