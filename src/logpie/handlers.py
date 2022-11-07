# -*- coding: UTF-8 -*-

from __future__ import annotations

from abc import ABC, abstractmethod
from atexit import register
from collections.abc import Mapping
from dataclasses import dataclass, make_dataclass, asdict, field
from datetime import date, datetime
from os.path import join, exists
from string import Template
from sys import stdout, stderr
from typing import List, TextIO, Union

from cfgpie import get_config, CfgParser
from colorpie import Style4Bit

from .constants import (
    THREAD_LOCKS,
    REGEX,
    FRAME,
    HANDLERS,
    FILE_MODES,
    FILESTREAM,
    FORMATTING,
    LEVELS,
    STRKEYS,
    INTKEYS,
    BACKUP
)
from .exceptions import UnknownLevelError, UnknownModeError
from .filehandlers import FileHandler
from .registry import ClassRegistry
from .stackframe import get_traceback, get_caller
from .utils import update, get_local, get_fields, cleanup, dispatch_lock, ensure_tree


@dataclass
class Row(object):
    timestamp: datetime = field(default=None)
    level: str = field(default=None)
    name: str = field(default=None)
    source: FRAME = field(default=None)
    message: str = field(default=None)

    def as_dict(self) -> dict:
        return asdict(self)


class AbstractHandler(ABC):
    """Base abstract handler."""

    __shared__: dict = {}

    @staticmethod
    def _check_config(instance: Union[CfgParser, str]) -> CfgParser:
        if not isinstance(instance, (CfgParser, str)):
            raise TypeError(
                f"'instance' must be of type 'CfgParser' or 'int' not '{type(instance).__name__}'!"
            )

        if isinstance(instance, str):
            return get_config(instance)

        return instance

    def __init__(self, name: str, **kwargs):
        self._name = name
        self._lock = dispatch_lock(name, THREAD_LOCKS)
        self.set_config(**kwargs)

    @property
    def name(self):
        return self._name

    @property
    def cfg(self) -> CfgParser:
        if self._name not in self.__shared__:
            self._set_config(f"logpie.{self._name}")
            self.cfg.read_dict(
                dictionary={"LOGGER": BACKUP.copy()},
                source="<backup>"
            )
        return self.__shared__.get(self._name)

    def set_config(self, **kwargs):
        self._lock.acquire()
        try:
            if "config" in kwargs:
                self._set_config(kwargs.pop("config"))
        except TypeError:
            raise
        else:
            self._update_config(**kwargs)
        finally:
            self._lock.release()

    def _set_config(self, instance: Union[CfgParser, str]):
        self._lock.acquire()
        try:
            instance: CfgParser = self._check_config(instance)
        except TypeError:
            raise
        else:
            self.__shared__.update({self._name: instance})
        finally:
            self._lock.release()

    def _update_config(self, **kwargs):
        with self._lock:
            if len(kwargs) > 0:
                self.cfg.read_dict(
                    dictionary={"LOGGER": kwargs},
                    source="<update>"
                )


class Formatter(AbstractHandler):

    @property
    def format(self) -> str:
        return self.cfg.get(
            "LOGGER", "format",
            fallback=FORMATTING.FORMAT,
            raw=True
        )

    @property
    def date_fmt(self):
        return self.cfg.get(
            "LOGGER", "date_fmt",
            fallback=FORMATTING.DATE_FMT,
            raw=True
        )

    @property
    def source_fmt(self):
        return self.cfg.get(
            "LOGGER", "source_fmt",
            fallback=FORMATTING.SOURCE_FMT,
            raw=True
        )

    @property
    def template(self) -> Template:
        return Template(self.format)

    def substitute(self, **kwargs) -> str:

        if "timestamp" in kwargs:
            timestamp: datetime = kwargs.pop("timestamp")

            if isinstance(timestamp, datetime):
                kwargs.update(
                    timestamp=timestamp.strftime(self.date_fmt)
                )

        if "source" in kwargs:
            source: FRAME = kwargs.pop("source")

            if isinstance(source, FRAME):
                template: Template = Template(self.source_fmt)
                kwargs.update(
                    source=template.safe_substitute(**source._asdict())
                )

        return self.template.safe_substitute(**kwargs)


