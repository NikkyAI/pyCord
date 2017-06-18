from .message import Message
import json
from typing import Callable, Any
from random import SystemRandom
from collections import deque
import logging
from pathlib import Path
import yaml

module_logger = logging.getLogger('libcord.auth')

class AuthUser(object):
    def __init__(self, username: str, account: str, id = None, nickname: str = None):
        self.username = username
        self.nickname = nickname
        self.account = account
        self.id = id
    
    def __repr__(self):
        return yaml.dump(self)

class Authenticator(object):

    def __init__(self, send: Callable[[Message], None], gateway: str="api-auth"):
        self.send = send
        self.gateway = gateway
        self.random = SystemRandom()

    def identify(self, name: str, account: str) -> AuthUser:
        p = Path('auth/', f"{account}.txt")
        if p.exists():
            with open(p, 'r') as f:
                account_data = yaml.load(f.read())
                for user_id, user in account_data['users'].items():
                    if name == user['username']:
                        return AuthUser(account=account, id=user_id, **user)
                for user_id, user in account_data['users'].items():
                    if 'nickname' in user:
                        if name == user['nickname']:
                            return AuthUser(account=account, id=user_id, **user)
            module_logger.error('no user found')
        else:
            module_logger.warning(f"file: {p} does not exist")
        return None