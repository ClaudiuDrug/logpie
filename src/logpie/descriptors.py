# -*- coding: UTF-8 -*-

from abc import ABC
from typing import Union

from cfgpie import get_config, CfgParser


class Descriptor(ABC):

    def __set_name__(self, owner, name):
        self._owner = owner
        self._name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self._name)

    def __set__(self, instance, value):
        instance.__dict__.update({self._name: value})

    def __delete__(self, instance):
        if self._name in instance.__dict__:
            instance.__dict__.pop(self._name)


class Configuration(Descriptor):

    @staticmethod
    def _check_config(instance: Union[CfgParser, str]) -> CfgParser:
        if not isinstance(instance, (CfgParser, str)):
            raise TypeError(
                f"Config parameter must be of type "
                f"'CfgParser' or 'str' not '{type(instance).__name__}'!"
            )

        if isinstance(instance, str):
            return get_config(instance)

        return instance

    def __set__(self, instance, value):
        super(Configuration, self).__set__(
            instance,
            self._check_config(value)
        )
