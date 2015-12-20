#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import time
import sys
from common import VERSION, EVENTLOOP_DELAY
import config

from sleekxmpp import ClientXMPP


class IdleBot(ClientXMPP):
    def __init__(self, jid, password, rooms, nick):
        ClientXMPP.__init__(self, jid, password)

        self.rooms = rooms
        self.nick = nick

        self.add_event_handler('session_start', self.session_start)
        self.add_event_handler('groupchat_message', self.muc_message)
        self.priority = 0
        self.status = None
        self.show = None

        self.logger = logging.getLogger(__name__)

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
        elif msg_obj['mucnick'] in config.runtime_config_store["other_bots"]:
            # not talking to the other bot.
            return False
        else:
            return True

    def hangup(self):
        """
        disconnect and exit
        """
        self.disconnect()
        sys.exit(1)


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
    import plugins

    if active:
        plugins.register_all()
        # if plugins.plugin_enabled_get(plugins.command_dsa_watcher):
            # first result is lost.
            # plugins.command_dsa_watcher(['dsa-watcher', 'crawl'])

    bot.connect()
    bot.register_plugin('xep_0045')
    bot.process()

    while 1:
        try:
            # print("hangup: %s" % got_hangup)
            if not plugins.event_trigger():
                bot.hangup()

            time.sleep(EVENTLOOP_DELAY)
        except KeyboardInterrupt:
            print('')
            exit(130)


if '__main__' == __name__:
    start(IdleBot)
