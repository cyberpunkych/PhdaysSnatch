import Queue
import threading
from config import MY_ACCOUNT

__author__ = 'gifts'

account_password_queue = Queue.Queue(100)
GOOD = Queue.Queue()
CHANGE = Queue.Queue()
ENEMY = Queue.Queue(50)
RECOVER = Queue.Queue()
OTP_QUEUE = Queue.Queue(50)

try:
    with open('enemies.txt', 'rb') as f:
        data = f.readlines()
except (OSError, IOError):
    data = ('', )

ENEMY_LIST = set(map(lambda x: x.strip(), data))

kLock = threading.Lock()
known_users = set()
known_users.add(MY_ACCOUNT)