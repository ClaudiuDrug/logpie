# -*- coding: UTF-8 -*-

from os.path import dirname, realpath, join
from sys import modules
from types import ModuleType
from weakref import WeakValueDictionary

from .mapping import Level

__all__ = [
    "NAME", "MODULE", "ROOT", "INSTANCES", "RLOCKS",
    "NOTSET", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL",
    "ROW", "TIME", "STACK",
    "MODE", "ENCODING", "FOLDER", "MAX_SIZE", "CYCLE", "CHRONOLOGICAL",
    "DATE_PREFIX", "DATE_AWARE",
]

# default name:
NAME: str = "logpie"

# main module:
MODULE: ModuleType = modules.get("__main__")

# root directory:
ROOT: str = realpath(dirname(MODULE.__file__))

# container for `Logger` instances:
INSTANCES: WeakValueDictionary = WeakValueDictionary()

# container for recursive thread lock instances:
RLOCKS: WeakValueDictionary = WeakValueDictionary()

# default severity levels:
NOTSET: Level = Level(name="NOTSET", value=0)
DEBUG: Level = Level(name="DEBUG", value=10)
INFO: Level = Level(name="INFO", value=20)
WARNING: Level = Level(name="WARNING", value=30)
ERROR: Level = Level(name="ERROR", value=40)
CRITICAL: Level = Level(name="CRITICAL", value=50)

# default formatting:
ROW: str = "${timestamp} - ${level} - ${source}: ${message}"
TIME: str = "[%Y-%m-%d %H:%M:%S.%f]"
STACK: str = "<${file}, ${line}, ${code}>"

# FileHandler defaults:
MODE: str = "a"
ENCODING: str = "UTF-8"
FOLDER: str = join(ROOT, "logs")
MAX_SIZE: int = (1024 ** 2) * 4  # in bytes (4 MB)
CYCLE: bool = False
CHRONOLOGICAL: bool = False
DATE_PREFIX: bool = False
DATE_AWARE: bool = False
