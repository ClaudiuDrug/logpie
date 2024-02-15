# -*- coding: UTF-8 -*-

from abc import abstractmethod
from atexit import register
from datetime import datetime, date
from io import TextIOWrapper
from os import fsync
from os.path import join, exists, split, splitext
from string import Template
from sys import stdout
from threading import RLock
from typing import Union, Tuple, Dict, TextIO, Mapping, IO

from .constants import *
from .mapping import Level, Traceback, Frame, Row
from .stackframe import get_caller, get_traceback
from .utils import get_local, get_type, check_tree, get_size

__all__ = [
    "Formatter", "BaseHandler", "Handler", "StreamHandler", "FileHandler",
    "RowFactory", "MetaSingleton", "BaseLogger", "Logger"
]


class Formatter:

    @staticmethod
    def _attach_info(message: str, source: Traceback) -> str:
        if isinstance(source, Traceback):
            return f"{message} (Exception: {source.message})"
        return message

    def __init__(self, row: str = ROW, time: str = TIME, stack: str = STACK):
        self._row = Template(row)
        self._time = time
        self._stack = Template(stack)

    def as_string(self, row: Row) -> str:
        timestamp: str = row.timestamp.strftime(self._time)
        source: str = self._stack.safe_substitute(
            file=row.source.file,
            line=row.source.line,
            code=row.source.code,
        )
        message: str = self._attach_info(row.message, row.source)
        return self._row.safe_substitute(
            timestamp=timestamp,
            name=row.name,
            level=row.level.name,
            source=source,
            message=message,
            **row.extra
        )


class BaseHandler:

    @staticmethod
    def _dispatch_rlock(name: str = NAME) -> RLock:
        if name not in RLOCKS:
            instance: RLock = RLock()
            RLOCKS[name] = instance
        return RLOCKS.get(name)


class Handler(BaseHandler):

    _formatter: Formatter = Formatter()

    @staticmethod
    def _check_formatter(formatter: Formatter) -> Formatter:
        if not isinstance(formatter, Formatter):
            raise TypeError(
                f"Argument 'formatter' must be of type"
                f" 'Formatter' not '{get_type(formatter)}'!"
            )
        return formatter

    def __init__(self, formatter: Formatter = None):
        self._thread_lock: RLock = self._dispatch_rlock(str(self))

        if formatter is not None:
            self._formatter = self._check_formatter(formatter)

    @property
    def formatter(self) -> Formatter:
        with self._thread_lock:
            return self._formatter

    @formatter.setter
    def formatter(self, value: Formatter):
        self._thread_lock.acquire()
        try:
            self._check_formatter(value)
        except TypeError:
            raise
        else:
            self._formatter = value
        finally:
            self._thread_lock.release()

    @abstractmethod
    def write(self, *args, **kwargs):
        raise NotImplementedError(
            f"Method not implemented for handler '{self.__class__.__name__}'!"
        )

    @abstractmethod
    def close(self, *args, **kwargs):
        raise NotImplementedError(
            f"Method not implemented for handler '{self.__class__.__name__}'!"
        )

    def emit(self, row: Row):
        with self._thread_lock:
            msg: str = self._formatter.as_string(row)
            self.write(msg)


class StreamHandler(Handler):

    _handle: TextIO = stdout

    @staticmethod
    def _check_handle(handle: TextIO) -> TextIO:
        if not isinstance(handle, TextIOWrapper):
            raise TypeError(
                f"Argument 'handle' must be of type"
                f" 'TextIO' not '{get_type(handle)}'!"
            )
        return handle

    def __init__(self, formatter: Formatter = None, handle: TextIO = None):
        super(StreamHandler, self).__init__(formatter)

        if handle is not None:
            self._handle = self._check_handle(handle)

    @property
    def handle(self) -> TextIO:
        with self._thread_lock:
            return self._handle

    @handle.setter
    def handle(self, value: TextIO):
        self._thread_lock.acquire()
        try:
            self._check_handle(value)
        except TypeError:
            raise
        else:
            self._handle = value
        finally:
            self._thread_lock.release()

    def write(self, message: str):
        self._handle.write(f"{message}\n")
        self._handle.flush()

    def close(self):
        """dummy"""


