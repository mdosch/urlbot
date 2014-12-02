"""
To be executed with nose
"""
import unittest
from urlbot import fetch_page


class TestEventlooper(unittest.TestCase):

	def test_broken_url(self):
		"""
		Test that broken socket calls are not breaking
		"""
		broken_url = 'http://foo'
		result = fetch_page(url=broken_url)
		self.assertEqual(result, (None, None))
