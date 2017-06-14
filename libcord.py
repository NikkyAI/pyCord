from gitwiki import Gitwiki
import argparse
from collections import OrderedDict
import inspect
import logging
from io import StringIO
import json
import requests
import requests.exceptions
import shlex
import sys
import datetime
from time import sleep
import traceback
import yaml
from collections import namedtuple

module_logger = logging.getLogger('libcord.core')

class Message(object):

# {'text': '!test --help', 'channel': 'bridge-test', 'username': 'Nikky', 'avatar': 'https://cdn.discordapp.com/avatars/11222862436
# 6575616/6c8d3b490bd3e56afc2b2e191f9c0767.jpg', 'account': 'discord.teamdev', 'event': '', 'protocol': 'discord', 'gateway': 'test
# 2', 'timestamp': '2017-06-06T22:26:08.759413856+02:00'}
    def __init__(self, text: str, channel: str = None, username: str = None, avatar: str = None, account: str = None, event: str = None, protocol: str = None, gateway: str = None, timestamp: datetime = None):
        self.text = text
        self.channel = channel
        self.username = username
        self.avatar = avatar
        self.account = account
        self.event = event
        self.protocol = protocol
        self.gateway = gateway
        self.timestamp = timestamp

    def __repr__(self):
        return yaml.dump(self, default_flow_style=True)

    def create_response(self, response: str):
        #TODO: append original username in front of message string?
        response_message = Message(text = response, gateway = self.gateway)
        # self.libcord.send(response_message)
        return response_message

class CommandContext(object):
    def __init__(self, message: Message):
        self.message = message
    
    NONE = None

    def __repr__(self):
        return yaml.dump(self, default_flow_style=False)


CommandContext.NONE = CommandContext(message = None)

class CommandResult(object):
    def __init__(self, result: str, cmd: str = None):
        self.result = result
        self.cmd = cmd
    
    NONE = None

    def __repr__(self):
        return yaml.dump(self, default_flow_style=False)

class Command:
    def __init__(self):
        self.func_map = {}
        self.func_arg_map = {}
        self.func_context_map = {}

    def register(self, prog: str, description: str = None):
        def func_wrapper(func):
            argspec: inspect.FullArgSpec = inspect.getfullargspec(func)
            descript = str(description)
            if not description and func.__doc__:
                descript = func.__doc__
            parser = argparse.ArgumentParser(prog=prog, description=descript)
            arg_dict = self.func_arg_map.get(func, OrderedDict())

            command_context = self.func_context_map.get(func, 'context')
            if command_context:
                if command_context not in argspec.args:
                    module_logger.warning(f"function {func} missing command_context argument {command_context}")
                    self.func_context_map[func] = command_context = False
                if command_context in argspec.annotations and argspec.annotations[command_context] != CommandContext:
                    module_logger.fatal(f"function {func} argument {command_context} type: { argspec.annotations[command_context]} is not matching type {CommandContext}")
                    self.func_context_map[func] = command_context = False

            defaults = {}
            if argspec.defaults:
                for arg, default_value in zip(reversed(argspec.args), reversed(argspec.defaults)):
                    module_logger.debug(f"argument={arg} default={default_value}")
                    defaults[arg] = default_value

            def add_argument(argument: str, data: dict):
                if dest == command_context:
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
            def execute(*args: str, context: CommandContext = None):
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
                    # print(type(typerr))
                    # print(typerr)

                except Exception as ex:
                    module_logger.exception("exception during parsing of arguments")
                    print(traceback.format_exc())
                finally:
                    sys.stdout = old_stdout

                output = mystdout.getvalue().rstrip()

                if output:
                    # fancy_output = "> " + output.replace('\n', '\n> ')
                    module_logger.debug(f"help output: \n{output}")
                else:

                    # for argument, value in arguments.items():
                    #     if not value:
                    #         module_logger.warning(f"argument: {argument} has no value")
                    #         return f"argument: {argument} has no value"

                    if command_context:
                        module_logger.debug(f"command context: {command_context}")
                        arguments[command_context] = context

                    try:
                        sys.stdout = mystdout = StringIO()

                        func(**arguments)

                    except Exception as ex:
                        module_logger.exception("exception executing function")
                        print(traceback.format_exc())
                    finally:
                        sys.stdout = old_stdout
                    output = mystdout.getvalue().rstrip()
                    module_logger.debug(f"command output: {output}")

                module_logger.debug(f"arguments: {arguments}")
                return output
            self.func_map[prog] = execute
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
    def call(self, cmd: str, context: CommandContext = CommandContext.NONE) -> CommandResult:
        try:
            tokens = shlex.split(cmd)
            prog = tokens[0]
            args = tokens[1:]
            func = self.func_map.get(prog)
            if func:
                return CommandResult(result=func(context = context, *args), cmd=prog)
            else:
                return CommandResult(result=f"no function {prog} found", cmd="")
        except Exception as ex:
            module_logger.exception("Error parsing input")
            return self.CommandResult(result=f"Error parsing input: {str(ex)}", cmd="")
            # return traceback.format_exc() #TODO: get better message

command = Command()

# example

@command.register("example")
def method_with_custom_name(my_arg):
    return "The args is: " + my_arg

class libcord:
    def __init__(self, prefix: str = '!', username: str = 'cord', token: str = None, host: str = 'localhost', port: int = 4242, protocol: str = 'http'):
        self.prefix = prefix
        self.username = username
        self.host = host
        self.port = port
        self.protocol = protocol
        self.session = requests.Session()
        self.wiki = Gitwiki(url="git@github.com:NikkyAI/pyCord.wiki.git", web_url_base="https://github.com/NikkyAI/pyCord/wiki")
        if token:
            self.session.headers = {'Authorization': f"Bearer {token}"}
    call = command.call

    def send(self, message: Message):
        if not message.username:
            message.username = self.username
        dict_dump = vars(message)
        dict_dump = {key: dict_dump[key] for key in dict_dump if dict_dump[key]}
        module_logger.debug(f"message: {dict_dump}")
        module_logger.debug(f"message as json: {json.dumps(dict_dump)}")
        url = f"{self.protocol}://{self.host}:{self.port}/api/message"
        response = self.session.post(url, json=dict_dump)
        response.raise_for_status()

    def run(self):
        while True:
            try:
                url = f"{self.protocol}://{self.host}:{self.port}/api/messages"
                response = self.session.get(url)
                response.raise_for_status()
                if response.content:
                    msg_list = response.json()
                    for message_dict in msg_list:
                        message: Message = Message(**message_dict)
                        # message.libcord = self
                        module_logger.debug(message)
                        text: str = message.text
                        module_logger.debug(f"text: {text}")
                        if text.startswith(self.prefix):
                            module_logger.debug(f"command: '{text}' by {message.username}")
                            cmd_result: CommandResult = command.call(cmd=text[1:], context=CommandContext(message))
                            # response = message.username + ": " + ret
                            if cmd_result.result:
                                module_logger.debug(f"return value: {cmd_result.result}")
                                if '\n' in cmd_result.result:
                                    #TODO: if return value is multiline.. git wiki
                                    test = self.wiki.upload(f"command/{cmd_result.cmd}", cmd_result.result)
                                    self.send(message.create_response(test))
                                else:
                                    self.send(message.create_response(cmd_result.result))

            except requests.exceptions.ConnectionError as err:
                module_logger.exception("api endpoint not running")
                #TODO: retry with increasing timeout up until max (of 20s ? )

            except Exception as ex:
                module_logger.exception("unknown error")
            sleep(0.1)