class FileHandler(Handler):
    """Stream handler that writes logs into a file."""

    def __init__(
            self,
            filename: str,
            mode: str = MODE,
            encoding: str = ENCODING,
            *,
            max_size: int = MAX_SIZE,
            cycle: bool = CYCLE,
            chronological: bool = CHRONOLOGICAL,
            date_prefix: bool = DATE_PREFIX,
            date_aware: bool = DATE_AWARE,
            formatter: Formatter = None,
    ):
        """
        Initialize FileStream object.

        :param filename: Name of the file to write logs into.
        :param mode: Mode of file opening.
        :param encoding: Encoding of the file.
        :param max_size: Maximum size of the log file.
        :param cycle: Whether to cycle files when maximum size is reached.
        :param chronological: Whether to sort files chronologically.
        :param date_prefix: Whether to add date prefix to filename.
        :param date_aware: Whether to use date awareness to the log file.
        :param formatter: Formatter object to format the logs.
        """
        super(FileHandler, self).__init__(formatter)

        self._folder, self._filename = split(filename)
        self._basename, self._ext = splitext(self._filename)

        if not len(self._ext) > 0:
            self._ext = ".log"

        if not len(self._folder) > 0:
            self._folder = FOLDER

        self._mode = mode
        self._encoding = encoding
        self._max_size = max_size
        self._cycle = cycle
        self._chronological = chronological
        self._date_prefix = date_prefix
        self._date_aware = date_aware

        self._file_size: int = 0
        self._file_idx: int = 0
        self._file_date: date = date.today()

        self._file_path: str = self._new_file_path()
        self._handle: IO = self._acquire(
            self._file_path,
            self._mode,
            encoding=self._encoding
        )

    def _get_date(self) -> date:
        """Get the date for the log file."""
        if self._date_aware:
            today: date = date.today()

            if today > self._file_date:
                self._file_date = today
                self._file_idx = 0

        return self._file_date

    @check_tree
    def _get_folder(self) -> str:
        """Get the folder for the log file."""
        if self._chronological:
            today: date = self._get_date()
            return join(self._folder, str(today.year), today.strftime("%B").lower())
        return self._folder

    def _get_basename(self) -> str:
        """Get the base name for the log file."""
        if self._date_prefix:
            return f"{self._get_date()}_{self._basename}"
        return self._basename

    def _get_idx(self) -> int:
        """Get the index for the log file."""
        self._file_idx += 1
        return self._file_idx

    def _next_filepath(self) -> str:
        """
        Get the next file path for the log file.

        :return: Next file path for the log file.
        """
        filepath: str = join(self._get_folder(), f"{self._get_basename()}.{self._get_idx()}{self._ext}")
        if exists(filepath) and ("w" not in self._mode):
            return self._next_filepath()
        return filepath

    def _get_file_name(self) -> str:
        """
        Get the file name for the log file.

        :return: File name for the log file.
        """
        if self._date_prefix:
            return f"{self._get_date()}_{self._filename}"
        return self._filename

    def _new_file_path(self) -> str:
        """
        Create a file path for the log file.

        :return: File path for the log file.
        """
        if self._cycle:
            return self._next_filepath()
        return join(self._get_folder(), self._get_file_name())

    def _acquire(self, file: str, *args, **kwargs) -> IO:
        """
        Acquire a new file handle.

        :param file: File to acquire handle for.
        :param args: Additional arguments.
        :param kwargs: Additional keyword arguments.
        :return: Acquired file handle.
        """
        self._thread_lock.acquire()
        try:
            handle: IO = open(file, *args, **kwargs)
        except FileNotFoundError:
            raise
        else:
            self._file_size = handle.tell()
            return handle
        finally:
            self._thread_lock.release()

    def _release(self, handle: IO):
        """
        Release a file handle.

        :param handle: File handle to release.
        """
        with self._thread_lock:
            handle.flush()
            if "r" not in handle.mode:
                fsync(handle.fileno())
            handle.close()

    def close(self):
        """Close the file stream and release the resources."""
        with self._thread_lock:
            if hasattr(self, "_handle"):
                self._release(self._handle)
                del self._handle

    def _cycle_handle(self, message: str):
        """
        Check if the file size has reached the limit and update the file path
        and the handle.

        :param message: the message string to used for size checking.
        """
        if not self._file_size <= self._max_size - get_size(message):
            self.close()
            self._file_path = self._next_filepath()
            self._handle = self._acquire(
                self._file_path,
                self._mode,
                encoding=self._encoding
            )

    def _write(self, message: str):
        """
        Write a log message into the file.

        :param message: Message to be written.
        """
        self._handle.write(f"{message}\n")
        self._handle.flush()

    def write(self, message: str):
        """
        Write a log message into the file.
        If `cycle` is set to `True`, the file handle will be renewed in case
        it reached the size limit.

        :param message: Message to be written.
        """
        if self._cycle:
            self._cycle_handle(message)
            self._write(message)
            self._file_size = self._handle.tell()
        else:
            self._write(message)


