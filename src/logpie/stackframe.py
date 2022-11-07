# -*- coding: UTF-8 -*-

from os.path import basename
from sys import exc_info, _getframe as get_frame
from typing import Union

from .constants import FRAME


def get_traceback(exception: Union[BaseException, tuple, bool]) -> FRAME:
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
        return FRAME(
            file=get_file(tb_frame),
            line=exception[-1].tb_lineno,
            code=get_code(tb_frame),
            traceback=f"{exception[0].__name__}({exception[1]})",
        )


def get_caller(depth: int) -> FRAME:
    """
    Get information about the frame object from the call stack.

    :param depth: Number of calls below the top of the stack.
    :return: The file name, line number and name of code object.
    """
    try:
        frame = get_frame(depth)
    except ValueError:
        raise
    else:
        return FRAME(
            file=get_file(frame),
            line=frame.f_lineno,
            code=get_code(frame),
            traceback=None,
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
