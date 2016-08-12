# -*- coding: utf-8 -*-
import logging
import re

from plugin_system import pluginfunction, ptypes
from rate_limit import RATE_FUN, RATE_GLOBAL

log = logging.getLogger(__name__)

# copy from https://de.wikipedia.org/wiki/Morsezeichen
raw_wiki_copy = """
A· −
B− · · ·
C− · − ·
D− · ·
E·
F· · − ·
G− − ·
H· · · ·
I· ·
J· − − −
K− · −
L· − · ·
M− −
N− ·
O− − −
P· − − ·
Q− − · −
R· − ·
S· · ·
T−
U· · −
V· · · −
W· − −
X− · · −
Y− · − −
Z− − · ·
1· − − − −
2· · − − −
3· · · − −
4· · · · −
5· · · · ·
6− · · · ·
7− − · · ·
8− − − · ·
9− − − − ·
0− − − − −
"""


# machen dictionary aus wikipaste
def wiki_paste_to_morse_dict(wikicopy):
    wikicopy = wikicopy.replace(' ', '')
    morse_dict = {l[0]: l[1:] for l in wikicopy.splitlines() if l}
    return morse_dict


ascii_morse = wiki_paste_to_morse_dict(raw_wiki_copy)
morse_ascii = {v: k for k, v in ascii_morse.items()}


# return a dictionary of possible morse-chars as key
# and their count as value
def possible_morse_chars(string):
    """
    returns dit,dah or None
    """
    stats = {}

    for c in re.sub("[\w\d ]", '', string):
        try:
            stats[c] += 1
        except KeyError:
            stats[c] = 1

    return stats


# return morse-encoded string
def morse_encode(string, dot='·', dash='−', sep=' ', ignore_unknown=False):
    morse_codes = []

    for char in string.upper():
        try:
            morse_codes.append(ascii_morse[char].replace('·', dot).replace('−', dash))
        except KeyError:
            if not ignore_unknown:
                morse_codes.append(char)

    return sep.join(morse_codes)


# return morse-decoded string with number of errors as tuple
# -> (decoded string, num errors)
def morse_decode(string, dot=None, dash=None):
    """
    decode a "morse string" to ascii text
    uses \s{2,} as word separator
    """
    # dot and dash given, just decode
    if dot and dash:
        errors = 0

        words = []
        # drawback: does not allow single characters.
        for match in re.finditer('([{dit}{dah}]+((?:\\s)[{dit}{dah}]+)+|\w+)'.format(dit=dot, dah=dash), string):
            word = match.group()
            log.debug("morse word: ", word)
            if any([dot in word, dash in word]):
                w = []
                for morse_character in word.split():
                    try:
                        character = morse_ascii[morse_character.replace(dot, '·').replace(dash, '−')]
                        print("Converted \t{} \tto {}".format(morse_character, character))
                    except KeyError:
                        character = morse_character
                        errors += 1
                    w.append(character)
                words.append(''.join(w))
            # words.append(''.join([morse_ascii[x.replace(dot, '·').replace(dash, '−')] for x in word.split()]))
            else:
                words.append(word)
        return ' '.join(words), errors

    # dot/dash given, search for dash/dot
    else:
        if not dash:
            dash_stats = {x: string.count(x) for x in '-−_'}
            dash = max(dash_stats, key=dash_stats.get)
        if not dot:
            dot_stats = {x: string.count(x) for x in '.·*'}
            dot = max(dot_stats, key=dot_stats.get)

        return morse_decode(string, dot=dot, dash=dash)


@pluginfunction('morse-encode', 'encode string to morse', ptypes.COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_morse_encode(argv, **args):
    if not argv:
        return {
            'msg': args['reply_user'] + "usage: morse-encode <string>"
        }

    if len(argv) == 1 and argv[0] == 'that':
        message_stack = args['stack']
        if not message_stack[-1]:
            return
        message = message_stack[-1]['body']
    else:
        message = ' '.join(argv)

    return {
        'msg': args['reply_user'] + ': %s' % morse_encode(message)
    }


@pluginfunction('morse-decode', 'decode morse encoded string', ptypes.COMMAND, ratelimit_class=RATE_FUN | RATE_GLOBAL)
def command_morse_decode(argv, **args):
    if not argv:
        return {
            'msg': args['reply_user'] + "usage: morse-decode <string>"
        }

    if len(argv) == 1 and argv[0] == 'that':
        message_stack = args['stack']
        if not message_stack[-1]:
            return
        message = message_stack[-1]['body']
    else:
        message = ' '.join(argv)

    decoded, errors = morse_decode(message, dot='·', dash='-')

    return {
        'msg': args['reply_user'] + ': %s (%d errors)' % (decoded, errors)
    }
