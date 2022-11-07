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

# file locks:
FILE_LOCKS = WeakValueDictionary()

# thread locks:
THREAD_LOCKS = WeakValueDictionary()

# fmt regex:
REGEX: str = r"(?P<placeholder>(?:\$\{)(?P<name>(?:\d|\_|\-|[a-zA-Z])+)(?:\}))"

# stack info:
FRAME = namedtuple("FRAME", ["file", "line", "code", "traceback"])

# default stream:
HANDLERS: List[str] = ["console"]  # or "console" or both, always as list.

# filestream modes:
FILE_MODES: dict = {
    "append": "a",
    "truncate": "w",
}


# file handler defaults:
class FILESTREAM:
    FOLDER: str = join(ROOT, "logs")
    IS_STRUCTURED: bool = True
    HAS_DATE: bool = True
    BASENAME: str = "logpie"
    SHOULD_CYCLE: bool = True
    MAX_SIZE: int = 1024 * 1024  # 1MB
    FILE_MODE: str = "append"  # or 'truncate'
    ENCODING: str = "UTF-8"


class FORMATTING:
    """Row formatting."""
    FORMAT: str = r"${timestamp} - ${level} - ${source}: ${message}"
    SOURCE_FMT: str = r"<${file}, ${line}, ${code}>"
    DATE_FMT: str = r"[%Y-%m-%d %H:%M:%S.%f]"


class LEVELS:
    """Default logging levels."""
    NOTSET: int = 0
    DEBUG: int = 10
    INFO: int = 20
    WARNING: int = 30
    ERROR: int = 40
    CRITICAL: int = 50


# logging level 'str' keys:
STRKEYS: dict = {
    "NOTSET": LEVELS.NOTSET,
    "DEBUG": LEVELS.DEBUG,
    "INFO": LEVELS.INFO,
    "WARNING": LEVELS.WARNING,
    "ERROR": LEVELS.ERROR,
    "CRITICAL": LEVELS.CRITICAL,
}

# logging level 'int' keys:
INTKEYS: dict = {value: key for key, value in STRKEYS.items()}

# default logging parameters:
BACKUP: dict = {
    "handlers": HANDLERS,
    "level": LEVELS.NOTSET,

    # formatting:
    "format": FORMATTING.FORMAT,
    "date_fmt": FORMATTING.DATE_FMT,
    "source_fmt": FORMATTING.SOURCE_FMT,

    # file stream settings:
    "folder": FILESTREAM.FOLDER,
    "is_structured": FILESTREAM.IS_STRUCTURED,

    "has_date": FILESTREAM.HAS_DATE,
    "basename": FILESTREAM.BASENAME,
    "should_cycle": FILESTREAM.SHOULD_CYCLE,
    "max_size": FILESTREAM.MAX_SIZE,
    "file_mode": FILESTREAM.FILE_MODE,
    "encoding": FILESTREAM.ENCODING,
}
