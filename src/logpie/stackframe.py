# -*- coding: UTF-8 -*-

from os.path import basename
from sys import exc_info, _getframe as get_frame
from typing import Union

from .mapping import Traceback, Frame

__all__ = [
    "get_traceback", "get_caller", "get_file", "get_code", "get_message"
]


def get_traceback(exception: Union[BaseException, tuple, bool]) -> Traceback:
    """
    Get information about the most recent exception caught by an except clause
    in the current stack frame or in an older stack frame.

    :param exception: If enabled it will return info about the most recent exception caught.
    :return: The file name, line number, name of code object and traceback message.
    :raise AttributeError: If exception is enabled and no traceback is found.
    """

    if isinstance(exception, BaseException):
        exception = (type(exception), exception, exception.__traceback__)
    elif not isinstance(exception, tuple):
        exception = exc_info()

    try:
        tb_frame = exception[-1].tb_frame
    except AttributeError:
        raise
    else:
        return Traceback(
            file=get_file(tb_frame),
            line=exception[-1].tb_lineno,
            code=get_code(tb_frame),
            message=get_message(exception),
        )


def get_caller(depth: int) -> Frame:
    """
    Get information about the frame object from the call stack.

    :param depth: Number of calls below the top of the stack.
    :return: The file name, line number and name of code object.
    """
    try:
        frame = get_frame(depth)
    except ValueError:
        depth -= 1
        return get_caller(depth)
    else:
        return Frame(
            file=get_file(frame),
            line=frame.f_lineno,
            code=get_code(frame),
        )


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


def get_message(exception: tuple) -> str:
    """Extract the traceback message from the given `exception`."""
    return f"{exception[0].__name__}({exception[1]})"
