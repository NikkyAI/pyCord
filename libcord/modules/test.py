from libcord import LibCord, Message, CommandHandler, CommandContext
from libcord.authenticator import AuthUser
import yaml
import re
import random

def init(cord: LibCord):
    test: CommandHandler = cord.create_handler('test')

    @test.register("test")
    @test.argument(dest="args", nargs='+')
    def test_command(args):
        print(f"running test command, args: {args}")

    @test.register(prog="test2")
    @test.argument(dest="name", metavar='NAME')
    def test_command_2(name: str, number: int, random):
        """test number 2, does this end up in --help ?"""
        print("running test command 2, name: " + name)
        print((name + " ") * number)
        print(f"random: {random} {type(random)}")

    @test.register("c")
    def test_context(context: CommandContext):
        print(f"context = { context }")

    @test.register("d")
    def test_defaults(number: int, something: str = None, val: str = "val1"):
        """test the docstring."""
        print(f"testing defaults = number: { number }, something = { something }, val = {val}")

    @test.register("m")
    def test_multiline(i: int):
        """test multiline output."""
        print(f"testing multiline")
        print("\nnewline"*i)

    @test.register("identify")
    def test_auth(user: AuthUser):
        """test nickserv identify"""
        if user:
            print(f"testing auth module: username: {user.username}")
        else:
            print('no user')
        # cord.auth.identify(auth_req=AuthRequest(name=context.message.username, account=context.message.account))
        # user: AuthUser = cord.auth.identify(name=context.message.username, account=context.message.account)

        # print(yaml.dump(user))@test.register("identify")
    @test.register('dice')
    @test.regex(r'(?P<a>\d+)dd(?P<b>\d+)')
    def test_regex(text: str, a, b):
        #TODO: add text: str argument
        """roll dice"""
        a = int(a)
        b = int(b)
        c = 0
        for _ in range(a):
            c = c + random.randint(0, b)
        c = c / a
        print(f"{text} = {c}")

    @test.register('regex2')
    @test.regex(r'(?P<a>\d+\s?)')
    def test_regex_2(a):
        """test nickserv identify"""
        print(a)
