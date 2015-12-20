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


class TestPlugins(unittest.TestCase):
    def setUp(self):
        import config
        self.bot_nickname = config.conf_get("bot_nickname")
        pass

    def shortDescription(self):
        return None

    def test_all_commands_no_message(self):
        """
        By specification, currently not possible! should be revisited after settings words[2:].
        Using '' as empty first word as workaround
        """
        import plugins
        plugin_functions = filter(
            lambda x: x[0].startswith("command") and x[1].plugin_type == 'command',
            plugins.__dict__.items()
        )

        msg_obj = {
            'body': '',
            'mucnick': 'hans'
        }

        plugin_arguments = {
            'msg_obj': msg_obj,
            'reply_user': msg_obj['mucnick'],
            'data': msg_obj['body'],
            'cmd_list': [],
            'parser_list': [],
        }

        for p in plugin_functions:
            func = p[1]
            result = func([''], **plugin_arguments)
            self.assertEqual(result, None)

    def test_all_commands_garbage(self):
        """
        message is rubbish
        :return:
        """
        import plugins
        plugin_functions = filter(
            lambda x: x[0].startswith("command") and x[1].plugin_type == 'command',
            plugins.__dict__.items()
        )

        msg_obj = {
            'body': 'urlbot: dewzd hweufweufgw ufzgwufgw ezfgweuf guwegf',
            'mucnick': 'hans'
        }

        plugin_arguments = {
            'msg_obj': msg_obj,
            'reply_user': msg_obj['mucnick'],
            'data': msg_obj['body'],
            'cmd_list': [],
            'parser_list': [],
        }
        words = msg_obj['body'].split()[1:]

        for p in plugin_functions:
            func = p[1]
            result = func(words, **plugin_arguments)
            self.assertEqual(result, None)

    def test_all_commands_with_command(self):
        """
        Call plugins with their name, expect None or some action dict
        """
        import plugins
        plugin_functions = filter(
            lambda x: x[0].startswith("command") and x[1].plugin_type == 'command',
            plugins.__dict__.items()
        )

        for p in plugin_functions:
            func = p[1]
            msg_obj = {
                'body': '{}: {}'.format(self.bot_nickname, func.plugin_name),
                'mucnick': 'hans'
            }

            plugin_arguments = {
                'msg_obj': msg_obj,
                'reply_user': msg_obj['mucnick'],
                'data': msg_obj['body'],
                'cmd_list': [],
                'parser_list': [],
            }
            words = msg_obj['body'].split()[1:]

            result = func(words, **plugin_arguments)

            import inspect
            source = inspect.getsourcelines(func)[0][2:10]

            # assert that check on the right name as long as we're doing that.
            self.assertTrue(func.plugin_name in ''.join(source), '{} not in {}'.format(func.plugin_name, source))

            self.assertTrue(result is None or isinstance(result, dict))
            if result:
                self.assertTrue(any(['msg' in result, 'event' in result, 'presence' in result]))
                if 'event' in result:
                    self.assertTrue(any(['msg' in result['event'], 'command' in result['event']]))
                if 'presence' in result:
                    self.assertTrue(all(['msg' in result['presence'], 'status' in result['presence']]))

    def test_commands_with_params(self):
        """
        Test known commands with params so that
        they don't return immidiately
        """

        import plugins, config
        plugin_functions = filter(
            lambda x: hasattr(x[1], 'plugin_type') and x[1].plugin_type == 'command',
            plugins.__dict__.items()
        )

        # fixture
        config.runtime_config_store['other_bots'].append('pork')

        for p in plugin_functions:
            func = p[1]
            msg_obj = {
                'body': '{}: {}'.format(self.bot_nickname, func.plugin_name),
                'mucnick': config.conf_get('bot_owner')
            }

            plugin_arguments = {
                'msg_obj': msg_obj,
                'reply_user': msg_obj['mucnick'],
                'data': msg_obj['body'],
                'cmd_list': [],
                'parser_list': [],
            }
            words = msg_obj['body'].split()[1:]
            param_mapping = {
                'plugin': ['disable', 'cake'],
                'wp': ['Wikipedia'],
                'wp-en': ['Wikipedia'],
                'choose': ['A', 'B'],
                'decode': ['@'],
                'record': ['urlbug', 'this', 'is', 'sparta'],
                'flausch': ['hans'],
                'set-status': ['unmute'],
                'remove-from-botlist': ['pork'],

            }

            if func.plugin_name in param_mapping:
                words.extend(param_mapping[func.plugin_name])

            result = func(words, **plugin_arguments)

            import inspect
            source = inspect.getsourcelines(func)[0][2:10]

            # assert that check on the right name as long as we're doing that.
            self.assertTrue(func.plugin_name in ''.join(source), '{} not in {}'.format(func.plugin_name, source))

            print(func.plugin_name, result)
            self.assertIsInstance(result, dict, msg=func.plugin_name)
            if result:
                self.assertTrue(any(['msg' in result, 'event' in result, 'presence' in result]))
                if 'event' in result:
                    self.assertTrue(any(['msg' in result['event'], 'command' in result['event']]))
                if 'presence' in result:
                    self.assertTrue(all(['msg' in result['presence'], 'status' in result['presence']]))

    def test_teatimer(self):
        from plugins import command_teatimer
        result = command_teatimer(['teatimer'], reply_user='hans')
        self.assertIn('event', result)
        self.assertIn('time', result['event'])
        self.assertIn('msg', result['event'])
        self.assertIn('msg', result)
