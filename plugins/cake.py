# -*- coding: utf-8 -*-
import random

from plugin_system import pluginfunction, ptypes
from rate_limit import RATE_FUN, RATE_GLOBAL

@pluginfunction('cake', 'displays a cake ASCII art', ptypes.COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_cake(argv, **args):
    if {'please', 'bitte'}.intersection(set(argv)):
        return {
            'msg': 'cake for {}: {}'.format(args['reply_user'], giphy('cake', 'dc6zaTOxFJmzC'))
        }

    return {
        'msg': args['reply_user'] + ': %s' % random.choice(cakes)
    }


@pluginfunction('keks', 'keks!', ptypes.COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_cookie(argv, **args):
    if {'please', 'bitte'}.intersection(set(argv)):
        return {
            'msg': 'keks für {}: {}'.format(args['reply_user'], giphy('cookie', 'dc6zaTOxFJmzC'))
        }

    return {
        'msg': args['reply_user'] + ': %s' % random.choice(cakes)
    }


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

