import Queue
from exceptions import OSError
import threading
from config import MIN_ACCOUNT, MAX_ACCOUNT, LOGGER
from my_queues import account_password_queue, known_users, RECOVER
from misc import OrderedSet
from hashlib import sha1
import itertools

__author__ = 'gifts'

class Generator(threading.Thread):
    def __init__(self):
        super(Generator, self).__init__()
        self.users_list = self.generate_users()
        self.passwords_list = self.generate_passwords()
        #self.iterator = itertools.product(self.users_list, self.passwords_list)
        # TODO: Remove trash
        #self.iterator = (('1000001', '1234567'), )
        self.known_users = set()

    def generate_users(self):
        return self.serial_generator()

    def generate_passwords(self):
        return OrderedSet(self.txt_file('passwords.txt'))

    def txt_file(self, filename):
        data = ''
        try:
            with open(filename, 'rb') as f:
                data = map(lambda x: x.strip(), f.readlines())
        except OSError as e:
            print e
            raise
        return data

    def serial_generator(self, mmin=MIN_ACCOUNT, mmax=MAX_ACCOUNT):
        return (str(i) for i in xrange(mmin, mmax))

    def run(self):
        LOGGER.info('Run numeric login-password generator')
        for user in self.users_list:
            account_password_queue.put((user, sha1('{0}|hekked'.format(user)).hexdigest()))
            RECOVER.put(str(user))
            for password in self.passwords_list:
                if user in known_users:
                    break
                LOGGER.debug('Add in queue: %s:%s', user, password)
                while 1:
                    try:
                        account_password_queue.put((user, password), block=1, timeout=1)
                        break
                    except Queue.Full:
                        LOGGER.error('account_password queue full!')
                        pass


class Generator_numeric(Generator):
    def __init__(self, size):
        self.size = size
        super(Generator_numeric, self).__init__()

    def generate_users(self):
        return OrderedSet(self.txt_file('users{0}.txt'.format(self.size)))

    def generate_passwords(self):
        return self.serial_generator(mmin=10 ** self.size, mmax=10 ** (self.size + 1) - 1)

    def txt_file(self, filename):
        data = ''
        try:
            with open(filename, 'rb') as f:
                data = map(lambda x: x.strip(), f.readlines())
        except OSError as e:
            print e
            raise
        return data

    def serial_generator(self, mmin=MIN_ACCOUNT, mmax=MAX_ACCOUNT):
        return (str(i) for i in xrange(mmin, mmax))


class Generator_enemy(Generator):
    def __init__(self):
        super(Generator_enemy, self).__init__()

    def generate_users(self):
        return self.serial_generator(1000000, 1000020)

    def generate_passwords(self):
        return itertools.cycle(self.serial_generator(mmin=1111, mmax=10000))

    def txt_file(self, filename):
        data = ''
        try:
            with open(filename, 'rb') as f:
                data = map(lambda x: x.strip(), f.readlines())
        except OSError as e:
            print e
            raise
        return data

    def serial_generator(self, mmin=0, mmax=1000):
        return (i for i in xrange(mmin, mmax))

    def run(self):
        LOGGER.info('Run enemy generator')
        for password in self.passwords_list:
            #LOGGER.info('Password: %s', password)
            #ENEMY.put((user, ''))
            for user in self.users_list:
                if user in known_users:
                    break
                LOGGER.debug('%r:%r', user, password)
                while 1:
                    try:
                        account_password_queue.put((user, password), block=1, timeout=1)
                        break
                    except Queue.Full:
                        LOGGER.error('account_password queue full!')
                        pass
