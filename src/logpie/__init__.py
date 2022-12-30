# -*- coding: UTF-8 -*-

from .constants import LOGGERS
from .handlers import Logger


def get_logger(name: str = "logpie", **kwargs) -> Logger:
    if name not in LOGGERS:
        # a strong reference is required
        instance = Logger(name, **kwargs)
        LOGGERS[name] = instance
    return LOGGERS[name]


__all__ = ["Logger", "get_logger"]
