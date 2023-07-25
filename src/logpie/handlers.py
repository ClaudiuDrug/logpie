# -*- coding: UTF-8 -*-

from abc import ABC, abstractmethod
from atexit import register
from datetime import date, datetime
from os import fsync
from os.path import splitext, split, join, exists
from string import Template
from sys import stdout, stderr
from threading import RLock
from typing import Union, List, Tuple, IO, TextIO, Mapping

from .constants import NAME, ROOT, INSTANCES, RLOCKS, STATE, LEVEL, FMT
from .exceptions import UnknownLevelError, UnknownStateError, UnknownHandlerError, UnknownFormatterError
from .mapping import Frame, Traceback, Row
from .stackframe import get_traceback, get_caller
from .utils import get_type, get_local, check_state, check_tree, get_size_of

__all__ = [
    "Formatter",
    "Handler",
    "StdStream",
    "FileStream",
    "RowFactory",
    "StreamHandler",
    "MetaSingleton",
    "BaseLogger",
    "Logger",
]


def _dispatch_rlock(name: str = NAME) -> RLock:
    """
    Dispatch a thread lock based on a given name.

    If a lock with the provided name doesn't exist, a new one is created and added
    to the global `RLOCKS` dictionary.

    :param name: The name of the lock.
    :return: The lock associated with the provided name.
    """
    if name not in RLOCKS:
        instance: RLock = RLock()
        RLOCKS.update({name: instance})
    return RLOCKS.get(name)


class Formatter(object):
    """
    Log message formatter.

    This class is responsible for formatting log messages.
    """

    def __init__(self, row: str = FMT.ROW, timestamp: str = FMT.TIME, stack: str = FMT.STACK):
        """
        Initialize the formatter with specified templates for `row`,
        `timestamp` and `stack`.

        :param row: The template for a row.
        :param timestamp: The template for a timestamp.
        :param stack: The template for a stack.
        """
        self._row = Template(row)
        self._timestamp = timestamp
        self._stack = Template(stack)

    def as_string(self, row: Row):
        """
        Format a given row into a string based on predefined templates.

        :param row: The row to be formatted.
        :return: The formatted string.
        """
        return self._row.safe_substitute(
            timestamp=row.timestamp.strftime(self._timestamp),
            name=row.name,
            level=row.level.name,
            source=self._stack.safe_substitute(
                file=row.source.file,
                line=row.source.line,
                code=row.source.code,
            ),
            message=self._attach_info(row.message, row.source),
            **row.extra
        )

    @staticmethod
    def _attach_info(message: str, source: Traceback) -> str:
        """
        Attach traceback info to a given `message` if the `source` is
        an instance of Traceback.

        :param message: The message to which traceback info needs to be attached.
        :param source: The source of the traceback.
        :return: The message with the attached traceback info.
        """
        if isinstance(source, Traceback):
            return f"{message} Traceback: {source.message}"
        return message


class Handler(ABC):
    """
    Abstract base class for all stream handlers.

    This class provides the fundamental methods for handling and processing
    logs. Each handler may use a different method for outputting logs
    (e.g., writing to a file or the console), which is defined in the
    `write` method.
    """

    _formatter: Formatter = Formatter()

    @staticmethod
    def _check_formatter(value: Formatter) -> Formatter:
        """
        Check if the provided formatter object is of correct type.

        :param value: Formatter object to check.
        :raises UnknownFormatterError: if the formatter is not of the correct type.
        :return: The formatter if it is of the correct type.
        """
        if not isinstance(value, Formatter):
            raise UnknownFormatterError(
                f"Handler 'formatter' attribute must be of "
                f"type 'Formatter' not '{get_type(value)}'!"
            )
        return value

    def __init__(self, formatter: Formatter = None):
        """
        Initialize the Handler.
        Creates a thread lock object and sets the formatter if it is provided.

        :param formatter: Optional formatter to set for the handler.
        """
        self._thread_lock: RLock = _dispatch_rlock(name=str(self))

        if formatter is not None:
            self.set_formatter(formatter)

    def set_formatter(self, value: Formatter):
        """
        Set the formatter for the Handler.

        This method acquires the thread lock to prevent other threads from
        manipulating the formatter during the update.

        :param value: Formatter object to set.
        :raises UnknownFormatterError: if the formatter is not of the correct type.
        """
        self._thread_lock.acquire()
        try:
            self._formatter: Formatter = self._check_formatter(value)
        except UnknownFormatterError:
            raise
        finally:
            self._thread_lock.release()

    @abstractmethod
    def write(self, *args, **kwargs):
        """
        Abstract method for writing to the stream.
        This method should be implemented by all subclasses.

        :raises NotImplementedError: if the method is not implemented.
        """
        raise NotImplementedError

    def emit(self, row: Row):
        """
        Emit a log row.

        This method formats the row and then writes it to the stream.
        It acquires the thread lock to ensure that no other log messages are written
        to the stream while it is writing.

        :param row: Row object representing the log record.
        """
        with self._thread_lock:
            msg: str = self._formatter.as_string(row)
            self.write(msg)


