#!/usr/bin/python

import xmpp
from local_config import conf

import time
t = -time.time()

def message_handler(connect_object, message_node):
	# hopefully the backlog is processed in this time
	# FIXME: find a better way.
	if (t + time.time() < 1):
		return None

	msg_from = message_node.getFrom().getResource()
	msg_body = message_node.getBody()

	if not type(msg_body) in [str, unicode]:
		return None

	if msg_body.startswith(conf('nick')):
		connect_object.send(
			xmpp.protocol.Message(
				to=conf('room'),
				body='hello %s!' % msg_from,
				typ='groupchat'
			)
		)

	try:
		print '%20s: %s' %(msg_from, msg_body)
	except Exception as e:
		print e
	
	return None

jid = xmpp.protocol.JID(conf('jid'))

client = xmpp.Client(jid.getDomain(), debug=[])
client.connect()
client.auth(jid.getNode(), conf('password'))
client.RegisterHandler('message', message_handler) 

client.send(xmpp.Presence(to=(conf('room') + '/' + conf('nick'))))

while (t + time.time()) < 30:
	client.Process(1)

client.disconnect()