class RowFactory(AbstractHandler):
    """Logging row constructor."""

    @staticmethod
    def _get_frame(exc_info: Union[BaseException, tuple, bool], depth: int) -> FRAME:
        """
        Get information about the most recent exception caught by an except clause
        in the current stack frame or in an older stack frame.
        """
        if exc_info:
            try:
                return get_traceback(exc_info)
            except AttributeError:
                pass

        return get_caller(depth)

    @staticmethod
    def _attach_info(message: str, *args, traceback: str = None) -> str:
        """Attach `args` & traceback info to `message` if `frame` is an exception."""

        if (len(args) == 1) and isinstance(args[0], Mapping):
            args = args[0]

        try:
            message = message % args
        except TypeError:
            message = f"{message} args: {args}"

        if traceback is not None:
            return f"{message} Traceback: {traceback}"

        return message

    @property
    def format(self) -> str:
        return self.cfg.get("LOGGER", "format", fallback=FORMATTING.FORMAT, raw=True)

    def build(self, level: int, msg: str, *args, **kwargs) -> Row:
        frame: FRAME = self._get_frame(
            exc_info=kwargs.pop("exc_info", None),
            depth=kwargs.pop("depth", 6)
        )

        row_dict = dict(
            timestamp=kwargs.pop("timestamp", get_local()),
            level=INTKEYS.get(level),
            name=self._name,
            source=frame,
            message=self._attach_info(msg, *args, traceback=frame.traceback),
        )

        if "extra" in kwargs:
            fields: List[str] = get_fields(REGEX, self.format)

            row = make_dataclass(
                "Row",
                fields=[
                    (key, type(value), field(default=value))
                    for key, value in kwargs.pop("extra").items()
                    if (key in fields) and (key not in row_dict.keys())
                ],
                bases=(Row,)
            )

            return row(**row_dict)

        return Row(**row_dict)


class OutputHandler(AbstractHandler):
    """Base abstract handler for stream output classes."""

    def __init__(self, name: str, **kwargs):
        super(OutputHandler, self).__init__(name, **kwargs)
        self._formatter = Formatter(name)

    @abstractmethod
    def write(self, *args, **kwargs):
        raise NotImplementedError

    def emit(self, row: Row):
        self.write(self.format(row))

    def format(self, row: Row) -> str:
        return self._formatter.substitute(**row.as_dict())


@ClassRegistry.register("console")
class StdStream(OutputHandler):
    """Handler used for logging to console."""

    def __init__(self, name: str, **kwargs):
        super(StdStream, self).__init__(name, **kwargs)

        self._warning = Style4Bit(color="yellow")
        self._error = Style4Bit(color="red")

        self._stream = stdout
        self._style = None

    def emit(self, row: Row):
        try:
            level: str = row.level.upper()
        except AttributeError:
            pass
        else:
            self._stream: TextIO = self._get_stream(level)
            self._style: Style4Bit = self._get_style(level)
        super(StdStream, self).emit(row)

    def write(self, record: str):
        """Write the log record to console and flush the handle."""
        record: str = self._attach_style(record)
        self._stream.write(f"{record}\n")
        self._stream.flush()

    @staticmethod
    def _get_stream(level: str) -> TextIO:
        if level in ["ERROR", "CRITICAL"]:
            return stderr
        else:
            return stdout

    def _get_style(self, level: str) -> Style4Bit:
        if level in ["ERROR", "CRITICAL"]:
            return self._error
        elif level == "WARNING":
            return self._warning

    def _attach_style(self, record: str) -> str:
        if self._style is not None:
            return self._style.format(record)
        return record


