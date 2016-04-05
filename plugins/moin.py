# -*- coding: utf-8 -*-
import logging
log = logging.getLogger(__name__)

from plugin_system import pluginfunction, ptypes

moin_strings_hi = [
    'Hi',
    'Guten Morgen', 'Morgen',
    'Moin',
    'Tag', 'Tach',
    'NAbend', 'Abend',
    'Hallo', 'Hello'
]

moin_strings_bye = [
    'Nacht', 'gN8', 'N8',
    'bye',
]

@pluginfunction('moin', 'parse hi/bye', ptypes.PARSE, enabled=False)
def parse_moin(**args):
    for direction in [moin_strings_hi, moin_strings_bye]:
        for d in direction:
            words = re.split(r'\W+', args['data'])

            # assumption: longer sentences are not greetings
            if 3 < len(args['data'].split()):
                continue

            for w in words:
                if d.lower() == w.lower():
                    if args['reply_user'] in config.conf_get('moin-disabled-user'):
                        log.info('moin blacklist match')
                        return

                    if args['reply_user'] in config.conf_get('moin-modified-user'):
                        log.info('being "quiet" for %s' % w)
                        return {
                            'msg': '/me %s' % random.choice([
                                "doesn't say anything at all",
                                'whistles uninterested',
                                'just ignores this incident'
                            ])
                        }

                    log.info('sent %s reply for %s' % (
                        'hi' if direction is moin_strings_hi else 'bye', w
                    ))
                    return {
                        'msg': '''%s, %s''' % (
                            random.choice(direction),
                            args['reply_user']
                        )
                    }


@pluginfunction('show-moinlist', 'show the current moin reply list, optionally filtered', ptypes.COMMAND)
def command_show_moinlist(argv, **args):
    log.info('sent moin reply list')

    user = None if not argv else argv[0]

    return {
        'msg':
            '%s: moin reply list%s: %s' % (
                args['reply_user'],
                '' if not user else ' (limited to %s)' % user,
                ', '.join([
                              b for b in moin_strings_hi + moin_strings_bye
                              if not user or user.lower() in b.lower()
                              ])
            )
    }


