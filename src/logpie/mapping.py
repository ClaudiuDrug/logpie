# -*- coding: UTF-8 -*-

from collections import namedtuple

__all__ = [
    "Level", "Frame", "Traceback", "Row"
]

Level: namedtuple = namedtuple(
    "Level",
    [
        "name",
        "value"
    ]
)

Frame: namedtuple = namedtuple(
    "Frame",
    [
        "file",
        "line",
        "code"
    ]
)

Traceback: namedtuple = namedtuple(
    "Traceback",
    [
        "file",
        "line",
        "code",
        "message"
    ]
)

Row: namedtuple = namedtuple(
    "Row",
    [
        "timestamp",
        "name",
        "level",
        "source",
        "message",
        "extra"
    ]
)