@ClassRegistry.register("file")
class FileStream(OutputHandler):
    """Handler used for logging to console."""

    @staticmethod
    def _get_date() -> date:
        return get_local().date()

    @staticmethod
    def _file_mode(value: str) -> str:
        if value not in FILE_MODES:
            file_modes = dict(zip(FILE_MODES.values(), FILE_MODES.keys()))
            value = file_modes.get(value)
        return FILE_MODES.get(value)

    def __init__(self, name: str, **kwargs):
        super(FileStream, self).__init__(name, **kwargs)

        self._file_idx: int = 0
        self._file_size: int = 0

        self._file_path = None
        self._folder_path = None

    @property
    def should_cycle(self) -> bool:
        return self.cfg.getboolean(
            "LOGGER", "should_cycle",
            fallback=FILESTREAM.SHOULD_CYCLE
        )

    @property
    def is_structured(self) -> bool:
        return self.cfg.getboolean(
            "LOGGER", "is_structured",
            fallback=FILESTREAM.IS_STRUCTURED
        )

    @property
    def folder(self) -> str:
        return self.cfg.get("LOGGER", "folder", fallback=FILESTREAM.FOLDER)

    @property
    def basename(self) -> str:
        return self.cfg.get(
            "LOGGER", "basename",
            fallback=FILESTREAM.BASENAME
        )

    @property
    def has_date(self) -> bool:
        return self.cfg.getboolean(
            "LOGGER", "has_date",
            fallback=FILESTREAM.HAS_DATE
        )

    @property
    def max_size(self) -> int:
        return self.cfg.getint("LOGGER", "max_size", fallback=FILESTREAM.MAX_SIZE)

    @property
    def file_mode(self) -> str:
        return self.cfg.get("LOGGER", "file_mode", fallback=FILESTREAM.FILE_MODE)

    @property
    def encoding(self) -> str:
        return self.cfg.get("LOGGER", "encoding", fallback=FILESTREAM.ENCODING)

    def write(self, record: str):
        """Write the log record to console and flush the handle."""
        file_path = self.get_file_path()
        mode = self._check_mode(self.file_mode)

        with FileHandler(file_path, mode, encoding=self.encoding) as file_handler:
            file_handler.write(f"{record}\n")
            self._file_size = file_handler.tell()

    def get_file_path(self):
        if self._file_path is None:
            self._file_path: str = self._get_file_path()

        elif not self.should_cycle:
            return self._file_path

        elif not (0 <= self._file_size <= (self.max_size - 512)):
            self._file_path: str = self._get_file_path()

        return self._file_path

    def _get_file_path(self):
        file_path = join(self.get_folder_path(), self._get_file_name())

        if exists(file_path) and self.should_cycle:
            return self._get_file_path()

        return file_path

    def get_folder_path(self):
        if self._folder_path is None:
            self._folder_path = self._get_folder_path()

            ensure_tree(self._folder_path)

        return self._folder_path

    def _get_folder_path(self) -> str:

        if self.is_structured:
            today: date = date.today()
            return join(
                self.folder,
                str(today.year),
                today.strftime("%B").lower()
            )

        return self.folder

    def _get_file_name(self) -> str:
        if not self.should_cycle:
            return self._attach_date(f"{self.basename}.log")

        return self._attach_date(
            f"{self.basename}.{self._get_file_idx()}.log"
        )

    def _get_file_idx(self) -> int:
        self._file_idx += 1
        return self._file_idx

    def _attach_date(self, basename: str) -> str:
        if self.has_date:
            return f"{date.today()}_{basename}"
        return basename

    def _check_mode(self, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError(
                f"'mode' must be of type 'str' not '{type(value).__name__}'!"
            )

        if value not in ["append", "truncate", "a", "w"]:
            raise UnknownModeError(
                f"Unrecognised file mode: '{value}'!"
            )

        return self._file_mode(value)


class StreamHandler(AbstractHandler):
    """Stream handler."""

    @property
    def handlers(self) -> List[str]:
        return self.cfg.getlist("LOGGER", "handlers", fallback=HANDLERS)

    def handle(self, row: Row):
        for handler in self._get_handlers():
            handler.emit(row)

    def _get_handlers(self) -> List[OutputHandler]:
        return [
            self._get_handler(handler)
            for handler in self.handlers
        ]

    def _get_handler(self, target: str) -> OutputHandler:
        if target not in self.__dict__:
            self.__dict__.update(
                {target: ClassRegistry.get(target, self._name)}
            )
        return self.__dict__.get(target)


class BaseLogger(AbstractHandler):
    """Base logging handler."""

    def __init__(self, name: str = "default", **kwargs):

        # allowed levels:
        self._allowed: dict = {}

        super(BaseLogger, self).__init__(name, **kwargs)

        self._factory = RowFactory(name)
        self._stream = StreamHandler(name)

        # execute at exit:
        register(self.close)

    @property
    def level(self) -> int:
        return self.cfg.getint("LOGGER", "level", fallback=LEVELS.NOTSET)

    @property
    def folder(self) -> str:
        return self.cfg.get("LOGGER", "folder", fallback=FILESTREAM.FOLDER)

    @update
    def log(self, level: Union[int, str], msg: str, *args, **kwargs):
        """
        Log a `msg % args` message with level `level`.

        To add exception info to the message use the
        keyword argument `exc_info` with a true value.

        Example:

            log("Testing '%s' messages!, "INFO", exc_info=True)

        :param level: The logging level to be used.
        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: Optional keyword arguments.
        """
        self._lock.acquire()
        try:
            level: int = self._check_level(level)
        except (TypeError, UnknownLevelError):
            raise
        else:
            if self._is_allowed(level):
                self._log(level, msg, *args, **kwargs)
        finally:
            self._lock.release()

    def close(self):
        with self._lock:
            cleanup(self.folder)

    def _check_level(self, value: Union[str, int]) -> int:
        """
        Check if a given `value` is a valid logging level
        and return its appropriate integer value.
        """
        if not isinstance(value, (str, int)):
            raise TypeError(
                f"'value' must be of type 'str' or 'int' not '{type(value).__name__}'!"
            )

        if not self._exists(value):
            raise UnknownLevelError(
                f"Unknown logging level: '{value}'!"
            )

        if isinstance(value, str):
            return STRKEYS.get(value.upper())

        return value

    @staticmethod
    def _exists(level: Union[str, int]) -> bool:
        if isinstance(level, str):
            return level.upper() in STRKEYS
        return level in INTKEYS

    def _is_allowed(self, level: int) -> bool:
        """
        Check if the given `level` is registered as allowed.
        """
        with self._lock:
            if level not in self._allowed:
                self._allowed.update({level: level >= self.level})
            return self._allowed.get(level)

    def _log(self, level: int, msg, *args, **kwargs):
        with self._lock:
            row: Row = self._factory.build(level, msg, *args, **kwargs)
            self._stream.handle(row)

    def _update_config(self, **kwargs):

        if "level" in kwargs:
            self._update_level(kwargs)

        if "handlers" in kwargs:
            self._update_handlers(kwargs)

        super(BaseLogger, self)._update_config(**kwargs)

    def _update_level(self, kwargs):
        try:
            level: int = self._check_level(kwargs.pop("level"))
        except (TypeError, UnknownLevelError):
            raise
        else:
            kwargs.update(level=level)
            self._reset_allowed(level)

    def _reset_allowed(self, level: int = LEVELS.NOTSET):
        """Reset the logging levels dict."""
        self._allowed.clear()
        if level > LEVELS.NOTSET:
            self._allowed.update({level: True})

    @staticmethod
    def _update_handlers(kwargs):
        handlers = kwargs.get("handlers")

        if not isinstance(handlers, (list, tuple, str)):
            raise TypeError(
                f"'handlers' param must be of type 'list', 'tuple' or 'str' not '{type(handlers).__name__}'!"
            )

        if isinstance(handlers, tuple):
            kwargs.update(handlers=list(handlers))

        elif isinstance(handlers, str):
            kwargs.update(handlers=[handlers])


class Logger(BaseLogger):
    """Logging handler."""

    @update
    def debug(self, msg: str, *args, **kwargs):
        """
        Log a message with level `DEBUG`.

        To add exception info to the message use the
        keyword argument `exc_info` with a true value.

        Example:

            log.debug("Testing '%s' messages!, "DEBUG", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: Optional keyword arguments.
        """
        self.log(LEVELS.DEBUG, msg, *args, **kwargs)

    @update
    def info(self, msg: str, *args, **kwargs):
        """
        Log a message with level `INFO`.

        To add exception info to the message use the
        keyword argument `exc_info` with a true value.

        Example:

            log.info("Testing '%s' messages!, "INFO", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: Optional keyword arguments.
        """
        self.log(LEVELS.INFO, msg, *args, **kwargs)

    @update
    def warning(self, msg: str, *args, **kwargs):
        """
        Log a message with level `WARNING`.

        To add exception info to the message use the
        keyword argument `exc_info` with a true value.

        Example:

            log.warning("Testing '%s' messages!, "WARNING", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: Optional keyword arguments.
        """
        self.log(LEVELS.WARNING, msg, *args, **kwargs)

    def warn(self, msg: str, *args, **kwargs):
        """Don't use this one. Use `warning` instead."""
        self.warning(msg, *args, depth=9, **kwargs)

    @update
    def error(self, msg: str, *args, **kwargs):
        """
        Log a message with level `ERROR`.

        To add exception info to the message use the
        keyword argument `exc_info` with a true value.

        Example:

            log.error("Testing '%s' messages!, "ERROR", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: Optional keyword arguments.
        """
        self.log(LEVELS.ERROR, msg, *args, **kwargs)

    def exception(self, msg: str, *args, **kwargs):
        """
        Just a more convenient way of logging
        an `ERROR` message with `exc_info=True`.
        """

        if "exc_info" not in kwargs:
            kwargs.update(exc_info=True)

        self.error(msg, *args, depth=9, **kwargs)

    @update
    def critical(self, msg: str, *args, **kwargs):
        """
        Log a message with level `CRITICAL`.

        To add exception info to the message use the
        keyword argument `exc_info` with a true value.

        Example:

            log.critical("Testing '%s' messages!, "CRITICAL", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: Optional keyword arguments.
        """
        self.log(LEVELS.CRITICAL, msg, *args, **kwargs)

    def fatal(self, msg: str, *args, **kwargs):
        """Don't use this one. Use `critical` instead."""
        self.critical(msg, *args, depth=9, **kwargs)
