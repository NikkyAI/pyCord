import asyncio
from collections import namedtuple
from typing import Dict, Callable, Any, Iterable, List
import argparse
from collections import OrderedDict
from enum import Enum
import inspect
import logging
from io import StringIO
import json
import requests
import requests.exceptions
import shlex
import sys
from time import sleep
import traceback
import yaml
import copy
import re
from re import _pattern_type

from .message import Message
from .gitwiki import Gitwiki
from .authenticator import Authenticator, AuthUser

module_logger = logging.getLogger('libcord.core')

class CommandContext(object):
    def __init__(self, message: Message):
        self.message = message
    
    NONE = None

    def __repr__(self):
        return yaml.dump(self, default_flow_style=False)


CommandContext.NONE = CommandContext(message = None)

class CommandResult(object):
    def __init__(self, output: str, cmd: str = None, is_help: bool = False):
        self.output = output
        self.cmd = cmd
        self.is_help = is_help

    NONE = None

    def __repr__(self):
        return yaml.dump(self, default_flow_style=False)

class ResultType(Enum):
    DEFAULT = 0
    HELP = 1

class Command(object):
    def __init__(self, func: Callable[[Any], Any] = None, parser: argparse.ArgumentParser = None, regex_func: Callable[[Any], Any] = None):
        self.func = func
        self.parser = parser
        self.regex_func = regex_func
    NONE = None

    def __repr__(self):
        return yaml.dump(self, default_flow_style=False)
    
    def description(self):
        return self.parser.description

