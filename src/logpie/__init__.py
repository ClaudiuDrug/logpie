# -*- coding: UTF-8 -*-

from .constants import INSTANCES, MODULE
from .handlers import Logger


def get_logger(**kwargs):
    name: str = kwargs.pop('name', MODULE.__name__)

    return _get_logger(
        name=name,
        **kwargs
    )


def _get_logger(name: str, **kwargs):
    name: str = f"{name}.{Logger.__name__}"

    if name not in INSTANCES:
        # a strong reference to the object is required.
        instance = Logger(**kwargs)
        INSTANCES[name] = instance
    return INSTANCES[name]


__all__ = ["Logger", "get_logger"]
