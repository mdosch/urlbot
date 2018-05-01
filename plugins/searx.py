import logging
import time
from requests.exceptions import SSLError
from functools import wraps
import json
import requests
from lxml import etree, html
from requests import HTTPError, ConnectionError

search_list = []

if not hasattr(json, 'JSONDecodeError'):
    json.JSONDecodeError = ValueError

class BrokenSearxError(RuntimeError):
    def __init__(self, url, response):
        pass

class RateLimitingError(HTTPError):
    pass


def retry(ExceptionToCheck, tries=4, delay=3, backoff=2, logger=None):
    """Retry calling the decorated function using an exponential backoff.

    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/
    original from: http://wiki.python.org/moin/PythonDecoratorLibrary#Retry

    :param ExceptionToCheck: the exception to check. may be a tuple of
        exceptions to check
    :type ExceptionToCheck: Exception or tuple
    :param tries: number of times to try (not retry) before giving up
    :type tries: int
    :param delay: initial delay between retries in seconds
    :type delay: int
    :param backoff: backoff multiplier e.g. value of 2 will double the delay
        each retry
    :type backoff: int
    :param logger: logger to use. If None, print
    :type logger: logging.Logger instance
    """

    def deco_retry(f):

        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck as e:
                    msg = "%s, Retrying in %d seconds..." % (str(e), mdelay)
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry  # true decorator

    return deco_retry


def fetch_all_searx_engines():
    # response = requests.get("http://stats.searx.oe5tpo.com")
    response = requests.get("https://stats.searx.xyz")
    response.raise_for_status()
    tree = etree.XML(
        response.content,
        parser=html.HTMLParser()
    )

    searxes = [str(x) for x in tree.xpath('//span[text()[contains(.,"200 - OK")]]/../..//a/text()') if str(x).startswith("http")]
    logger = logging.getLogger(__name__)
    logger.info("Registered {} searxes".format(len(searxes)))
    if not searxes:
        raise RuntimeError("not a single searx discovered... " + str(response.content))
    return searxes
#    return ["https://search.mdosch.de"]


@retry(ExceptionToCheck=(ConnectionError, BrokenSearxError, RateLimitingError, json.JSONDecodeError, SSLError), tries=10, delay=1, backoff=1.1)
def searx(text):
    global search_list
    if not search_list:
        search_list = fetch_all_searx_engines()
    logger = logging.getLogger(__name__)

    url = search_list[0]
    logger.info('Currently feeding from {} (of {} in stock)'.format(url, len(search_list)))
    try:
        response = requests.get(url, params={
            'q': text,
            'format': 'json',
            'lang': 'en'
        })
    except SSLError:
        search_list.pop(0)
        raise

    if response.status_code == 429:
        search_list.pop(0)
        raise RateLimitingError(response=response, request=response.request)
    elif response.status_code >= 400:
        search_list.pop(0)
        raise BrokenSearxError(url, response)
    try:
        response = response.json()
    except json.JSONDecodeError:
        # "maintenance" they say...
        search_list.pop(0)
        raise

    if 'results' not in response or not response['results']:
        return
    return [(r.get('content', ''), r['url'], url) for r in response['results']][0]