class RowFactory:

    @staticmethod
    def _get_frame(exc_info: Union[BaseException, tuple, bool], depth: int) -> Union[Frame, Traceback]:
        """
        Get information about the most recent exception caught by an except clause
        in the current stack frame or in an older stack frame.

        :param exc_info: Information about the most recent exception.
        :param depth: The depth of the stack frame.
        :return: Information about the most recent exception or the caller's stack frame.
        """
        if exc_info:
            try:
                return get_traceback(exc_info)
            except AttributeError:
                pass
        return get_caller(depth)

    @staticmethod
    def _attach_info(message: str, args: tuple) -> str:
        """
        Attach `args` & `traceback` info to `message`.

        :param message: The log message.
        :param args: The arguments for the log message.
        :return: The log message with the arguments and traceback info attached.
        """
        if (len(args) == 1) and isinstance(args[0], Mapping):
            args = args[0]
        try:
            message = message % args
        except (TypeError, KeyError, ValueError):
            message = f"{message} (args: {args})"
        return message

    def build(
            self,
            timestamp: datetime,
            name: str,
            level: Level,
            msg: str,
            args: tuple,
            *,
            exc_info: Union[BaseException, tuple, bool] = False,
            depth: int = 1,
            **extra
    ) -> Row:
        """
        Build a log row.

        :param timestamp: The timestamp of the log row.
        :param name: The name of the logger that emitted the log row.
        :param level: The level of the log row.
        :param msg: The log message.
        :param args: The arguments for the log message.
        :param exc_info: Information about any exception (default is False).
        :param depth: The depth of the stack frame (default is 7).
        :param extra: Any additional information to include in the log row.
        :return: The constructed log row.
        """
        source: Union[Frame, Traceback] = self._get_frame(
            exc_info=exc_info,
            depth=depth
        )

        if len(args) > 0:
            msg: str = self._attach_info(msg, args)

        return Row(
            timestamp=timestamp,
            name=name,
            level=level,
            source=source,
            message=msg,
            extra=extra,
        )


class MetaSingleton(type):
    """
    Singleton metaclass (for non-strict class).
    Restrict object to only one instance per runtime.
    """

    def __call__(
            cls,
            name: str = NAME,
            level: Level = NOTSET,
            handlers: Union[Handler, Tuple[Handler, ...]] = None
    ):
        if name not in INSTANCES:
            instance: BaseLogger = super(MetaSingleton, cls).__call__(name, level, handlers)
            register(instance.close)
            INSTANCES[name] = instance
        return INSTANCES.get(name)


