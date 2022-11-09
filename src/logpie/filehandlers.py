# -*- coding: UTF-8 -*-

from abc import ABC, abstractmethod
from os import fsync
from threading import RLock
from typing import IO, AnyStr, List, TextIO, BinaryIO, Union, Optional, Any
from weakref import WeakValueDictionary

from .filelockers import FileLocker


class AbstractFileHandler(ABC):
    """Base abstract handler for all context-manager classes in this module."""

    __locks__ = WeakValueDictionary()

    def __init__(self, file: str, *args, **kwargs):
        self._file, self._args, self._kwargs = file, args, kwargs
        self._thread_lock = self._dispatch(self._file)

    @property
    def mode(self) -> str:
        return self._handle.mode

    @property
    def name(self) -> str:
        return self._handle.name

    @property
    def closed(self) -> bool:
        return self._handle.closed

    @property
    def buffer(self) -> BinaryIO:
        if hasattr(self._handle, "buffer"):
            return self._handle.buffer

    @property
    def encoding(self) -> str:
        if hasattr(self._handle, "encoding"):
            return self._handle.encoding

    @property
    def errors(self) -> Optional[str]:
        if hasattr(self, "errors"):
            return self._handle.errors

    # noinspection PyTypeChecker
    @property
    def line_buffering(self) -> bool:
        if hasattr(self._handle, "line_buffering"):
            return self._handle.line_buffering

    @property
    def newlines(self) -> Any:
        if hasattr(self._handle, "newlines"):
            return self._handle.newlines

    def fileno(self) -> int:
        return self._handle.fileno()

    def flush(self):
        self._handle.flush()

    def isatty(self) -> bool:
        return self._handle.isatty()

    def read(self, n: int = -1) -> AnyStr:
        return self._handle.read(n)

    def readable(self) -> bool:
        return self._handle.readable()

    def readline(self, limit: int = -1) -> AnyStr:
        return self._handle.readline(limit)

    def readlines(self, hint: int = -1) -> List[AnyStr]:
        return self._handle.readlines(hint)

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._handle.seek(offset, whence)

    def seekable(self) -> bool:
        return self._handle.seekable()

    def tell(self) -> int:
        return self._handle.tell()

    def truncate(self, size: int = None) -> int:
        return self._handle.truncate(size)

    def writable(self) -> bool:
        return self._handle.writable()

    def write(self, string: AnyStr) -> int:
        return self._handle.write(string)

    def writelines(self, lines: List[AnyStr]) -> None:
        self._handle.writelines(lines)

    def close(self):
        with self._thread_lock:
            if hasattr(self, "_handle"):
                self._release(self._handle)
                del self._handle

    def _dispatch(self, name: str) -> RLock:
        if name not in self.__locks__:
            instance = RLock()
            self.__locks__.update({name: instance})
        return self.__locks__.get(name)

    def __enter__(self) -> Union[IO, BinaryIO, TextIO]:
        self._thread_lock.acquire()
        try:
            if not hasattr(self, "_handle"):
                self._handle = self._acquire(self._file, *self._args, **self._kwargs)
        except FileNotFoundError:
            self._thread_lock.release()
            raise
        else:
            return self._handle

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, "_handle"):
            self._release(self._handle)
            del self._handle
        self._thread_lock.release()

    @abstractmethod
    def _acquire(self, *args, **kwargs) -> Union[IO, BinaryIO, TextIO]:
        raise NotImplementedError

    @abstractmethod
    def _release(self, *args, **kwargs):
        raise NotImplementedError


class FileHandler(AbstractFileHandler):
    """Simple handler with thread & file lock management."""

    def __init__(self, *args, **kwargs):
        super(FileHandler, self).__init__(*args, **kwargs)

        self._file_lock = FileLocker()

        self._thread_lock.acquire()
        try:
            if not hasattr(self, "_handle"):
                self._handle = self._acquire(*args, **kwargs)
        except FileNotFoundError:
            raise
        finally:
            self._thread_lock.release()

    def _acquire(self, *args, **kwargs) -> Union[IO, BinaryIO, TextIO]:
        """Returns a new locked file handle."""
        self._thread_lock.acquire()
        try:
            handle = open(*args, **kwargs)
        except FileNotFoundError:
            raise
        else:
            return self._file_lock.acquire(handle)
        finally:
            self._thread_lock.release()

    def _release(self, handle: Union[IO, BinaryIO, TextIO]):
        """Close the file handle and release the resources."""
        with self._thread_lock:
            handle.flush()
            if "r" not in handle.mode:
                fsync(handle.fileno())
            self._file_lock.release(handle)
            handle.close()
