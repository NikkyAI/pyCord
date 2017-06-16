from .message import Message
import json
from typing import Callable, Any
from random import SystemRandom
from collections import deque
import logging

module_logger = logging.getLogger('libcord.auth')

class AuthRequest(object):
    def __init__(self, nickname: str, account: str, protocol: str, request_id: int):
        self.nickname = nickname
        self.account = account
        self.request_id = request_id

class AuthResponse(object):
    def __init__(self, username: str, request_id: int):
        self.username = username
        self.request_id = request_id

class AuthenticatedUser(object):
    def __init__(self, username: str, account: str):
        self.username = username
        self.account = account

class AuthExec(object):
    def __init__(self, func: Callable[[Any],Any], args: dict, user_arg: str = 'user'):
        self.func = func
        self.args = args
        self.user_arg = user_arg

    def execute(self, user: AuthenticatedUser):
        self.args[self.user_arg] = user
        return self.func(**args)

class Authenticator(object):

    def __init__(self, send: Callable[[Message], None], gateway: str="api-auth"):
        self.send = send
        self.gateway = gateway
        self.auth_requests = dict()
        self.auth_execs = dict()
        self.last_ids = deque()
        self.random = SystemRandom()

    def identify(self, auth_req: AuthRequest) -> str:
        rand_id: int = None
        while rand_id in self.last_ids and rand_id:
            rand_id = self.random.randint(0, 2^10)
        auth_req.request_id = rand_id
        while len(self.last_ids) > 20:
            self.last_ids.popleft()
        self.last_ids.append(rand_id)

        self.auth_requests[id] = auth_req

        text: str = json.dumps(auth_req)
        self.send(username="botmaster", message=Message(text=text,gateway=self.gateway))
        return auth_req
    
    def execute_authenticated(self, func: Callable[[Any],Any], args: dict):
        auth_exec: AuthExec = AuthExec(func=func, args=args)


    def handle(self, message: Message):
        module_logger.debug(f"handle auth message: {message}")
        auth_response: AuthResponse
        try:
            data = json.load(message.text)
            auth_response = AuthResponse(**data)
        except ValueError as valerr:
            module_logger.exception("value error during parsing of json")
        
        id: int = auth_response.request_id
        request: AuthRequest = self.auth_requests[id]
        user: AuthenticatedUser = AuthenticatedUser(username=auth_response.username, account=request.account)

        auth_exec = self.auth_execs[request]
        #TODO: delete self.auth_requests[id]
        #TODO: delete self.auth_execs[id]

        return auth_exec.execute(user)