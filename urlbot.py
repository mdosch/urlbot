#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The URLBot - ready to strive for desaster in YOUR jabber MUC
"""
import re
import shlex
import sys
import time
from collections import deque

from lxml import etree

import requests

from plugin_system import plugin_storage, ptypes, plugin_enabled_get
from rate_limit import rate_limit_classes, RATE_GLOBAL, RATE_CHAT, RATE_EVENT, rate_limit

import events

from common import get_nick_from_object, else_command

from config import runtimeconf_set
from idlebot import IdleBot, start

import config


class UrlBot(IdleBot):
    """
    The URLBot, doing things the IdleBot wouldn't dare to.
    """

    def __init__(self, jid, password, rooms, nick):
        super(UrlBot, self).__init__(jid, password, rooms, nick)

        self.hist_ts = {p: [] for p in rate_limit_classes}
        self.hist_flag = {p: True for p in rate_limit_classes}
        self.message_stack = {str(room): deque(maxlen=5) for room in self.rooms}

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
            self.logger.info("Got the following MUC message: %s", str(msg_obj))
            return
        else:
            self.logger.info("Got the following PM: %s", str(msg_obj))
            self.handle_msg(msg_obj)

    def muc_online(self, msg_obj):
        """
        Hook for muc event "user joins"
        :param msg_obj:
        """
        self.handle_muc_online(msg_obj)

    # @rate_limited(10)
    def send_reply(self, message, msg_obj=None):
        """
        Send a reply to a message
        """
        if self.show:
            self.logger.warning("I'm muted! (status: %s)", self.show)
            return

        request_counter = int(config.runtimeconf_get('request_counter'))
        config.runtimeconf_set('request_counter', request_counter + 1)

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
            other_bots = config.runtimeconf_get("other_bots")
            if not other_bots:
                return False
            users = self.plugin['xep_0045'].getRoster(room)
            return set(users).intersection(set(other_bots))

        def _prevent_panic(message, room):
            """check other bots, add nospoiler with urls"""
            if 'http' in message and get_bots_present(room):
                message = '(nospoiler) %s' % message
            return message

        if config.conf_get('debug_mode'):
            print(message)
        else:
            if msg_obj:
                # TODO: bot modes off/on/auto... this should be active for "on".
                # message = _prevent_panic(message, msg_obj['from'].bare)
                # if get_bots_present(msg_obj['from'].bare):
                #     return
                if msg_obj['type'] == 'groupchat':
                    if msg_obj['mucnick'] in config.runtimeconf_get("other_bots", ()):
                        msg_obj['type'] = 'chat'
                        self.send_reply("You're flagged as bot, please write {}: remove-from-botlist "
                                        "{} if you're not a bot.".format(
                                            config.conf_get('bot_nickname'),
                                            get_nick_from_object(msg_obj)
                                        ), msg_obj)
                        self.logger.debug("not talking to the other bot named {}".format(get_nick_from_object(msg_obj)))
                        return False
                    self.send_message(
                        mto=msg_obj['from'].bare,
                        mbody=message,
                        mtype='groupchat'
                    )
                elif msg_obj['type'] == 'chat':
                    self.send_message(
                        mto=msg_obj['from'],
                        mbody=message,
                        mtype='chat'
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

        if msg_obj['mucnick'] in config.runtime_config_store['spammers']:
            self.logger.info("ignoring spammer {}".format(msg_obj['mucnick']))
            return

        try:
            reacted_on_command = self.data_parse_commands(msg_obj)
            reacted_on_parse = self.data_parse_other(msg_obj)

            # disabled for now
            # self.data_parse_forum_thread(msg_obj)
            # self.data_parse_forum_post(msg_obj)

            if (msg_obj['body'].startswith(config.conf_get('bot_nickname')) and not any(
                    [reacted_on_command, reacted_on_parse]) and rate_limit(RATE_GLOBAL)):
                ret = else_command({'reply_user': get_nick_from_object(msg_obj)})
                if ret:
                    if 'msg' in ret:
                        self.send_reply(ret['msg'], msg_obj)
        except Exception as e:
            self.logger.exception(e)
        finally:
            if msg_obj['from'].bare in self.rooms:
                self.message_stack[msg_obj['from'].bare].append(msg_obj)

    def handle_muc_online(self, msg_obj):
        """
        react to users that got online

        :param msg_obj: incoming message parameters
        :return:
        """

        # don't react to yourself
        if msg_obj['muc']['nick'] == self.nick:
            return

        reply_user = get_nick_from_object(msg_obj)

        for plugin in plugin_storage[ptypes.MUC_ONLINE]:
            if not plugin_enabled_get(plugin):
                continue

            ret = plugin(reply_user=reply_user)
            if ret:
                self._run_action(ret, plugin, None)

    def data_parse_commands(self, msg_obj):
        """
        react to a message with the bots nick
        :param msg_obj: dictionary with incoming message parameters

        :returns: nothing
        """
        data = msg_obj['body']
        try:
            words = shlex.split(data)
        except ValueError:
            words = data.split()

        # prepend the bot nick so we have the same syntax as in muc
        if msg_obj['type'] == 'chat' and words and self.nick not in words[0]:
            words = [self.nick] + words

        if len(words) < 2:  # need at least two words
            return None

        # only reply if beginning of the text matches bot_nickname or it's a private session.
        if msg_obj['type'] == 'groupchat' and not data.startswith(config.conf_get('bot_nickname')):
            return None

        if 'hangup' in data:
            self.logger.warning('received hangup: ' + data)
            self.hangup()
            sys.exit(1)

        reply_user = get_nick_from_object(msg_obj)

        # TODO: check how several commands/plugins
        # in a single message behave (also with rate limiting)
        reacted = False
        for plugin in filter(lambda p: p.plugin_name == words[1], plugin_storage[ptypes.COMMAND]):

            if not plugin_enabled_get(plugin):
                continue

            ret = plugin(
                data=data,
                cmd_list=[pl.plugin_name for pl in plugin_storage[ptypes.COMMAND]],
                parser_list=[pl.plugin_name for pl in plugin_storage[ptypes.PARSE]],
                reply_user=reply_user,
                msg_obj=msg_obj,
                argv=words[2:] if len(words) > 1 else [],
                stack=self.message_stack.get(msg_obj['from'].bare, [])
            )

            if ret:
                self._run_action(ret, plugin, msg_obj)
                reacted = True
        return reacted

    def data_parse_other(self, msg_obj):
        """
        react to any message

        :param msg_obj: incoming message parameters
        :return:
        """
        data = msg_obj['body']
        reply_user = get_nick_from_object(msg_obj)
        reacted = False

        for plugin in plugin_storage[ptypes.PARSE]:
            if not plugin_enabled_get(plugin):
                continue

            ret = plugin(reply_user=reply_user, data=data)

            if ret:
                self._run_action(ret, plugin, msg_obj)
                reacted = True
        return reacted

    def data_parse_forum_thread(self, msg_obj):
        return

    def data_parse_forum_post(self, msg_obj):
        links = re.findall(r'(https?://(?:www\.)?debianforum\.de/forum/[^\s>]+)', msg_obj['body'])
        for link in links:
            html = requests.get(link).text
            tree = etree.XML(html, etree.HTMLParser())
            postid = re.findall('p=?([0-9]{4,})', link)
            if not postid:
                return
            postid = 'p{}'.format(postid[0])
            post_path = '//div[@id="{}"]'.format(postid)
            postelement = tree.xpath(post_path)
            if postelement:
                postelement = postelement[0]
            else:
                self.logger.warn("No post with id {} found!".format(postid))
                return
            # excludes any [code] and [quote] elements by only looking at direct text child nodes
            username_xpath = '//dl[@class="postprofile"]//*[contains(@href, "memberlist")]/text()'
            user = tree.xpath('{}{}'.format(post_path, username_xpath))[0]
            posttext = postelement.xpath('{}//div[@class="content"]/text()'.format(post_path))
            print(user, '\n'.join(posttext))
            summary_action = {'msg': '{} posted {} words'.format(user, len('\n'.join(posttext).split()))}
            self._run_action(summary_action, plugin=plugin_storage[ptypes.COMMAND][0], msg_obj=msg_obj)
        return

    def _run_action(self, action, plugin, msg_obj):
        """
        Execute the plugin's execution plan
        :param action: dict with event and/or msg
        :param plugin: plugin obj
        :param msg_obj: xmpp message obj
        """
        if 'event' in action and action["event"] is not None:
            event = action["event"]
            if 'msg' in event:
                events.register_event(event["time"], self.send_reply, [event['msg'], msg_obj])
            elif 'command' in event:
                command = event["command"]
                if rate_limit(RATE_EVENT):
                    # register_event(t=event["time"], callback=command[0], args=command[1])
                    # kind of ugly..
                    events.register_active_event(
                        t=event['time'],
                        callback=command[0],
                        args=command[1],
                        action_runner=self._run_action,
                        plugin=plugin,
                        msg_obj=msg_obj
                    )

        if 'msg' in action and rate_limit(RATE_CHAT | plugin.ratelimit_class):
            self.send_reply(action['msg'], msg_obj)

        if 'priv_msg' in action and rate_limit(RATE_CHAT | plugin.ratelimit_class):
            msg_obj['type'] = 'chat'
            self.send_reply(action['priv_msg'], msg_obj)

        if 'presence' in action:
            presence = action['presence']
            runtimeconf_set('presence', presence)

            self.status = presence.get('msg')
            self.show = presence.get('status')

            self.send_presence(pstatus=self.status, pshow=self.show)
            # self.reconnect(wait=True)


if __name__ == '__main__':
    start(UrlBot, True)
