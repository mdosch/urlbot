# -*- coding: utf-8 -*-
import os
import random
from functools import lru_cache

import re

import time


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


def get_random_question(quizcfg):
    questions = get_questions()
    # select a random question
    used_ids = quizcfg.get('used_ids', [])
    q_index = None
    while q_index is None:
        rand = random.choice(range(0, len(questions)-2, 2))
        if rand not in used_ids:
            q_index = rand

    quizcfg['active_id'] = q_index
    quizcfg['used_ids'] = used_ids + [q_index]
    return questions[q_index], questions[q_index+1]


def get_current_question(quizcfg):
    if quizcfg.get('active_id'):
        return int(quizcfg['active_id'])


def end_question(quizcfg):
    lines = ['Question time over!']

    score = float(quizcfg.get('current_max_score', 0))
    winner = quizcfg.get('current_max_user', 'nobody')

    print(winner, score)
    win_msg = '{} scores with {:.2f}%'.format(winner, score)
    lose_msg = 'nobody scores.'

    if score > 50.0:
        lines.append(win_msg)
    else:
        lines.append(lose_msg)

    quizcfg['current_max_user'] = 'nobody'
    quizcfg['current_max_score'] = 0

    quizcfg['active_id'] = None

    start_next = None
    if not quizcfg.get('stop_bit', False):
        start_next = {
            'time': time.time() + 10,
            'command': (start_random_question, ([quizcfg],))
        }
    return {
        'msg': lines,
        'event': start_next
    }


def stop(quizcfg):
    quizcfg['stop_bit'] = True
    return end_question(quizcfg)


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
    answer = questions[current_quiz_question+1].lower()

    anwer_words = set(re.findall('[a-zA-ZäöüÄÖÜß]+', answer))
    words = set(response.lower().split())

    # stripping all fill words seems like a tedious task...

    same_words = words.intersection(anwer_words)
    percentage = len(same_words)/len(anwer_words)*100

    threshold = 50
    if (
        percentage > threshold and
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


def start_random_question(quizcfg, interval):
    stop(quizcfg)
    qa = get_random_question(quizcfg)

    return {
        'msg': ['Q: {}'.format(qa[0])],
        'event': {
            'command': (end_question, ([quizcfg],)),
            'time': time.time() + interval
        }
    }


def skip(quizcfg):
    """ skip the current question, omitting the
    answer and removing it from the used ones """
    quizcfg['used_ids'].remove(get_current_question(quizcfg))
    return end_question(quizcfg)


def answer(quizcfg):
    the_answer = get_questions()[get_current_question(quizcfg)+1]
    return {
        'msg': 'Answer to the question: {}'.format(the_answer),
        'event': {
            'command': (end_question, ([quizcfg], )),
            'time': time.time() + 3
        }
    }
