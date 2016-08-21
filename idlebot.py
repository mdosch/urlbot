#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import time
import sys
import config
import events
from common import VERSION

from sleekxmpp import ClientXMPP


class IdleBot(ClientXMPP):
    def __init__(self, jid, password, rooms, nick):
        ClientXMPP.__init__(self, jid, password)

        self.rooms = rooms
        self.nick = nick

        self.add_event_handler('session_start', self.session_start)
        self.add_event_handler('groupchat_message', self.muc_message)
        self.add_event_handler('disconnected', self.disconnected)
        self.add_event_handler('presence_error', self.disconnected)
        self.priority = 0
        self.status = None
        self.show = None

        self.logger = logging.getLogger(__name__)
        for room in self.rooms:
            self.add_event_handler('muc::%s::got_offline' % room, self.muc_offline)

    def disconnected(self, _):
        self.disconnect(wait=True)

    def session_start(self, _):
        self.get_roster()
        self.send_presence(ppriority=self.priority, pstatus=self.status, pshow=self.show)

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
        if msg_obj['mucnick'] == self.nick or 'groupchat' != msg_obj['type']:
            return False
        elif msg_obj['body'].startswith(config.conf_get('bot_nickname')) and 'hangup' in msg_obj['body']:
            self.logger.warn("got 'hangup' from '%s': '%s'" % (
                msg_obj['mucnick'], msg_obj['body']
            ))
            self.hangup()
            return False
        # elif msg_obj['mucnick'] in config.runtimeconf_get("other_bots", ()):
        #     self.logger.debug("not talking to the other bot named {}".format( msg_obj['mucnick']))
        #     return False
        else:
            return True

    def muc_offline(self, msg_obj):
        if 'muc' in msg_obj.values:
            room = msg_obj.values['muc']['room']
            user = msg_obj.values['muc']['nick']
            if user == config.conf_get('bot_nickname'):
                self.logger.warn("Left my room, rejoin")
                self.plugin['xep_0045'].joinMUC(
                    room,
                    self.nick,
                    wait=True
                )

    def hangup(self):
        """
        disconnect and exit
        """
        self.disconnect(wait=True)


def start(botclass, active=False):
    logging.basicConfig(
        level=config.conf_get('loglevel'),
        format=sys.argv[0] + ' %(asctime)s %(levelname).1s %(funcName)-15s %(message)s'
    )
    logger = logging.getLogger(__name__)
    logger.info(VERSION)

    jid = config.conf_get('jid')
    if '/' not in jid:
        jid = '%s/%s' % (jid, botclass.__name__)
    bot = botclass(
        jid=jid,
        password=config.conf_get('password'),
        rooms=config.conf_get('rooms'),
        nick=config.conf_get('bot_nickname')
    )

    bot.connect()
    bot.register_plugin('xep_0045')
    bot.process()

    config.runtimeconf_set('start_time', -time.time())

    if active:
        import plugins

    events.event_loop.start()


if '__main__' == __name__:
    start(IdleBot)
