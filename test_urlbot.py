"""
To be executed with nose

TODO: test all plugins, maybe declare their sample input somewhere near the code
"""
import unittest
import time
from common import buckets, rate_limit, RATE_GLOBAL


class TestEventlooper(unittest.TestCase):
    def test_broken_url(self):
        """
        Test that broken socket calls are not breaking
        """
        from common import fetch_page
        broken_url = 'http://foo'
        result = fetch_page(url=broken_url)
        self.assertEqual(result, (None, None))


from collections import namedtuple

Bucket = namedtuple("BucketConfig", ["history", "period", "max_hist_len"])


class TestRateLimiting(unittest.TestCase):
    def setUp(self):
        # just for assertions
        self.called = {
            RATE_GLOBAL: [],
        }

    def say(self, msg, rate_class=RATE_GLOBAL):
        if rate_limit(rate_class):
            self.called[rate_class].append(msg)
            # print(msg)
            time.sleep(0.1)

    def test_simple_burst(self):
        messages = ["x_%d" % i for i in range(1, 9)]
        for m in messages:
            self.say(msg=m)
        self.assertEqual(messages[:buckets[RATE_GLOBAL].max_hist_len], self.called[RATE_GLOBAL])

    def test_msg_two_bursts(self):
        # custom bucket, just for testing
        buckets[0x42] = Bucket(history=[], period=1, max_hist_len=5)
        self.called[0x42] = []

        bucket = buckets[0x42]
        messages = ["x_%d" % i for i in range(0, 15)]
        for i, m in enumerate(messages):
            if i % bucket.max_hist_len == 0:
                time.sleep(bucket.period)
            self.say(msg=m, rate_class=0x42)
        self.assertEqual(messages, self.called[0x42])