class BaseLogger(BaseHandler, RowFactory, metaclass=MetaSingleton):
    """Base class for all logging handlers."""

    _handlers: Tuple[Handler, ...] = (StreamHandler(),)

    @staticmethod
    def _check_name(value: str) -> str:
        if not isinstance(value, str):
            raise TypeError(
                f"Argument 'name' must be of type 'str'"
                f" not '{get_type(value)}'!"
            )
        if not len(value) > 0:
            raise ValueError(f"Argument 'name' must not be empty!")
        return value

    @staticmethod
    def _check_level(value: Level) -> Level:
        if not isinstance(value, Level):
            raise TypeError(
                f"Argument 'level' must be of type"
                f" 'Level' not '{get_type(value)}'!"
            )
        return value

    @staticmethod
    def _check_handlers(value: Union[Handler, Tuple[Handler, ...]]) -> Tuple[Handler, ...]:
        if not isinstance(value, (Handler, tuple)):
            raise TypeError(
                f"Argument 'handlers' must be of type 'Handler' or"
                f" 'Tuple[Handler, ...]' not '{get_type(value)}'!"
            )
        if isinstance(value, tuple):
            if not all(isinstance(item, Handler) for item in value):
                raise TypeError(
                    "All elements in the tuple must be of type 'Handler'!"
                )
            return tuple(set(value))
        return (value,)

    def __init__(
            self,
            name: str = NAME,
            level: Level = NOTSET,
            handlers: Union[Handler, Tuple[Handler, ...]] = None
    ):
        self._name = self._check_name(name)
        self._level = self._check_level(level)

        if handlers is not None:
            self._handlers = self._check_handlers(handlers)

        self._thread_lock: RLock = self._dispatch_rlock(self._name)
        self._cache: Dict[int, bool] = {}

    @property
    def name(self) -> str:
        return self._name

    @property
    def level(self) -> Level:
        with self._thread_lock:
            return self._level

    @level.setter
    def level(self, level: Level):
        self._thread_lock.acquire()
        try:
            self._level = self._check_level(level)
        except TypeError:
            raise
        else:
            self._reset_cache(level.value)
        finally:
            self._thread_lock.release()

    @property
    def handlers(self) -> Tuple[Handler, ...]:
        with self._thread_lock:
            return self._handlers

    @handlers.setter
    def handlers(self, value: Union[Handler, Tuple[Handler, ...]]):
        self._thread_lock.acquire()
        try:
            self._handlers = self._check_handlers(value)
        except TypeError:
            raise
        finally:
            self._thread_lock.release()

    def add_handler(self, handler: Handler):
        """
        Add a new `handler` to this logger.

        :param handler: The handler to be added.
        """
        self._thread_lock.acquire()
        try:
            handlers = self._check_handlers(handler)
        except TypeError:
            raise
        else:
            if handler not in self._handlers:
                self._handlers = self._handlers + handlers
        finally:
            self._thread_lock.release()

    def remove_handler(self, handler: Handler):
        """
        Remove the given `handler` instance.

        :param handler: The handler to be removed.
        """
        self._thread_lock.acquire()
        try:
            self._check_handlers(handler)
        except TypeError:
            raise
        else:
            handlers: list = list(self._handlers)
            if handler in handlers:
                handlers.remove(handler)
                self._handlers = tuple(handlers)
        finally:
            self._thread_lock.release()

    def has_handlers(self) -> bool:
        """Check if this logger instance has any handlers."""
        with self._thread_lock:
            return len(self._handlers) > 0

    def _reset_cache(self, value: int):
        """
        Clear the cache.

        :param value: The new level value for this logger.
        """
        self._cache.clear()
        if value > NOTSET.value:
            self._cache[value] = True

    def _log(self, level: Level, msg: str, *args, **kwargs):
        """
        Log `msg % args` with severity `level`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:
            self._log(ERROR, "Testing '%s' messages!", "ERROR", exc_info=True)

            or

            self._log(ERROR, "Testing '%(level)s' messages!", {"level": "ERROR"}, exc_info=True)

        :param level: The logging level to be used.
        :param msg: The message to be logged.
        :param args: Optional arguments.
        :param kwargs: optional keyword arguments.
        """
        with self._thread_lock:
            if self._is_allowed(level.value):
                row: Row = self.build(get_local(), self._name, level, msg, args, depth=7, **kwargs)
                self._emit(row)

    def _is_allowed(self, value: int) -> bool:
        """
        Check whether the given level value is allowed before logging the
        message.

        :param value: The integer value of the level to be checked.
        """
        if value not in self._cache:
            self._cache[value] = value >= self._level.value
        return self._cache.get(value)

    def _emit(self, row: Row):
        """
        Emit a row using all handlers.

        :param row: The row to be emitted.
        """
        for handler in self._handlers:
            handler.emit(row)

    def close(self):
        """Close all handlers before exiting."""
        with self._thread_lock:
            for handler in self._handlers:
                handler.close()


class Logger(BaseLogger):

    def debug(self, msg: str, *args, **kwargs):
        """
        Log a `msg % args` with level `DEBUG`.
        To add exception info to the message use the
        `exc_info` keyword argument with a True value.

        Example:
            log.debug("Testing '%s' messages!", "DEBUG", exc_info=True)

            or

            log.debug("Testing '%(level)s' messages!", {"level": "DEBUG"}, exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments.
        :param kwargs: Optional keyword arguments.
        """
        self._log(DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """
        Log a `msg % args` with level `INFO`.
        To add exception info to the message use the
        `exc_info` keyword argument with a True value.

        Example:
            log.info("Testing '%s' messages!", "INFO", exc_info=True)

            or

            log.info("Testing '%(level)s' messages!", {"level": "INFO"}, exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments.
        :param kwargs: Optional keyword arguments.
        """
        self._log(INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """
        Log a `msg % args` with level `WARNING`.
        To add exception info to the message use the
        `exc_info` keyword argument with a True value.

        Example:
            log.warning("Testing '%s' messages!", "WARNING", exc_info=True)

            or

            log.warning("Testing '%(level)s' messages!", {"level": "WARNING"}, exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments.
        :param kwargs: Optional keyword arguments.
        """
        self._log(WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """
        Log a `msg % args` with level `ERROR`.
        To add exception info to the message use the
        `exc_info` keyword argument with a True value.

        Example:
            log.error("Testing '%s' messages!", "ERROR", exc_info=True)

            or

            log.error("Testing '%(level)s' messages!", {"level": "ERROR"}, exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments.
        :param kwargs: Optional keyword arguments.
        """
        self._log(ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """
        Log a `msg % args` with level `CRITICAL`.
        To add exception info to the message use the
        `exc_info` keyword argument with a True value.

        Example:
            log.critical("Testing '%s' messages!", "CRITICAL", exc_info=True)

            or

            log.critical("Testing '%(level)s' messages!", {"level": "CRITICAL"}, exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments.
        :param kwargs: Optional keyword arguments.
        """
        self._log(CRITICAL, msg, *args, **kwargs)
