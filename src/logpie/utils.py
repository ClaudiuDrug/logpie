# -*- coding: UTF-8 -*-

from datetime import datetime, timezone
from functools import wraps
from os import makedirs
from os.path import exists
from typing import Any

__all__ = [
    "get_type",
    "get_local",
    "get_utc",
    "check_state",
    "check_tree",
    "make_dirs",
    "get_size_of",
]


def get_type(value: Any) -> str:
    """Get the type name of `value`."""
    return type(value).__name__


def get_local() -> datetime:
    """Returns an aware localized `datetime` object."""
    utc = get_utc()
    return utc.astimezone()


def get_utc() -> datetime:
    """Returns a UTC `datetime`."""
    return datetime.now(timezone.utc)


def check_state(method):
    """
    Check if the logger is enabled and
    proceed to record the message else pass.
    """
    @wraps(method)
    def wrapper(logger, *args, **kwargs):
        if logger.is_enabled():
            method(logger, *args, **kwargs)

    return wrapper


def check_tree(method):
    """Ensure that the folder tree exists."""
    @wraps(method)
    def wrapper(handler):
        path: str = method(handler)
        if not exists(path):
            make_dirs(path)
        return path
    return wrapper


def make_dirs(path: str):
    """Attempt to create a folder tree."""
    try:
        makedirs(path)
    except FileExistsError:
        pass


def get_size_of(value: str) -> int:
    """Get the size in bytes of the given `value`."""
    return len(value.encode("UTF-8"))