class CommandHandler:
    def __init__(self, name: str):
        self.name = name #TODO: use for printing
        self.cmd_map = dict()
        self.func_arg_map = {}
        self.func_context_map = {}
        self.func_user_map = {}
        self.func_text_map = {}
        self.func_pattern_map = {}

    def register(self, prog: str, description: str = None, regex=None):
        """
        registers a function as a given command name, with a optional description
        """
        def func_wrapper(func):
            argspec: inspect.FullArgSpec = inspect.getfullargspec(func)
            descript = str(description)
            args = {'prog': prog}
            if not description and func.__doc__:
                # module_logger.debug(f"description: {func.__doc__.strip()}")
                descript = func.__doc__.strip()
                args['description'] = descript
            # parser = argparse.ArgumentParser(prog=prog, description=descript)
            parser = argparse.ArgumentParser(**args)
            arg_dict = self.func_arg_map.get(func, OrderedDict())

            command_context = self.func_context_map.get(func, 'context')
            if command_context:
                if command_context not in argspec.args:
                    module_logger.warning(f"function {func} missing command_context argument {command_context}")
                    self.func_context_map[func] = command_context = False
                if command_context in argspec.annotations and argspec.annotations[command_context] != CommandContext:
                    module_logger.fatal(f"function {func} argument {command_context} type: { argspec.annotations[command_context]} is not matching type {CommandContext}")
                    self.func_context_map[func] = command_context = False
            
            command_user = self.func_user_map.get(func, 'user')
            if command_user:
                if command_user not in argspec.args:
                    module_logger.warning(f"function {func} missing command_user argument {command_user}")
                    self.func_user_map[func] = command_user = False
                if command_user in argspec.annotations and argspec.annotations[command_user] != AuthUser:
                    module_logger.fatal(f"function {func} argument {command_user} type: { argspec.annotations[command_user]} is not matching type {AuthUser}")
                    self.func_user_map[func] = command_user = False

            command_text = self.func_text_map.get(func, 'text')
            if command_text:
                if command_text not in argspec.args:
                    module_logger.warning(f"function {func} missing command_text argument {command_text}")
                    self.func_text_map[func] = command_text = False
                if command_text in argspec.annotations and argspec.annotations[command_text] != str:
                    module_logger.fatal(f"function {func} argument {command_text} type: { argspec.annotations[command_text]} is not matching type {str}")
                    self.func_text_map[func] = command_text = False

            command_pattern = self.func_pattern_map.get(func)

            defaults = {}
            if argspec.defaults:
                for arg, default_value in zip(reversed(argspec.args), reversed(argspec.defaults)):
                    module_logger.debug(f"argument={arg} default={default_value}")
                    defaults[arg] = default_value

            def add_argument(argument: str, data: dict):
                if dest == command_context:
                    module_logger.info('context does not generate arguments')
                    return
                if dest == command_user:
                    module_logger.info('user does not generate arguments')
                    return
                if dest == command_text:
                    module_logger.info('text does not generate arguments')
                    return
                # https://docs.python.org/3.6/library/argparse.html#the-add-argument-method
                # TODO: figure out default values
                module_logger.debug(f"data: {data}")
                arg_type = data.get('arg_type', 'positional') # TODO: replace with enum

                data['dest'] = dest

                if dest in defaults:
                    data['default'] = defaults[dest]

                if dest in defaults and arg_type == "positional":# TODO: replace with enum
                    # make positional arguments optional, because we have default arguments
                    data['nargs'] = '?'

                if dest not in defaults and arg_type == "optional":# TODO: replace with enum
                    data['required'] = True

                if dest in argspec.annotations:
                    data['type'] = argspec.annotations[dest]

                module_logger.debug(f"argument/dest: '{dest}'\ndata: {data}")

                filtered_data = {
                    key: data[key] for key in
                    ['action', 'nargs', 'const', 'default', 'type', 'choices', 'required', 'help', 'metavar', 'dest']
                    if key in data
                }
                filtered_names = []
                if arg_type == "positional":
                    if 'name' in data:
                        filtered_names.append(data['name'])
                if arg_type == "optional":
                    if 'name' in data:
                        filtered_names.append('--'+data['name']) #TODO: use prefix chars for parser (eg. / + $ etc)
                    if 'short' in data:
                        filtered_names.append('-'+data['short'])
                module_logger.debug(f"names: {filtered_names} data: {filtered_data}")
                parser.add_argument(*filtered_names, **filtered_data)

            for dest, data in reversed(arg_dict.items()):
                add_argument(argument=dest, data=data)

            module_logger.debug(f"argspec: {argspec}")
            not_decorated = [arg for arg in argspec.args if arg not in arg_dict]
            for dest in not_decorated:
                data = {}
                data['dest'] = dest
                if dest in argspec.annotations:
                    data['type'] = argspec.annotations[dest]
                module_logger.debug(f"generating default argument for non decorated argument: {dest}")
                add_argument(argument=dest, data=data)
                
            '''
            splits args and executes method, handles capturing output
            '''
            def execute(*args: str, text: str, context: CommandContext = None, user: AuthUser = None) -> CommandResult:
                module_logger.debug(f"\ncalling: {parser.prog}")
                module_logger.debug(f"args: {args}")

                self.prints_help = False

                def fake_exit(status=0, message=None):
                    """Prevents arparse from killing the program"""
                    if message:
                        module_logger.error(f"status: {status} message: {message}")
                        # if status != 2: # not sure if this is good, prevents printing on --help hopefully
                        if not self.prints_help:
                            print(message)
                        module_logger.warning("exit aborted")
                    return
                parser.exit = fake_exit

                old_help = parser.print_help
                def help_wrapper(file=None):
                    self.prints_help = True
                    old_help(file=file)

                parser.print_help = help_wrapper

                old_stdout = sys.stdout

                arguments: dict = {}

                try:
                    sys.stdout = mystdout = StringIO()

                    namespace = parser.parse_args(args=args)
                    arguments: dict = vars(namespace)
                except TypeError as typerr:
                    module_logger.exception("type error during parsing of arguments")
                    print(traceback.format_exc())
                    # print(type(typerr))
                    # print(typerr)

                except Exception as ex:
                    module_logger.exception("exception during parsing of arguments")
                    print(traceback.format_exc())
                finally:
                    sys.stdout = old_stdout

                output = mystdout.getvalue().rstrip()
                is_help = False

                if output:
                    # fancy_output = "> " + output.replace('\n', '\n> ')
                    module_logger.debug(f"help output: \n{output}")
                    return CommandResult(output=output, is_help=True)
                else:

                    # for argument, value in arguments.items():
                    #     if not value:
                    #         module_logger.warning(f"argument: {argument} has no value")
                    #         return f"argument: {argument} has no value"

                    if command_context:
                        module_logger.debug(f"command context: {command_context}")
                        arguments[command_context] = context
                    
                    if command_user:
                        module_logger.debug(f"auth_user: {user}")
                        arguments[command_user] = user

                    if command_text:
                        module_logger.debug(f"command_text: {text}")
                        arguments[command_text] = text
                    
                    try:
                        sys.stdout = mystdout = StringIO()

                        module_logger.debug(arguments)

                        ret = func(**arguments)
                        if type(ret) is str:
                            print(ret)
                        elif type(ret) is ResultType:
                            if ret == ResultType.HELP:
                                is_help = True
                        # TODO check if it is HELP
                    except Exception as ex:
                        module_logger.exception("exception executing function")
                        print(traceback.format_exc())
                    finally:
                        sys.stdout = old_stdout
                    output = mystdout.getvalue().rstrip()
                    module_logger.debug(f"command output: {output}")

                module_logger.debug(f"arguments: {arguments}")
                return CommandResult(output=output, is_help=is_help)
            cmd: Command = self.cmd_map.get(prog, Command())
            cmd.func = execute
            cmd.parser = parser

            if command_pattern:
                def exec_regex(text: str, context: CommandContext = None, user: AuthUser = None) -> CommandResult:#
                    m = command_pattern.fullmatch(text)
                    if m:
                        module_logger.debug(f"\ncalling: {parser.prog}")
                        module_logger.debug(f"args: {args}")

                        arguments = m.groupdict()

                        is_help = False

                        if command_context:
                            module_logger.debug(f"command context: {command_context}")
                            arguments[command_context] = context
                        
                        if command_user:
                            module_logger.debug(f"auth_user: {user}")
                            arguments[command_user] = user

                        if command_text:
                            module_logger.debug(f"command_text: {text}")
                            arguments[command_text] = text

                        try:
                            old_stdout = sys.stdout
                            sys.stdout = mystdout = StringIO()
    
                            module_logger.debug(arguments)

                            ret = func(**arguments)
                            if type(ret) is str:
                                print(ret)
                            elif type(ret) is ResultType:
                                if ret == ResultType.HELP:
                                    is_help = True
                            # TODO check if it is HELP
                        except Exception as ex:
                            module_logger.exception("exception executing function")
                            print(traceback.format_exc())
                        finally:
                            sys.stdout = old_stdout
                    
                        output = mystdout.getvalue().rstrip()
                        module_logger.debug(f"command output: {output}")
                        return CommandResult(output=output, is_help=is_help)
                    return None
                cmd.regex_func = exec_regex
            self.cmd_map[prog] = cmd
            return execute
        return func_wrapper

    def argument(self, arg_type: str = "positional", dest: str = None, name: str = None, short: str = None, **kwargs):
        def func_wrapper(func):
            argspec: inspect.FullArgSpec = inspect.getfullargspec(func)
            arg_dict = self.func_arg_map.get(func, OrderedDict())

            if not dest:
                raise ValueError("dest is required")

            if dest not in arg_dict:
                arg_dict[dest] = {}
            arg_info = arg_dict[dest]
            arg_info['arg_type'] = arg_type
            if name:
                arg_info['name'] = name
            if short:
                arg_info['short'] = short

            arg_dict[dest] = {**arg_info, **kwargs}
            self.func_arg_map[func] = arg_dict
            return func
        return func_wrapper

    def context(self, command_context, enabled: bool = True):
        def func_wrapper(func):
            if enabled and command_context:
                self.func_context_map[func] = command_context
            else:
                self.func_context_map[func] = False
            return func
        return func_wrapper

    def regex(self, pattern_data):
        def func_wrapper(func):
            if type(pattern_data) == str:
                pattern = re.compile(pattern_data)
            elif type(pattern_data) == _pattern_type: pattern = pattern_data
            module_logger.debug(f"regex: {type(pattern)}")
            self.func_pattern_map[func] = pattern

            return func
        return func_wrapper

    # def call(self, cmd: str, context: CommandContext = CommandContext.NONE) -> CommandResult:
    #     try:
    #         tokens = shlex.split(cmd)
    #         prog = tokens[0]
    #         args = tokens[1:]
    #         cmd: Command = self.cmd_map.get(prog)
    #         func = cmd.func
    #         if func:
    #             exec_result: CommandResult = func(context=context, *args)
    #             exec_result.cmd = prog
    #             return exec_result
    #         else:
    #             return CommandResult(output=f"no function {prog} found", cmd=None)
    #     except Exception as ex:
    #         module_logger.exception("Error parsing input")
    #         return CommandResult(output=f"Error parsing input: {str(ex)}", cmd=None)
    #         # return traceback.format_exc() #TODO: get better message
    
    def list(self) -> Dict[str, Command]:
        """
        shallow copy of all registered commands
        """
        return copy.copy(self.cmd_map)

