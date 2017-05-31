# -*- coding: utf-8 -*-
import random

from common import giphy
from plugin_system import pluginfunction, ptypes
from rate_limit import RATE_FUN, RATE_GLOBAL


def give_item(user, item_name, search_word=None):
    if not search_word:
        search_word = item_name
    return {'msg': '{} for {}: {}'.format(item_name, user, giphy(search_word, 'dc6zaTOxFJmzC'))}


def cake_excuse(user):
    return {
        'msg': '{}: {}'.format(user, random.choice(cakes))
    }


@pluginfunction('cake', 'displays a cake ASCII art', ptypes.COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_cake(argv, **args):
    if {'please', 'bitte'}.intersection(set(argv)):
        return give_item(args['reply_user'], 'cake')
    else:
        return cake_excuse(args['reply_user'])


@pluginfunction('keks', 'keks!', ptypes.COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_cookie(argv, **args):
    if {'please', 'bitte'}.intersection(set(argv)):
        return give_item(args['reply_user'], 'keks', 'cookie')
    else:
        return cake_excuse(args['reply_user'])


@pluginfunction('schnitzel', 'schnitzel!', ptypes.COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_schnitzel(argv, **args):
    if {'please', 'bitte'}.intersection(set(argv)):
        return give_item(args['reply_user'], 'schnitzel')
    else:
        return cake_excuse(args['reply_user'])


@pluginfunction('kaffee', 'kaffee!', ptypes.COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_coffee(argv, **args):
    if {'please', 'bitte'}.intersection(set(argv)):
        return give_item(args['reply_user'], 'kaffee', 'coffee')
    else:
        return cake_excuse(args['reply_user'])


cakes = [
    "No cake for you!",
    ("The Enrichment Center is required to remind you "
     "that you will be baked, and then there will be cake."),
    "The cake is a lie!",
    ("This is your fault. I'm going to kill you. "
     "And all the cake is gone. You don't even care, do you?"),
    "Quit now and cake will be served immediately.",
    ("Enrichment Center regulations require both hands to be "
     "empty before any cake..."),
    ("Uh oh. Somebody cut the cake. I told them to wait for "
     "you, but they did it anyway. There is still some left, "
     "though, if you hurry back."),
    "I'm going to kill you, and all the cake is gone.",
    "Who's gonna make the cake when I'm gone? You?"
]
