#!/bin/python3
# -*- coding: utf-8 -*-

import logging
import sys
import yaml

from libcord import libcord, command, Message

root = logging.getLogger()
root.setLevel(logging.INFO)
logging.getLogger('libcord').setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s | %(name)s | %(levelname)s] %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

# Ccommands

@command.register("test")
@command.argument(dest="args", nargs='+')
def test_command(args):
    print(f"running test command, args: {args}")

@command.register(prog="test2")
@command.argument(dest="name", metavar='NAME')
def test_command_2(name: str, number: int, random):
    """test number 2, does this end up in --help ?"""
    print("running test command 2, name: " + name)
    print((name + " ") * number)
    print(f"random: {random} {type(random)}")

@command.register("c")
def test_context(context: Message):
    print(f"context = { context }")

@command.register("d")
def test_defaults(number: int, something: str = None, val: str = "val1"):
    """test the docstring"""
    print(f"testing defaults = number: { number }, something = { something }, val = {val}")

@command.register("m")
def test_multiline(i: int):
    """test the docstring"""
    print(f"testing multiline")
    print("\nnewline"*i)

# TODO: register core commands
# TODO: import modules (use config)

config = None
with open('config.yaml') as f: 
    config = yaml.load(f)

cord: libcord = libcord(**config['core'])

# test wrapper method

def test(cmd: str) -> str:
    print(f"calling `{cmd}`")
    result = command.call(cmd=cmd)
    print(f"result `{result}`")
    return result

# test(cmd="test saf fd<fd ewre")
# test(cmd='test2 "printed 2 times" 2 4')
# test(cmd='test2 "printed 2 times"" asdsd 4')
# test(cmd="test2 -h")
# test(cmd="test2 1 1")

cord.run()
