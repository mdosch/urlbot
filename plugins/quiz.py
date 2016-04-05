# -*- coding: utf-8 -*-
import os
import random
from functools import lru_cache

import re

import time
import config
from plugin_system import pluginfunction, ptypes


@pluginfunction('quiz', 'play quiz', ptypes.COMMAND)
def quiz_control(argv, **args):
    usage = """quiz mode usage: "quiz start [secs interval:default 30]", "quiz stop", "quiz rules;
Not yet implemented: "quiz answer", "quiz skip".
If the quiz mode is active, all messages are parsed and compared against the answer.
    """
    if not argv:
        return {'msg': usage}

    rules = """
The answers will be matched by characters/words. Answers will be
 granted points according to the match percentage with a minimum
 percentage depending on word count. After a configurable timeout per
 quiz game, a single winner will be declared, if any. The timeout can
 be cancelled with "quiz answer" or "quiz skip", which results in
 a lost round.
    """

    with config.plugin_config('quiz') as quizcfg:
        if quizcfg is None:
            quizcfg = dict()

        if argv[0] == 'start':
            quizcfg['stop_bit'] = False
            interval = int(argv[1]) if len(argv) > 1 else 30
            quizcfg['interval'] = interval
            return start_random_question()
        elif argv[0] == 'stop':
            return end(quizcfg)
        elif argv[0] == 'answer':
            return answer(quizcfg)
        elif argv[0] == 'skip':
            return skip(quizcfg)
        elif argv[0] == 'rules':
            return {
                'msg': rules
            }


@pluginfunction('quizparser', 'react on chat during quiz games', ptypes.PARSE)
def quizparser(**args):
    with config.plugin_config('quiz') as quizcfg:
        current_quiz_question = get_current_question(quizcfg)
        if current_quiz_question is None:
            return
        else:
            return rate(quizcfg, args['data'], args['reply_user'])


@lru_cache(10)
def get_questions(directory=None):
    if not directory:
        directory = 'plugins/quiz_resources/'
    all_files = sorted(filter(lambda x: x.endswith('.txt'), os.listdir(directory)))
    all_questions = []
    for q_file in all_files:
        with open(directory + q_file) as f:
            all_questions += f.readlines()[1:]
    return all_questions


def get_random_question():
    with config.plugin_config('quiz') as quizcfg:
        questions = get_questions()
        # select a random question
        used_ids = quizcfg.get('used_ids', [])
        q_index = None
        while q_index is None or len(questions[q_index+1].split()) > 8:
            rand = random.choice(range(1956, len(questions)-2, 2))
            if rand not in used_ids:
                q_index = rand

        quizcfg['active_id'] = q_index
        quizcfg['used_ids'] = used_ids + [q_index]
    return questions[q_index], questions[q_index+1]


def get_current_question(quizcfg):
    if quizcfg.get('active_id') and quizcfg.get('active_id') != 'None':
        return int(quizcfg['active_id'])


def end_question():
    with config.plugin_config('quiz') as quizcfg:
        lines = ['Question time over!']

        score = float(quizcfg.get('current_max_score', 0))
        winner = quizcfg.get('current_max_user', 'nobody')

        print(winner, score)
        win_msg = '{} scores with {:.2f}%'.format(winner, score)
        lose_msg = 'nobody scores.'

        the_answer = get_questions()[get_current_question(quizcfg)+1]
        lines.append('Answer to the question: {}'.format(the_answer))

        if score >= 50.0:
            lines.append(win_msg)
        else:
            lines.append(lose_msg)

        quizcfg["locked"] = False
        quizcfg['current_max_user'] = 'nobody'
        quizcfg['current_max_score'] = 0

        quizcfg['active_id'] = None

        action = {
            'msg': lines
        }
        if quizcfg.get('stop_bit', False):
            quizcfg['stop_bit'] = False
            lines.append('stopping the quiz now.')
        else:
            action['event'] = {
                'time': time.time() + 10,
                'command': (start_random_question, ([],))
            }
            lines.append('continuing.')

        return action


def end(quizcfg):
    # TODO: cleanup the switches
    quizcfg['stop_bit'] = True
    quizcfg['locked'] = False
    return {'msg': 'stopping.'}


def rate(quizcfg, response, user):
    """
    rate answer, check threshold, note user score
    :param quizcfg: configsection plugins/quiz
    :param response: text given by users
    :param user: nick to the response
    :return: actiondict
    """
    questions = get_questions()
    current_quiz_question = get_current_question(quizcfg)
    the_answer = questions[current_quiz_question+1].lower()

    anwer_words = set(re.findall('[a-zA-ZäöüÄÖÜß0-9]+', the_answer))
    words = set(response.lower().split())

    # stripping all fill words seems like a tedious task...

    same_words = words.intersection(anwer_words)
    percentage = len(same_words)/len(anwer_words)*100

    threshold = 50
    if (
        percentage >= threshold and
        float(quizcfg.get('current_max_score', 0)) < percentage
    ):
        quizcfg['current_max_user'] = user
        quizcfg['current_max_score'] = percentage
        return {
            'msg': 'Good answer.'
        }

    # verbose_response = {
    #     'msg': 'matching {} words (answer {}), percentage {}'.format(
    #         same_words, anwer_words, percentage
    #     )
    # }


def start_random_question():
    with config.plugin_config('quiz') as quizcfg:
        if quizcfg.get("locked", False):
            return {'msg': 'already running!'}

        else:
            quizcfg["locked"] = True
        qa = get_random_question()

        return {
            'msg': ['Q: {}'.format(qa[0])],
            'event': {
                'command': (end_question, ([],)),
                'time': time.time() + int(quizcfg['interval'])
            }
        }


# TODO: fix those
def skip(quizcfg):
    """ skip the current question, omitting the
    answer and removing it from the used ones """
    raise NotImplementedError()
    quizcfg['used_ids'].remove(get_current_question(quizcfg))
    return end_question()


def answer(quizcfg):
    raise NotImplementedError()
    the_answer = get_questions()[get_current_question(quizcfg)+1]
    return {
        'msg': 'Answer to the question: {}'.format(the_answer),
        'event': {
            'command': (end_question, ([], )),
            'time': time.time() + 3
        }
    }
