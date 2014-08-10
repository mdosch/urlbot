#!/usr/bin/python

import xmpp
from local_config import conf

def message_handler(connect_object, message_node):
	print 'connect_object:'
	print connect_object
	print 'message_node:'
	print message_node
	return None

jid = xmpp.protocol.JID(conf('jid'))

client = xmpp.Client(jid.getDomain()) #, debug=[])
client.connect()
client.auth(jid.getNode(), conf('password'))
client.RegisterHandler('message', message_handler) 

client.send(xmpp.Presence(to=(conf('room') + '/' + conf('nick'))))

if 0:
	msg = xmpp.protocol.Message(body='''wee, I'm a native bot.''')
	msg.setTo(conf('room'))
	msg.setType('groupchat')
	client.send(msg)

import time
time.sleep(10)

client.disconnect()
