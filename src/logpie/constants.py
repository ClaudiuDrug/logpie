# -*- coding: UTF-8 -*-

from enum import IntFlag, Enum
from os.path import dirname, realpath
from sys import modules
from types import ModuleType
from weakref import WeakValueDictionary

__all__ = [
    "NAME",
    "MODULE",
    "ROOT",
    "INSTANCES",
    "RLOCKS",
    "STATE",
    "LEVEL",
    "FMT",
]

# default instance name:
NAME: str = "logpie"

# main module:
MODULE: ModuleType = modules.get("__main__")

# root directory:
ROOT: str = realpath(dirname(MODULE.__file__))

# container for `Logger` instances:
INSTANCES: WeakValueDictionary = WeakValueDictionary()

# container for recursive thread lock instances:
RLOCKS: WeakValueDictionary = WeakValueDictionary()


class STATE(Enum):
    """Logger default states."""

    ON: bool = True
    OFF: bool = False


class LEVEL(IntFlag):
    """Default logging levels."""

    NOTSET: int = 0
    DEBUG: int = 10
    INFO: int = 20
    WARNING: int = 30
    ERROR: int = 40
    CRITICAL: int = 50


class FMT:
    """`Formatter` default settings."""
    ROW: str = "${timestamp} - ${level} - ${source}: ${message}"
    TIME: str = "[%Y-%m-%d %H:%M:%S.%f]"
    STACK: str = "<${file}, ${line}, ${code}>"
