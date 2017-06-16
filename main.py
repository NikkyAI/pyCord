#!/bin/python3
# -*- coding: utf-8 -*-

import logging
import sys
import yaml

from libcord import LibCord

root = logging.getLogger()
root.setLevel(logging.INFO)
logging.getLogger('libcord').setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('[%(asctime)s | %(name)s | %(levelname)s] %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

config = None
with open('config.yaml') as f: 
    config = yaml.load(f)

cord: LibCord = LibCord(**config)

# test wrapper method

def test(cmd: str) -> str:
    print(f"calling `{cmd}`")
    result = cord.call(cmd=cmd)
    print(f"result `{result}`")
    return result

# test(cmd="test saf fd<fd ewre")
# test(cmd='test2 "printed 2 times" 2 4')
# test(cmd='test2 "printed 2 times"" asdsd 4')
# test(cmd="test2 -h")
# test(cmd="test2 1 1")

cord.start()
