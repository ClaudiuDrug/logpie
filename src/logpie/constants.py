# -*- coding: UTF-8 -*-

from collections import namedtuple
from os.path import dirname, realpath, join
from sys import modules
from types import ModuleType
from typing import List
from weakref import WeakValueDictionary

# main module:
MODULE: ModuleType = modules.get("__main__")

# root directory:
ROOT: str = realpath(dirname(MODULE.__file__))

# logging instances:
LOGGERS = WeakValueDictionary()

# thread lock instances:
LOCKS = WeakValueDictionary()

# stack info:
FRAME = namedtuple("FRAME", ["file", "line", "code", "traceback"])

# fmt regex:
REGEX: str = r"(?P<placeholder>(?:\$\{)(?P<name>(?:\d|\_|\-|[a-zA-Z])+)(?:\}))"


HANDLERS_LIST: List[str] = ["console", "file"]


class LOGGER:
    """Logger defaults."""

    HANDLERS: List[str] = ["console"]  # or "file" or both, always as list.
    STATE: str = "ON"  # or "OFF" (disabled)


class FILESTREAM:
    """File handler defaults."""

    FOLDER: str = join(ROOT, "logs")
    IS_STRUCTURED: bool = True
    HAS_DATE: bool = True
    BASENAME: str = "logpie"
    HAS_NAME: bool = False
    SHOULD_CYCLE: bool = True
    MAX_SIZE: int = 1024 * 1024  # 1MB
    ENCODING: str = "UTF-8"


class FORMATTING:
    """Row default formatting."""

    FORMAT: str = r"${timestamp} - ${level} - ${source}: ${message}"
    SOURCE_FMT: str = r"<${file}, ${line}, ${code}>"
    DATE_FMT: str = r"[%Y-%m-%d %H:%M:%S.%f]"


class LEVELS:
    """Logging levels. Defaults to `NOTSET`."""

    NOTSET: int = 0
    DEBUG: int = 10
    INFO: int = 20
    WARNING: int = 30
    ERROR: int = 40
    CRITICAL: int = 50


# logging levels ('str' keys):
STRKEYS: dict = {
    "NOTSET": LEVELS.NOTSET,
    "DEBUG": LEVELS.DEBUG,
    "INFO": LEVELS.INFO,
    "WARNING": LEVELS.WARNING,
    "ERROR": LEVELS.ERROR,
    "CRITICAL": LEVELS.CRITICAL,
}

# logging levels ('int' keys):
INTKEYS = dict(
    zip(
        tuple(STRKEYS.values()),
        tuple(STRKEYS.keys())
    )
)

# translating states to 'ON' and 'OFF':
STATES: dict = {
    True: "ON",
    1: "ON",
    "ENABLED": "ON",
    "ON": "ON",

    False: "OFF",
    0: "OFF",
    "DISABLED": "OFF",
    "OFF": "OFF",
}
