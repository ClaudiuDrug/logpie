# -*- coding: UTF-8 -*-

from datetime import date, datetime, timezone
from functools import wraps
from glob import glob
from os import makedirs, walk
from os.path import basename, isdir, join, exists
from re import finditer, MULTILINE
from shutil import rmtree
from threading import RLock
from typing import Any, Tuple, Union, List, Generator
from zipfile import ZipFile

from .constants import STRKEYS, INTKEYS, STATES, LOCKS, HANDLERS_LIST
from .exceptions import UnknownLevelError, UnknownStateError, UnknownHandlerError


def dispatch_lock(name: str) -> RLock:
    if name not in LOCKS:
        instance = RLock()
        LOCKS.update({name: instance})
    return LOCKS.get(name)


def get_local() -> datetime:
    """Returns an aware localized `datetime` object."""
    utc = get_utc()
    return utc.astimezone()


def get_utc() -> datetime:
    """Returns a UTC `datetime`."""
    return datetime.now(timezone.utc)


def to_string(value: Any, encoding: str = "UTF-8") -> str:
    if not isinstance(value, str):
        if isinstance(value, bytes):
            return value.decode(encoding)
        return str(value)
    return value


def ensure_tree(path: str):
    if not exists(path):
        create_tree(path)


def create_tree(path: str):
    try:
        makedirs(path)
    except FileExistsError:
        pass


def get_fields(pattern: str, text: str) -> List[str]:
    """Find and return a dictionary of row dictionary."""
    matches = finditer(pattern, text, MULTILINE)
    return [
        match.group("name")
        for match in matches
    ]


def cleanup(folder_path: str):
    if exists(folder_path) and isdir(folder_path):
        results = scan(folder_path)

        for folder, files in results:
            archive(f"{folder}.zip", files)
            rmtree(folder)


def scan(target: str) -> Generator:
    today: date = date.today()
    month: str = today.strftime("%B").lower()
    months: list = months_list(today)

    for root, folders, files in walk(target):

        if (root == target) or (len(folders) == 0):
            continue

        for folder in folders:
            if folder == month:
                continue

            if folder in months:
                folder: str = join(root, folder)
                files: str = join(folder, "*.log")

                yield folder, (file for file in glob(files))


def archive(file_path: str, data: Union[Generator, str]):
    """Archive `data` to the given `file_path`."""
    with ZipFile(file_path, "w") as zip_handle:
        if isinstance(data, Generator) is True:
            for file in data:
                path, name = file, basename(file)
                zip_handle.write(path, name)
        else:
            path, name = data, basename(data)
            zip_handle.write(path, name)


def months_list(today: date) -> List[str]:
    return [
        date(today.year, n, 1).strftime("%B").lower()
        for n in range(1, 13)
        if n != today.month
    ]


def check_state(method):
    """
    Check if the logger is enabled and also update the params before calling
    the logging method.
    """

    @wraps(method)
    def wrapper(*args, **kwargs):

        if args[0].state == "ON":
            _update_params(method.__name__, kwargs)
            method(*args, **kwargs)

    return wrapper


def _update_params(name: str, kwargs: dict):
    """
    Check if the `timestamp` and `depth` params are present before calling the
    logging method.

    :param name: Name of the calling method.
    :param kwargs: Keyword arguments passed to the calling method.
    """

    if "timestamp" not in kwargs:
        kwargs.update(timestamp=get_local())

    if "depth" not in kwargs:

        if name == "log":
            kwargs.update(depth=6)

        else:
            kwargs.update(depth=8)


def _check_level(value: Union[int, str]) -> int:
    """
    Check if a given `value` is a valid logging level
    and return its appropriate integer value.
    """
    if not isinstance(value, (int, str)):
        raise TypeError(
            f"Logging level must be of type 'str' or 'int' not '{type(value).__name__}'!"
        )

    value = _normalise_value(value)

    if not _level_exists(value):
        raise UnknownLevelError(
            f"Unknown logging level: '{value}'!"
        )

    if isinstance(value, str):
        return STRKEYS.get(value)

    return value


def _normalise_value(value: Union[str, bool, int]) -> Union[str, bool, int]:
    if isinstance(value, str):
        if value.isnumeric():
            return int(value)
        return value.upper()
    return value


