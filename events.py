# -*- coding: utf-8 -*-
import logging
import time
import sched
import threading

EVENTLOOP_DELAY = 0.100  # seconds

event_list = sched.scheduler(time.time, time.sleep)


def register_active_event(t, callback, args, action_runner, plugin, msg_obj, mutex=None):
    """
    Execute a callback at a given time and react on the output

    :param t: when to execute the job
    :param callback: the function to execute
    :param args: parameters for said function
    :param action_runner: bots action dict parser
    :param plugin: pass-through object for action parser
    :param msg_obj: pass-through object for action parser
    :return:
    """
    def func(func_args):
        action = callback(*func_args)
        if action:
            action_runner(action=action, plugin=plugin, msg_obj=msg_obj)
    register_event(t, func, args, mutex=mutex)


def register_event(t, callback, args, **kwargs):
    for pending_event in event_list.queue:
        if kwargs.get('mutex') and pending_event.kwargs.get('mutex', None) == kwargs.get('mutex'):
            logging.debug("Dropped event: %s", kwargs.get('mutex'))
            return
    event_list.enterabs(t, 0, callback, args)


class EventLoop(threading.Thread):
    def run(self):
        while 1:
            event_list.run(False)
            time.sleep(EVENTLOOP_DELAY)

event_loop = EventLoop()