class LibCord:
    def __init__(self, username, prefix: str = '.', token: str = None, host: str = 'localhost', port: int = 4242, pastebin: dict = None, auth: dict = None):
        from libcord.loader import ModLoader
        
        if not username:
            raise TypeError("username required")

        self.prefix = prefix
        self.username = username
        self.host = host
        self.port = port

        # self.pastebin = pastebin

        self.auth = None
        if auth:
            self.auth = Authenticator(send=self.send, **auth)

        self.loader = ModLoader(self)

        self.cmd_handlers = dict()
        self.session = requests.Session()
        self.wiki = Gitwiki(url="git@github.com:NikkyAI/pyCord.wiki.git", web_url_base="https://github.com/NikkyAI/pyCord/wiki")
        if token:
            self.session.headers = {'Authorization': f"Bearer {token}"}
        
        self.q = asyncio.Queue()

    def create_handler(self, name: str) -> CommandHandler:
        handler: CommandHandler = CommandHandler(name=name)
        self.cmd_handlers[name] = handler
        return handler

    def send(self, message: Message):
        if not message.username:
            message.username = self.username
        dict_dump = vars(message)
        dict_dump = {key: dict_dump[key] for key in dict_dump if dict_dump[key]}
        module_logger.debug(f"message: {dict_dump}")
        module_logger.debug(f"message as json: {json.dumps(dict_dump)}")
        url = f"http://{self.host}:{self.port}/api/message"
        response = self.session.post(url, json=dict_dump)
        response.raise_for_status()    

    def call(self, text: str, context: CommandContext = CommandContext.NONE, user: AuthUser = None) -> CommandResult:
        try:
            tokens = shlex.split(text)
            prog = tokens[0]
            args = tokens[1:]
            cmd: Command = None
            for handler_name, cmd_handler in self.cmd_handlers.items():
                if prog in cmd_handler.cmd_map:
                    cmd = cmd_handler.cmd_map[prog]
                    break

            if not cmd:
                module_logger.error(f"command '{prog}' not found")
                return CommandResult(output=f"no function {prog} found", cmd=None)
            func = cmd.func
            if func:
                exec_result: CommandResult = func(context=context, user=user, text=text, *args)
                exec_result.cmd = prog
                return exec_result
            else:
                return CommandResult(output=f"no function {prog} found", cmd=None)
        except Exception as ex:
            module_logger.exception("Error parsing input")
            return CommandResult(output=f"Error parsing input: {str(ex)}", cmd=None)
            # return traceback.format_exc() #TODO: get better message
    
    def call_regex(self, text: str, context: CommandContext = CommandContext.NONE, user: AuthUser = None) -> List[CommandResult]:
        try:
            results = list()
            for handler_name, cmd_handler in self.cmd_handlers.items():
                for prog, cmd in cmd_handler.cmd_map.items():
                    if cmd.regex_func:
                        # TODO: wrap in try catch ?
                        result = cmd.regex_func(text=text, context=context, user=user)
                        if result:
                            result.cmd = prog
                            results.append(result)
            return results
        except Exception as ex:
            module_logger.exception("Error parsing input")
            return CommandResult(output=f"Error parsing input: {str(ex)}", cmd=None)
            # return traceback.format_exc() #TODO: get better message
    
    async def consume_message(self):
        while True:
            message: Message = await self.q.get()
            module_logger.debug(message)
            text: str = message.text
            module_logger.debug(f"text: {text}")
            # handle responses from auth bots
            cmd_result: CommandResult = None
            user = self.auth.identify(message.username, message.account)
            results = self.call_regex(text=text, context=CommandContext(message), user=user)
            if len(results):
                for regex_result in results:
                    if regex_result.output:
                        module_logger.debug(f"return value: {regex_result.output}")
                        if '\n' in regex_result.output:
                            github_url = self.wiki.upload(f"command/{regex_result.cmd}", regex_result.output, is_help=regex_result.is_help)
                            self.send(message.create_response(github_url))
                        else:
                            self.send(message.create_response(regex_result.cmd+": "+regex_result.output))
            if text.startswith(self.prefix):
                module_logger.debug(f"command: '{text}' by {message.username}")
                cmd=text[1:]
                cmd_result: CommandResult = self.call(text=cmd, context=CommandContext(message), user=user)
            if cmd_result:
                # response = message.username + ": " + ret
                if cmd_result.output:
                    module_logger.debug(f"return value: {cmd_result.output}")
                    if '\n' in cmd_result.output:
                        # if cmd_result.help or not self.pastebin or 'token' not in self.pastebin:
                            #TODO: if return value is multiline.. git wiki
                            github_url = self.wiki.upload(f"command/{cmd_result.cmd}", cmd_result.output, is_help=cmd_result.is_help)
                            self.send(message.create_response(github_url))
                        # else:
                        #     TODO: fix pastebin or similar service
                        #     url = pastebin.paste(self.pastebin['token'], cmd_result.output, paste_name=cmd_result.cmd + "_output", paste_private="unlisted", paste_expire_date='1H', paste_format=None)
                        #     self.send(message.create_response(url))
                    else:
                        self.send(message.create_response(cmd_result.output))


    async def produce_message(self):
        while True:
            try:
                url = f"http://{self.host}:{self.port}/api/messages"
                response = self.session.get(url)
                response.raise_for_status()
                if response.content:
                    msg_list = response.json()
                    for message_dict in msg_list:
                        message: Message = Message(**message_dict)
                        # message.libcord = self
                        # result = self.handle_message(message) #TODO: look up await ?
                        
                        await self.q.put(message)
                        # module_logger.debug("added: " + str(message))

            except requests.exceptions.ConnectionError as err:
                module_logger.exception("api endpoint not running")
                #TODO: retry with increasing timeout up until max (of 20s ? )

            except Exception as ex:
                module_logger.exception("unknown error")
            await asyncio.sleep(0.1)
    
    def start(self):
        module_logger.info("starting loop")
        self.loader.load_all()
        loop = asyncio.get_event_loop()
        loop.create_task(self.produce_message())
        loop.create_task(self.consume_message())
        loop.run_forever()