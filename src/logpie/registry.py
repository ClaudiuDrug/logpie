# -*- coding: UTF-8 -*-

from abc import ABC
from typing import Any, Type

from .exceptions import RegistryKeyError, DuplicateKeyError, MissingKeyError


class AbstractHandler(ABC):

    __registry__: dict = {}
    __mutable__: bool = True

    @classmethod
    def register(cls, key: str):
        def decorator(value: Type):
            cls._set_entry(key, value)
            return value
        return decorator

    @classmethod
    def unregister(cls, key: str):
        cls._del_entry(key)

    @classmethod
    def get(cls, key: str, *args, **kwargs) -> Any:
        return cls._instance(
            cls._get_entry(key), *args, **kwargs
        )

    @classmethod
    def _get_entry(cls, key: str) -> Type:
        if key not in cls.__registry__:
            raise MissingKeyError(
                f"Cannot find any entry with key '{key}'!"
            )
        return cls.__registry__.get(key)

    @classmethod
    def _set_entry(cls, key: str, value: Type):

        if (len(key) == 0) or (key is None):
            raise RegistryKeyError(
                f"Cannot register class '{value.__name__}' "
                f"with an empty registry key '{key}'!"
            )

        if (cls.__mutable__ is False) and (key in cls.__registry__):
            raise DuplicateKeyError(
                f"Duplicate key '{key}' found with class '{cls._get_entry(key).__name__}'!"
            )

        cls.__registry__.update({key: value})

    @classmethod
    def _del_entry(cls, key: str):
        if key not in cls.__registry__:
            raise MissingKeyError(
                f"Cannot find any entry with key '{key}'!"
            )
        cls.__registry__.pop(key)

    @classmethod
    def _instance(cls, value: Type, *args, **kwargs) -> Any:
        return value(*args, **kwargs)


class ClassRegistry(AbstractHandler):
    """
    Immutable class registry handler.

    Example:
        from .registry import ClassRegistry

        @ClassRegistry.register("some_name")
        class SomeClass(object):
            def __init__(self, var: str):
                self.var = var

        some_class = ClassRegistry.get("some_name", "var_value")
        print(some_class.var)
    """

    __registry__: dict = {}
    __mutable__: bool = False
