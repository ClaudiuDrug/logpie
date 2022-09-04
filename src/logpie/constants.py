# -*- coding: UTF-8 -*-

from collections import namedtuple
from os.path import dirname, realpath, join
from sys import modules
from threading import RLock
from types import ModuleType
from weakref import WeakValueDictionary

RLOCK: RLock = RLock()
INSTANCES = WeakValueDictionary()

ROW = namedtuple("ROW", ["timestamp", "level", "file", "line", "code", "message"])
FRAME = namedtuple("FRAME", ["file", "line", "code"])
TRACEBACK = namedtuple("TRACEBACK", ["file", "line", "code", "message"])

# main module
MODULE: ModuleType = modules.get("__main__")

# root directory
ROOT: str = dirname(realpath(MODULE.__file__))

FOLDER: str = join(ROOT, "logs")

BACKUP: dict = {
    "LOGGER": {
        "basename": "logpie",  # if handler is `file`
        "handler": "console",  # or `file` or `nostream` (does nothing)
        "debug": False,  # if set to `True` it will also print `DEBUG` messages
    }
}