def _level_exists(level: Union[int, str]) -> bool:
    """Check if the given `level` exists."""
    if isinstance(level, str):
        return level in STRKEYS
    return level in INTKEYS


def check_config(method):
    """
    Check and update configuration parameters before setting them.
    """

    @wraps(method)
    def wrapper(*args, **kwargs):

        _update_state(kwargs)
        _update_level(args[0], kwargs)
        _update_handlers(kwargs)

        _is_string("format", kwargs)
        _is_string("date_fmt", kwargs)
        _is_string("source_fmt", kwargs)

        _is_string("folder", kwargs)
        _is_boolean("is_structured", kwargs)

        _is_boolean("has_date", kwargs)
        _is_string("basename", kwargs)
        _is_boolean("has_name", kwargs)
        _is_boolean("should_cycle", kwargs)
        _is_integer("max_size", kwargs)
        _is_string("encoding", kwargs)

        method(*args, **kwargs)

    return wrapper


def _update_level(cls, kwargs: dict):
    """
    If the `level` param is present in kwargs then check if it's a valid
    level and convert it to its appropriate integer value.
    That means can not only use integers but also string objects wich
    represent either the name of the level or the level number.
    """
    if "level" in kwargs:
        try:
            level: int = _check_level(kwargs.pop("level"))
        except (TypeError, UnknownLevelError):
            raise
        else:
            kwargs.update(level=level)
            cls._reset_allowed(level)


def _update_state(kwargs: dict):
    if "state" in kwargs:
        try:
            value: str = _check_state(kwargs.pop("state"))
        except UnknownStateError:
            raise
        else:
            kwargs.update(state=value)


def _check_state(value: Union[str, bool, int]) -> str:

    if not isinstance(value, (str, bool, int)):
        raise TypeError(
            f"Logger state 'value' must be of type 'str', 'bool' or 'int' not '{type(value).__name__}'!"
        )

    value = _normalise_value(value)

    if value not in STATES:
        raise UnknownStateError(
            f"Unknown state value: '{value}'!"
        )

    if value in STATES:
        return STATES.get(value)

    return value


def _is_string(target: str, kwargs):
    if target in kwargs:
        value: str = kwargs.get(target)
        try:
            _check_string(value)
        except TypeError:
            raise


def _is_boolean(target: str, kwargs):
    if target in kwargs:
        value: bool = kwargs.get(target)
        try:
            _check_bool(value)
        except TypeError:
            raise


def _is_integer(target: str, kwargs):
    if target in kwargs:
        value: int = kwargs.get(target)
        try:
            _check_integer(value)
        except TypeError:
            raise


def _check_string(value: str):
    if not isinstance(value, str):
        raise TypeError(
            f"'value' must be of type 'str' not '{type(value).__name__}'!"
        )


def _check_bool(value: bool):
    if not isinstance(value, bool):
        raise TypeError(
            f"'value' must be of type 'bool' not '{type(value).__name__}'!"
        )


def _check_integer(value: int):
    if not isinstance(value, int):
        raise TypeError(
            f"'value' must be of type 'int' not '{type(value).__name__}'!"
        )


def _update_handlers(kwargs):
    if "handlers" in kwargs:
        try:
            handlers: List[str] = _check_handlers(kwargs.pop("handlers"))
        except TypeError:
            raise
        else:
            kwargs.update(handlers=handlers)


def _check_handlers(value: Union[List[str], Tuple[str], str]) -> List[str]:

    if not isinstance(value, (list, tuple, str)):
        raise TypeError(
            f"Logging 'handlers' value must be of type 'list[str]', 'tuple[str]' or 'str' not '{type(value).__name__}'!"
        )

    if isinstance(value, tuple):
        return list(_check_handler(item) for item in value)

    if isinstance(value, str):
        return [_check_handler(value)]

    return [_check_handler(item) for item in value]


def _check_handler(value: str):
    if not isinstance(value, str):
        raise TypeError(
            f"Logging handler value must be of type 'str' not '{type(value).__name__}'!"
        )

    handler = value.lower()

    if handler not in HANDLERS_LIST:
        raise UnknownHandlerError(
            f"Logging handler 'value' must be either 'file' or 'console' not '{value}'!"
        )

    return handler
