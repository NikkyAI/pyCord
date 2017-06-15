import sys
from pathlib import Path

p = Path(Path(__file__).parent)
modules = list(p.glob('*.py'))
modules = [ f.stem for f in modules if f.is_file() and not str(f.name) == '__init__.py']
# TODO: filter using config
__all__ = modules

