# -*- coding: UTF-8 -*-

from datetime import datetime, timezone
from os.path import basename
from sys import exc_info, _getframe as get_frame
from typing import Union, Generator
from zipfile import ZipFile

from .constants import TRACEBACK, FRAME


def get_traceback(exception: Union[BaseException, tuple, bool]) -> TRACEBACK:
    """
    Get information about the most recent exception caught by an except clause
    in the current stack frame or in an older stack frame.

    :param exception: If enabled it will return info about the most recent exception caught.
    :return: The file name, line number, name of code object and traceback message.
    :raise AttributeError: If exception is enabled and no traceback is found.
    """

    if isinstance(exception, BaseException) is True:
        exception = (type(exception), exception, exception.__traceback__)
    elif isinstance(exception, tuple) is False:
        exception = exc_info()

    try:
        f_lineno = exception[-1].tb_lineno
        tb_frame = exception[-1].tb_frame
    except AttributeError:
        raise
    else:
        return TRACEBACK(
            file=get_file(tb_frame),
            line=f_lineno,
            code=get_code(tb_frame),
            message=f"{exception[0].__name__}({exception[1]})"
        )


def get_caller(depth: int = 0) -> FRAME:
    """
    Get information about the frame object from the call stack.

    :param depth: Number of calls below the top of the stack.
    :return: The file name, line number and name of code object.
    """
    frame = get_frame(depth)
    return FRAME(file=get_file(frame), line=get_line(frame), code=get_code(frame))


def get_level(depth: int = 3) -> str:
    """Log method (a.k.a. `LEVEL`) name getter."""
    return get_frame(depth).f_code.co_name.upper()


def get_file(frame) -> str:
    """Frame file name getter."""
    return basename(frame.f_code.co_filename)


def get_code(frame) -> str:
    """Frame object name getter."""
    try:
        co_class = frame.f_locals["self"].__class__.__name__
    except KeyError:
        return frame.f_code.co_name
    else:
        return f"{co_class}.{frame.f_code.co_name}"


def get_line(frame) -> int:
    """Frame line number getter."""
    return frame.f_lineno


def get_timestamp(fmt: str = "%Y-%m-%d %H:%M:%S.%f") -> str:
    """:returns: an aware localized and formatted `datetime` string object."""
    local = get_local()
    return local.strftime(fmt)


def get_local() -> datetime:
    """:returns: an aware localized datetime object."""
    utc = get_utc()
    return utc.astimezone()


def get_utc() -> datetime:
    """:returns: UTC `datetime`."""
    return datetime.now(timezone.utc)


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
