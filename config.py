__author__ = 'gifts'

import logging
#logging.basicConfig(level=logging.DEBUG)#, filename='result.txt', filemode='ab')
logging.basicConfig(level=logging.CRITICAL)#, filename='result.txt', filemode='ab')
LOGGER = logging.getLogger(__name__)

handler = logging

import re

TARGET_HOST = '192.168.252.128'

MY_ACCOUNT = '90107430600712500003'
MY_LOGIN = '1000003'
MY_PASSWORD = '2gJgff'

MIN_ACCOUNT = 1000000
MAX_ACCOUNT = 1000081
FORCE_STEAL = 1

DUPE_GOLD = True
CONCURRENT_RACE = 3

RE_ACCOUNT_NUMBER = re.compile(r'Account number:</b> (\d+)')
RE_AMOUNT = re.compile(r'([0-9\.e\+]+) RUB')
NEW_PASSWORD = re.compile(r'New password: (\w+)')
RE_ID = re.compile(r'<b>Id:</b> (\d+)<')
RE_TICKET = re.compile(r'One-time password \(# (\d+)\):')

