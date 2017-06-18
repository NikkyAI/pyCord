import sys
from libcord import LibCord
from .modules import modules
from importlib import reload, import_module
import logging

module_logger = logging.getLogger('libcord.loader')

class ModLoader():
    def __init__(self, cord: LibCord):
        self.cord = cord

    def load_all(self):
        for mod in modules:
            self.load(mod)

    def load(self, module: str):
        assert(module in modules)
        module_logger.debug(f"load('{module}')")
        _basename = 'libcord.modules.{}'.format(module)
        mod = import_module(_basename)
        mod.init(self.cord)
    
    def reload(self, module: str):
        assert(module in modules)
        module_logger.debug(f"reload('{module}')")
        _basename = 'libcord.modules.{}'.format(module)
        mod = sys.modules[_basename]
        reload(mod)
        mod.init(self.cord)