class StdStream(Handler):
    """
    Stream handler that writes logs to the console.

    This class is responsible for taking in logging rows and outputting
    them to the appropriate console output, based on the severity level
    of the log message. For instance, error and critical logs will be
    directed to stderr, while others are directed to stdout.
    """

    _handles: dict = {
        LEVEL.DEBUG: stdout,
        LEVEL.INFO: stdout,
        LEVEL.WARNING: stdout,
        LEVEL.ERROR: stderr,
        LEVEL.CRITICAL: stderr,
    }

    def emit(self, row: Row):
        """
        Emit a log row.

        This method acquires the thread lock, writes the log row formatted as a string
        to the handle associated with the logging level of the row.

        :param row: Row object representing the log record.
        """
        with self._thread_lock:
            self.write(
                handle=self._handles.get(row.level, stdout),
                message=self._formatter.as_string(row)
            )

    def write(self, handle: TextIO, message: str):
        """
        Write the log message to the given handle.

        :param handle: Handle object to write log message.
        :param message: Log message to write.
        """
        handle.write(f"{message}\n")
        handle.flush()


class FileStream(Handler):
    """Stream handler that writes logs into a file."""

    def __init__(
            self,
            filename: str,
            mode: str = "a",
            encoding: str = "UTF-8",
            *,
            folder: str = None,
            max_size: int = (1024 ** 2) * 4,
            cycle: bool = False,
            chronological: bool = False,
            date_prefix: bool = False,
            date_aware: bool = False,
            formatter: Formatter = None,
    ):
        """
        Initialize FileStream object.

        :param filename: Name of the file to write logs into.
        :param mode: Mode of file opening.
        :param encoding: Encoding of the file.
        :param folder: Folder to write logs in.
        :param max_size: Maximum size of the log file.
        :param cycle: Whether to cycle files when maximum size is reached.
        :param chronological: Whether to sort files chronologically.
        :param date_prefix: Whether to add date prefix to filename.
        :param date_aware: Whether to use date awareness to the log file.
        :param formatter: Formatter object to format the logs.
        """
        super(FileStream, self).__init__(formatter)

        if folder is None:
            folder = join(ROOT, "logs")

        self._folder, self._filename = split(filename)
        self._basename, self._ext = splitext(self._filename)

        if not len(self._ext) > 0:
            self._ext = ".log"

        if not len(self._folder) > 0:
            self._folder = folder

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

        self._filepath: str = None
        self._handle: IO = self._new_handle()

    def write(self, message: str):
        """
        Write a log message into the file.

        :param message: Message to be written.
        """
        msg_size: int = get_size_of(message)
        handle: IO = self._get_handle(msg_size)
        handle.write(f"{message}\n")
        handle.flush()
        self._file_size = handle.tell()

    def _get_handle(self, msg_size: int) -> IO:
        """
        Get the file handle for the log file.

        :param msg_size: Size of the log message.
        :return: File handle for the log file.
        """
        if self._cycle:
            if not self._file_size <= self._max_size - msg_size:
                self.close()
                self._handle = self._new_handle()
        return self._handle

    def _new_handle(self) -> IO:
        """
        Create a new file handle.

        :return: New file handle.
        """
        file_path: str = self._get_filepath()
        handle: IO = self._acquire(file_path, self._mode, encoding=self._encoding)
        self._file_size = handle.tell()
        return handle

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
            return open(file, *args, **kwargs)
        except FileNotFoundError:
            raise
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

    def _get_filepath(self) -> str:
        """
        Get the file path for the log file.

        :return: File path for the log file.
        """
        if self._filepath is None:
            self._filepath = self._make_filepath()
        elif self._cycle:
            self._filepath = self._next_filepath()
        return self._filepath

    def _make_filepath(self) -> str:
        """
        Create a file path for the log file.

        :return: File path for the log file.
        """
        if self._cycle:
            return self._next_filepath()
        return join(self._get_folder(), self._get_filename())

    def _next_filepath(self) -> str:
        """
        Get the next file path for the log file.

        :return: Next file path for the log file.
        """
        filepath: str = join(self._get_folder(), f"{self._get_basename()}.{self._get_idx()}{self._ext}")
        if exists(filepath) and ("w" not in self._mode):
            return self._next_filepath()
        return filepath

    @check_tree
    def _get_folder(self) -> str:
        """
        Get the folder for the log file.

        :return: Folder for the log file.
        """
        if self._chronological:
            today: date = self._get_date()
            return join(self._folder, str(today.year), today.strftime("%B").lower())
        return self._folder

    def _get_basename(self) -> str:
        """
        Get the base name for the log file.

        :return: Base name for the log file.
        """
        if self._date_prefix:
            return f"{self._get_date()}_{self._basename}"
        return self._basename

    def _get_idx(self) -> int:
        """
        Get the index for the log file.

        :return: Index for the log file.
        """
        self._file_idx += 1
        return self._file_idx

    def _get_filename(self) -> str:
        """
        Get the file name for the log file.

        :return: File name for the log file.
        """
        if self._date_prefix:
            return f"{self._get_date()}_{self._filename}"
        return self._filename

    def _get_date(self) -> date:
        """
        Get the date for the log file.

        :return: Date for the log file.
        """
        if self._date_aware:
            today: date = date.today()

            if today > self._file_date:
                self._file_date = today
                self._file_idx = 0

        return self._file_date


