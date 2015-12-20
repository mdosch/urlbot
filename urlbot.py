#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
The URLBot - ready to strive for desaster in YOUR jabber MUC
"""
import sys

import time

from common import (
    conf_load, conf_save,
    rate_limit_classes,
    RATE_GLOBAL,
    RATE_CHAT,
    RATE_EVENT,
    rate_limit,
    conf_set
)
from idlebot import IdleBot, start
from plugins import (
    plugins as plugin_storage,
    ptypes_COMMAND,
    plugin_enabled_get,
    ptypes_PARSE,
    register_event,
    else_command
)

import config


class UrlBot(IdleBot):
    """
    The URLBot, doing things the IdleBot wouldn't dare to.
    """
    def __init__(self, jid, password, rooms, nick):
        super(UrlBot, self).__init__(jid, password, rooms, nick)

        self.hist_ts = {p: [] for p in rate_limit_classes}
        self.hist_flag = {p: True for p in rate_limit_classes}

        self.add_event_handler('message', self.message)
        self.priority = 100

        for room in self.rooms:
            self.add_event_handler('muc::%s::got_online' % room, self.muc_online)

    def muc_message(self, msg_obj):
        """
        Handle muc messages, return if irrelevant content or die by hangup.
        :param msg_obj:
        :return:
        """
        return super(UrlBot, self).muc_message(msg_obj) and self.handle_msg(msg_obj)

    def message(self, msg_obj):
        """
        General message hook
        :param msg_obj:
        """
        if msg_obj['type'] == 'groupchat':
            return
        else:
            self.logger.info("Got the following PM: %s", str(msg_obj))

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
                    'is' if len(records) == 1 else 'are',
                    len(records),
                    '' if len(records) == 1 else 's',
                    '\n'.join(records)
                ),
                mtype='groupchat'
            )
            self.logger.info('sent %d offline records to room %s',
                             len(records), msg_obj['from'].bare)

            if config.get('persistent_locked'):
                self.logger.warning("couldn't get exclusive lock")
                return False

            config.set('persistent_locked', True)
            blob = conf_load()

            if 'user_records' not in blob:
                blob['user_records'] = {}

            if arg_user_key in blob['user_records']:
                blob['user_records'].pop(arg_user_key)

            conf_save(blob)
            config.set('persistent_locked', False)

    # @rate_limited(10)
    def send_reply(self, message, msg_obj=None):
        """
        Send a reply to a message
        """
        if self.show:
            self.logger.warning("I'm muted! (status: %s)", self.show)
            return

        config.set('request_counter', config.get('request_counter') + 1)

        if str is not type(message):
            message = '\n'.join(message)

        def cached(function, ttl=60):
            cache = {}
            ttl = 60
            now = time.time()

            def wrapper(*args):
                hash_ = hash(args)
                if hash_ in cache and cache[args]['time'] < now - ttl:
                    return cache[hash_]['result']
                else:
                    result = function(*args)
                    cache[hash_] = {}
                    cache[hash_]['time'] = now
                    cache[hash_]['result'] = result
                    return result

            return wrapper

        @cached
        def get_bots_present(room):
            other_bots = conf_load().get("other_bots", ())
            users = self.plugin['xep_0045'].getRoster(room)
            return set(users).intersection(set(other_bots))

        def _prevent_panic(message, room):
            """check other bots, add nospoiler with urls"""
            if 'http' in message:
                other_bots = conf_load().get("other_bots", ())
                users = self.plugin['xep_0045'].getRoster(room)
                if set(users).intersection(set(other_bots)):
                    message = '(nospoiler) %s' % message
            return message

        if config.get('debug_mode'):
            print(message)
        else:
            if msg_obj:
                # TODO: bot modes off/on/auto... this should be active for "on".
                # message = _prevent_panic(message, msg_obj['from'].bare)
                if get_bots_present(msg_obj['from'].bare):
                    return
                self.send_message(
                    mto=msg_obj['from'].bare,
                    mbody=message,
                    mtype='groupchat'
                )
            else:
                for room in self.rooms:
                    # message = _prevent_panic(message, room)
                    if get_bots_present(room):
                        continue
                    self.send_message(
                        mto=room,
                        mbody=message,
                        mtype='groupchat'
                    )

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

        self.data_parse_commands(msg_obj)
        self.data_parse_other(msg_obj)

    def data_parse_commands(self, msg_obj):
        """
        react to a message with the bots nick
        :param msg_obj: dictionary with incoming message parameters

        :returns: nothing
        """
        data = msg_obj['body']
        words = data.split()

        if len(words) < 2:  # need at least two words
            return None

        # don't reply if beginning of the text matches bot_nickname
        if not data.startswith(config.get('bot_nickname')):
            return None

        if 'hangup' in data:
            self.logger.warning('received hangup: ' + data)
            self.hangup()
            sys.exit(1)

        reply_user = msg_obj['mucnick']

        # TODO: check how several commands/plugins
        # in a single message behave (also with rate limiting)
        reacted = False
        for plugin in plugin_storage[ptypes_COMMAND]:

            if not plugin_enabled_get(plugin):
                continue

            ret = plugin(
                data=data,
                cmd_list=[pl.plugin_name for pl in plugin_storage[ptypes_COMMAND]],
                parser_list=[pl.plugin_name for pl in plugin_storage[ptypes_PARSE]],
                reply_user=reply_user,
                msg_obj=msg_obj,
                argv=words[1:]
            )

            if ret:
                self._run_action(ret, plugin, msg_obj)
                reacted = True

        if not reacted and rate_limit(RATE_GLOBAL):
            ret = else_command({'reply_user': reply_user})
            if ret:
                if 'msg' in ret:
                    self.send_reply(ret['msg'], msg_obj)

    def data_parse_other(self, msg_obj):
        """
        react to any message

        :param msg_obj: incoming message parameters
        :return:
        """
        data = msg_obj['body']
        reply_user = msg_obj['mucnick']

        for plugin in plugin_storage[ptypes_PARSE]:
            if not plugin_enabled_get(plugin):
                continue

            ret = plugin(reply_user=reply_user, data=data)

            if ret:
                self._run_action(ret, plugin, msg_obj)

    def _run_action(self, action, plugin, msg_obj):
        """
        Execute the plugin's execution plan
        :param action: dict with event and/or msg
        :param plugin: plugin obj
        :param msg_obj: xmpp message obj
        """
        if 'event' in action:
            event = action["event"]
            if 'msg' in event:
                register_event(event["time"], self.send_reply, [event['msg'], msg_obj])
            elif 'command' in event:
                command = event["command"]
                if rate_limit(RATE_EVENT):
                    register_event(event["time"], command[0], command[1])

        if 'msg' in action and rate_limit(RATE_CHAT | plugin.ratelimit_class):
            self.send_reply(action['msg'], msg_obj)

        if 'presence' in action:
            presence = action['presence']
            conf_set('presence', presence)

            self.status = presence.get('msg')
            self.show = presence.get('status')

            self.send_presence(pstatus=self.status, pshow=self.show)
        # self.reconnect(wait=True)


if __name__ == '__main__':
    start(UrlBot, True)
