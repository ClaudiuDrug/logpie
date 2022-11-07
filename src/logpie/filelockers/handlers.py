# -*- coding: UTF-8 -*-

from abc import ABC, abstractmethod
from typing import IO

from .constants import LOCK
from .core import lock, unlock
from .exceptions import LockFlagsError


class AbstractLockHandler(ABC):
    """Base lock handler."""

    def __init__(self, *args, **kwargs):
        self._args, self._kwargs = args, kwargs

    def __enter__(self) -> IO:
        if hasattr(self, "_handle") is False:
            self._handle = self.acquire(*self._args, **self._kwargs)
        return self._handle

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, "_handle") is True:
            self.release(self._handle)
            del self._handle

    def __delete__(self, instance):
        instance.release()

    @abstractmethod
    def acquire(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def release(self, *args, **kwargs):
        raise NotImplementedError


class FileLocker(AbstractLockHandler):

    __flags__: dict = {
        "w": LOCK.EX,
        "a": LOCK.EX,
        "x": LOCK.EX,
        "r": LOCK.SH,
    }

    def acquire(self, handle: IO, flags: int = None) -> IO:
        """
        Acquire a lock on the given `handle`.
        If `flags` are not provided it will try to guess
        them by reading the handle's operating mode.

        :param handle: The file handle.
        :param flags: The flags to be used to lock the handle.
        :return: The newly locked handle.
        """

        mode = self._get_mode(handle)

        if flags is None:
            flags = self.__flags__.get(mode)

        elif (mode == "w") and (flags in (LOCK.SH | LOCK.NB)):
            raise LockFlagsError(f"Wrong flags used on this operating mode of the handle (`{mode}`)!")

        lock(handle, flags)
        return handle

    def release(self, handle: IO):
        """Unlock the file handle."""
        unlock(handle)

    @staticmethod
    def _get_mode(handle: IO) -> str:
        """Return the handle's operating mode."""
        mode = handle.mode
        return mode.strip("tb+")