class RowFactory(object):
    """A factory class for building logging rows."""

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
        except TypeError:
            message = f"{message} (args: {args})"
        return message

    def build(
            self,
            timestamp: datetime,
            name: str,
            level: LEVEL,
            msg: str,
            args: tuple,
            *,
            exc_info: Union[BaseException, tuple, bool] = False,
            depth: int = 7,
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
        row: Row = Row(
            timestamp=timestamp,
            name=name,
            level=level,
            source=source,
            message=self._attach_info(msg, args),
            extra=extra,
        )
        return row


class StreamHandler(object):
    """
    A log stream handler that manages and delegates logging to multiple handlers.
    """

    _default: StdStream = StdStream()
    _handlers: List[Handler] = []

    @staticmethod
    def _check_handler(handler: Handler) -> Handler:
        """
        Check if the provided value is a valid handler.
        :param handler: The value to be checked.
        :return: The provided value if it is a valid handler.
        :raises UnknownHandlerError: If the provided value is not a valid handler.
        """
        if not isinstance(handler, Handler):
            raise UnknownHandlerError(
                f"Stream 'handler' must be of "
                f"type 'Handler' not '{get_type(handler)}'!"
            )
        return handler

    def __init__(self, handlers: Union[Handler, List[Handler], Tuple[Handler]]):
        """
        Initialize a StreamHandler instance.
        :param handlers: A handler or a list/tuple of handlers for the logger.
        """
        self.set_handlers(handlers)

    def set_handlers(self, value: Union[Handler, List[Handler], Tuple[Handler]]):
        """
        Set the handlers of the logger.
        :param value: A handler or a list/tuple of handlers for the logger.
        """
        if value is not None:
            self._handlers: List[Handler] = self._check_handlers(value)

    def del_handlers(self):
        """Delete the handlers of the logger."""
        if self._has_handlers():
            self._handlers.clear()

    def add_handler(self, value: Handler):
        """
        Add a handler to the logger.
        :param value: The handler to be added to the logger.
        """
        self._check_handler(value)
        if value not in self._handlers:
            self._handlers.append(value)

    def remove_handler(self, value: Handler):
        """
        Remove a handler from the logger.
        :param value: The handler to be removed from the logger.
        """
        if value in self._handlers:
            self._handlers.remove(value)

    def emit(self, row: Row):
        """
        Emit a log record using the handlers.
        If no handler was assigned the :class:`StdStream` default handler will
        be used.
        :param row: The log record to emit.
        """
        if not self._has_handlers():
            self._default.emit(row)
        else:
            for handler in self._handlers:
                handler.emit(row)

    def close(self):
        """
        Close the handlers of the logger and release the resources.
        """
        for handler in self._handlers:
            if hasattr(handler, "close"):
                handler.close()
            self._handlers.remove(handler)

    def _check_handlers(self, handlers: Union[Handler, List[Handler], Tuple[Handler]]) -> List[Handler]:
        """
        Check if the provided value(s) are valid handlers.
        :param handlers: The value(s) to be checked.
        :return: The provided value(s) if they are valid handlers.
        :raises UnknownHandlerError: If the provided value(s) are not valid handlers.
        """
        if isinstance(handlers, Handler):
            return [handlers]
        elif isinstance(handlers, (list, tuple)):
            return [self._check_handler(handler) for handler in handlers]
        else:
            raise UnknownHandlerError(
                f"Stream 'handlers' attribute must be of type 'Handler', "
                f"'List[Handler]' or 'Tuple[Handler]' not '{get_type(handlers)}'!"
            )

    def _has_handlers(self) -> bool:
        """
        Check if there are any handlers.
        :return: Boolean value indicating whether there are any handlers.
        """
        return len(self._handlers) > 0


class MetaSingleton(type):
    """
    Singleton metaclass (for non-strict class).
    Restrict object to only one instance per runtime.
    """

    def __call__(
            cls,
            name: str = NAME,
            level: LEVEL = LEVEL.NOTSET,
            state: STATE = STATE.ON,
            handlers: Union[Handler, List[Handler], Tuple[Handler]] = None
    ):
        if name not in INSTANCES:
            instance: BaseLogger = super(MetaSingleton, cls).__call__(name, level, state, handlers)
            INSTANCES.update({name: instance})
        return INSTANCES.get(name)


class BaseLogger(object):
    """
    BaseLogger class - serves as the basic logging handler.
    """

    @staticmethod
    def _check_name(value: str) -> str:
        """
        Check if the provided value is a valid name for the logger.
        :param value: The value to be checked.
        :return: The provided value if it is a valid name.
        :raises TypeError: If the provided value is not a string.
        :raises ValueError: If the provided value is an empty string.
        """
        if not isinstance(value, str):
            raise TypeError(
                f"Logger 'name' attribute must be of "
                f"type 'str' not '{get_type(value)}'!"
            )
        if len(value) == 0:
            raise ValueError(
                f"Logger 'name' attribute must be a "
                f"string object with a length greater than '0'!"
            )
        return value

    @staticmethod
    def _check_level(value: LEVEL) -> LEVEL:
        """
        Check if the provided value is a valid logging level.
        :param value: The value to be checked.
        :return: The provided value if it is a valid logging level.
        :raises UnknownLevelError: If the provided value is not a valid logging level.
        """
        if not isinstance(value, LEVEL):
            raise UnknownLevelError(
                f"Logger 'level' attribute must be of "
                f"type 'LEVEL' not '{get_type(value)}'!"
            )
        return value

    @staticmethod
    def _check_state(value: STATE) -> STATE:
        """
        Check if the provided value is a valid logger state.
        :param value: The value to be checked.
        :return: The provided value if it is a valid logger state.
        :raises UnknownStateError: If the provided value is not a valid logger state.
        """
        if not isinstance(value, STATE):
            raise UnknownStateError(
                f"Logger 'state' attribute must be of "
                f"type 'STATE' not '{get_type(value)}'!"
            )
        return value

    def __init__(
            self,
            name: str = NAME,
            level: LEVEL = LEVEL.NOTSET,
            state: STATE = STATE.ON,
            handlers: Union[Handler, List[Handler], Tuple[Handler]] = None
    ):
        """
        If handlers are not provided, a default one will be set.
        :param name: Name of the logger.
        :param level: Logging level of the logger.
        :param state: State of the logger.
        :param handlers: A handler or a list/tuple of handlers for the logger.
        """
        self._name = self._check_name(name)
        self._level = self._check_level(level)
        self._state = self._check_state(state)

        self._thread_lock: RLock = _dispatch_rlock(self._name)

        self._row: RowFactory = RowFactory()
        self._stream: StreamHandler = StreamHandler(handlers)

        # cached allowed levels:
        self._cache: dict = {}

        # execute at exit:
        register(self.close)

    @property
    def name(self) -> str:
        return self._name

    def set_level(self, value: LEVEL):
        """
        Set the level of the logger to `value`.
        :param value: The value to set the level to.
        """
        self._thread_lock.acquire()
        try:
            self._level = self._check_level(value)
        except UnknownLevelError:
            raise
        else:
            self._reset_cache(self._level)
        finally:
            self._thread_lock.release()

    def set_state(self, value: STATE):
        """
        Set the state of the logger to `value`.
        :param value: The value to set the state to.
        """
        self._thread_lock.acquire()
        try:
            self._state = self._check_state(value)
        except UnknownStateError:
            raise
        finally:
            self._thread_lock.release()

    def set_handlers(self, value: Union[Handler, List[Handler], Tuple[Handler]]):
        """
        Set the handlers of the logger to `value`.
        :param value: A handler or a list/tuple of handlers for the logger.
        """
        self._thread_lock.acquire()
        try:
            self._stream.set_handlers(value)
        except UnknownHandlerError:
            raise
        finally:
            self._thread_lock.release()

    def del_handlers(self):
        """Delete the handlers of the logger."""
        with self._thread_lock:
            self._stream.del_handlers()

    def add_handler(self, value: Handler):
        """
        Add a handler to the logger.
        :param value: The handler to add to the logger.
        """
        self._thread_lock.acquire()
        try:
            self._stream.add_handler(value)
        except UnknownHandlerError:
            raise
        finally:
            self._thread_lock.release()

    def remove_handler(self, value: Handler):
        """
        Remove a handler from the logger.
        :param value: The handler to remove from the logger.
        """
        with self._thread_lock:
            self._stream.remove_handler(value)

    def is_enabled(self) -> bool:
        """
        Check if the logger is enabled.
        :return: Boolean value indicating whether the logger is enabled.
        """
        with self._thread_lock:
            return self._state.value

    @check_state
    def log(self, level: LEVEL, msg: str, *args, **kwargs):
        """
        Log a message with `msg % args` with level `level`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:

            log(LEVEL.ERROR, "Testing '%s' messages!", "ERROR", exc_info=True)

        :param level: The logging level to be used.
        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: optional keyword arguments.
        """
        self._thread_lock.acquire()
        try:
            self._check_level(level)
        except UnknownLevelError:
            raise
        else:
            if self._is_allowed(level):
                self._log(get_local(), level, msg, args, **kwargs)
        finally:
            self._thread_lock.release()

    def _is_allowed(self, level: LEVEL) -> bool:
        """
        Check if a logging level is allowed.
        :param level: The logging level to check.
        :return: Boolean value indicating whether the level is allowed.
        """
        with self._thread_lock:
            if level not in self._cache:
                self._cache.update({level: level >= self._level})
            return self._cache.get(level)

    def _log(self, timestamp: datetime, level: LEVEL, msg: str, args: tuple, **kwargs):
        """
        Record a log.
        :param timestamp: The timestamp of the log.
        :param level: The level of the log.
        :param msg: The message to be logged.
        :param args: Additional arguments to format the message.
        :param kwargs: Additional keyword arguments to format the message.
        """
        with self._thread_lock:
            row: Row = self._row.build(timestamp, self._name, level, msg, args, **kwargs)
            self._stream.emit(row)

    def _reset_cache(self, level: LEVEL):
        """
        Reset the cache.
        :param level: The level to set the cache to.
        """
        self._cache.clear()
        if level > LEVEL.NOTSET:
            self._cache.update({level: True})

    def close(self):
        """
        Close the handlers of this logger and release the resources.
        """
        with self._thread_lock:
            self._stream.close()


class Logger(BaseLogger, metaclass=MetaSingleton):
    """Main logging handler."""

    def debug(self, msg: str, *args, **kwargs):
        """
        Log a message with `msg % args` with level `DEBUG`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:

            log.debug("Testing '%s' messages!", "DEBUG", exc_info=True)

            or

            log.debug("Testing '%(level)s' messages!", {"level": "DEBUG"}, exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: optional keyword arguments.
        """
        self.log(LEVEL.DEBUG, msg, *args, **kwargs)

    def info(self, msg: str, *args, **kwargs):
        """
        Log a message with `msg % args` with level `INFO`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:

            log.info("Testing '%s' messages!", "INFO", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: optional keyword arguments.
        """
        self.log(LEVEL.INFO, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs):
        """
        Log a message with `msg % args` with level `WARNING`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:

            log.warning("Testing '%s' messages!", "WARNING", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: optional keyword arguments.
        """
        self.log(LEVEL.WARNING, msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs):
        """
        Log a message with `msg % args` with level `ERROR`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:

            log.error("Testing '%s' messages!", "ERROR", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: optional keyword arguments.
        """
        self.log(LEVEL.ERROR, msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """
        Just a more convenient way of logging
        an `ERROR` message with `exc_info=True`.

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: optional keyword arguments.
        """
        if "exc_info" not in kwargs:
            kwargs.update(exc_info=True)
        self.log(LEVEL.ERROR, msg, *args, **kwargs)

    def critical(self, msg: str, *args, **kwargs):
        """
        Log a message with `msg % args` with level `CRITICAL`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:

            log.critical("Testing '%s' messages!", "CRITICAL", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: optional keyword arguments.
        """
        self.log(LEVEL.CRITICAL, msg, *args, **kwargs)
