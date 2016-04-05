# -*- coding: utf-8 -*-
import time
import logging
from collections import namedtuple

RATE_NO_LIMIT = 0x00
RATE_GLOBAL = 0x01
RATE_NO_SILENCE = 0x02
RATE_INTERACTIVE = 0x04
RATE_CHAT = 0x08
RATE_URL = 0x10
RATE_EVENT = 0x20
RATE_FUN = 0x40

Bucket = namedtuple("BucketConfig", ["history", "period", "max_hist_len"])

buckets = {
    # everything else
    RATE_GLOBAL: Bucket(history=[], period=60, max_hist_len=10),
    # bot writes with no visible stimuli
    RATE_NO_SILENCE: Bucket(history=[], period=10, max_hist_len=5),
    # interactive stuff like ping
    RATE_INTERACTIVE: Bucket(history=[], period=30, max_hist_len=5),
    # chitty-chat, master volume control
    RATE_CHAT: Bucket(history=[], period=10, max_hist_len=5),
    # reacting on URLs
    RATE_URL: Bucket(history=[], period=10, max_hist_len=5),
    # triggering events
    RATE_EVENT: Bucket(history=[], period=60, max_hist_len=10),
    # bot blames people, produces cake and entertains
    RATE_FUN: Bucket(history=[], period=180, max_hist_len=5),
}

rate_limit_classes = buckets.keys()


def rate_limit(rate_class=RATE_GLOBAL):
    """
    Remember N timestamps,
    if N[0] newer than now()-T then do not output, do not append.
    else pop(0); append()

    :param rate_class: the type of message to verify
    :return: False if blocked, True if allowed
    """
    if rate_class not in rate_limit_classes:
        return all(rate_limit(c) for c in rate_limit_classes if c & rate_class)

    now = time.time()
    bucket = buckets[rate_class]
    logging.getLogger(__name__).debug(
        "[ratelimit][bucket=%x][time=%s]%s",
        rate_class, now, bucket.history
    )

    if len(bucket.history) >= bucket.max_hist_len and bucket.history[0] > (now - bucket.period):
        # print("blocked")
        return False
    else:
        if bucket.history and len(bucket.history) > bucket.max_hist_len:
            bucket.history.pop(0)
        bucket.history.append(now)
        return True


def rate_limited(max_per_second):
    """
    very simple flow control context manager
    :param max_per_second: how many events per second may be executed - more are delayed
    :return:
    """
    min_interval = 1.0 / float(max_per_second)

    def decorate(func):
        lasttimecalled = [0.0]

        def ratelimitedfunction(*args, **kargs):
            elapsed = time.clock() - lasttimecalled[0]
            lefttowait = min_interval - elapsed
            if lefttowait > 0:
                time.sleep(lefttowait)
            ret = func(*args, **kargs)
            lasttimecalled[0] = time.clock()
            return ret

        return ratelimitedfunction

    return decorate

