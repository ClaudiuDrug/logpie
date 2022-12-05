# -*- coding: UTF-8 -*-

from abc import ABC, abstractmethod
from atexit import register
from collections.abc import Mapping
from dataclasses import dataclass, asdict, field, make_dataclass
from datetime import datetime, date
from os.path import join, exists
from string import Template
from sys import stdout, stderr
from typing import Union, List, TextIO

from cfgpie import get_config, CfgParser
from colorpie import Style4Bit

from .constants import FRAME, LOGGER, LEVELS, INTKEYS, REGEX, FORMATTING, FILESTREAM
from .exceptions import UnknownLevelError
from .filehandlers import FileHandler
from .registry import ClassRegistry
from .stackframe import get_traceback, get_caller
from .utils import (
    dispatch_lock,
    get_local,
    ensure_tree,
    get_fields,
    cleanup,
    check_config,
    _check_config,
    check_state,
    _check_level,
)


@dataclass
class Row(object):
    """Logging base row class."""
    timestamp: datetime = field(default=None)
    level: str = field(default=None)
    name: str = field(default=None)
    source: FRAME = field(default=None)
    message: str = field(default=None)

    def as_dict(self) -> dict:
        return asdict(self)


class BaseHandler(ABC):
    """Base handler."""

    __config__: dict = {}

    def __init__(self, name: str, **kwargs):
        self._name = name
        self._thread_lock = dispatch_lock(name)
        self.set_config(**kwargs)

    @property
    def name(self):
        return self._name

    @property
    def cfg(self) -> CfgParser:
        return self.__config__.get(self._name)

    @check_config
    def set_config(self, **kwargs):
        self._thread_lock.acquire()
        try:
            if "config" in kwargs:
                instance: CfgParser = _check_config(
                    kwargs.pop("config")
                )
                self.__config__.update({self._name: instance})
        except TypeError:
            raise
        else:
            if self.cfg is None:
                instance: CfgParser = get_config(f"logpie.{self._name}")
                self.__config__.update({self._name: instance})

            if len(kwargs) > 0:
                self.cfg.read_dict(
                    dictionary={"LOGGER": kwargs},
                    source="<update>"
                )
        finally:
            self._thread_lock.release()


class Formatter(BaseHandler):

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

    def safe_substitute(self, **kwargs) -> str:

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


class OutputHandler(BaseHandler):
    """Base abstract handler for stream output classes."""

    def __init__(self, name: str, **kwargs):
        super(OutputHandler, self).__init__(name, **kwargs)
        self._formatter = Formatter(name)

    @abstractmethod
    def write(self, *args, **kwargs):
        raise NotImplementedError

    def emit(self, row: Row):
        self.write(self._as_string(row))

    def _as_string(self, row: Row) -> str:
        return self._formatter.safe_substitute(**row.as_dict())


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
    def has_name(self) -> bool:
        return self.cfg.getboolean(
            "LOGGER", "has_name",
            fallback=FILESTREAM.HAS_NAME
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
    def encoding(self) -> str:
        return self.cfg.get("LOGGER", "encoding", fallback=FILESTREAM.ENCODING)

    def write(self, record: str):
        """Write the log record to console and flush the handle."""

        with FileHandler(self.get_file_path(), "a", encoding=self.encoding) as file_handler:
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
            return self._attach_date(
                f"{self._attach_name(self.basename)}.log"
            )

        return self._attach_date(
            f"{self._attach_name(self.basename)}.{self._get_file_idx()}.log"
        )

    def _attach_name(self, value: str) -> str:
        if self.has_name:
            return f"{value}.{self._name}"
        return value

    def _attach_date(self, basename: str) -> str:
        if self.has_date:
            return f"{date.today()}_{basename}"
        return basename

    def _get_file_idx(self) -> int:
        self._file_idx += 1
        return self._file_idx


class RowFactory(BaseHandler):
    """Logging row factory."""

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
        """Attach `args` & `traceback` info to `message`."""

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
        """Construct and return a new `Row` object."""
        frame: FRAME = self._get_frame(
            exc_info=kwargs.pop("exc_info", None),
            depth=kwargs.pop("depth", 0)
        )

        row = dict(
            timestamp=kwargs.pop("timestamp", get_local()),
            level=INTKEYS.get(level),
            name=self._name,
            source=frame,
            message=self._attach_info(msg, *args, traceback=frame.traceback),
        )

        if "extra" in kwargs:
            return self._replace(row, kwargs.pop("extra"))

        return Row(**row)

    def _replace(self, row: dict, extra: dict) -> Row:
        """
        Construct and update a new `Row` object using the `row` and `extra`
        dictionaries.
        """
        keys: List[str] = get_fields(REGEX, self.format)

        new_row = make_dataclass(
            "Row",
            fields=[
                (key, type(value), field(default=value))
                for key, value in extra.items()
                if (key in keys) and (key not in row.keys())
            ],
            bases=(Row,)
        )

        return new_row(**row)


class StreamHandler(BaseHandler):
    """Logging stream handler."""

    @property
    def handlers(self) -> List[str]:
        return self.cfg.getlist("LOGGER", "handlers", fallback=LOGGER.HANDLERS)

    def handle(self, row: Row):
        for handler in self._get_handlers():
            handler.emit(row)

    def _get_handlers(self) -> List[OutputHandler]:
        return [
            self._get_handler(item)
            for item in self.handlers
        ]

    def _get_handler(self, target: str) -> OutputHandler:
        if target not in self.__dict__:
            self.__dict__.update(
                {target: ClassRegistry.get(target, self._name)}
            )
        return self.__dict__.get(target)


class BaseLogger(RowFactory, StreamHandler):
    """Base logging handler."""

    def __init__(self, name: str = "default", **kwargs):

        # allowed levels:
        self._allowed: dict = {}

        super(BaseLogger, self).__init__(name, **kwargs)

        # execute at exit:
        register(self.close)

    @property
    def state(self) -> str:
        return self.cfg.get("LOGGER", "state", fallback=LOGGER.STATE)

    @property
    def level(self) -> int:
        return self.cfg.getint("LOGGER", "level", fallback=LEVELS.NOTSET)

    @property
    def folder(self) -> str:
        return self.cfg.get("LOGGER", "folder", fallback=FILESTREAM.FOLDER)

    @check_state
    def log(self, level: Union[int, str], msg: str, *args, **kwargs):
        """
        Log `msg % args` message with level `level`.

        To add exception info to the message use the
        keyword argument `exc_info` with a true value.

        Example:

            log("Testing '%s' messages!, "INFO", exc_info=True)

        :param level: The logging level to be used.
        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: Optional keyword arguments.
        """
        self._thread_lock.acquire()
        try:
            level: int = _check_level(level)
        except (TypeError, UnknownLevelError):
            raise
        else:
            if self._is_allowed(level):
                self._log(level, msg, *args, **kwargs)
        finally:
            self._thread_lock.release()

    def close(self):
        with self._thread_lock:
            cleanup(self.folder)

    def _is_allowed(self, level: int) -> bool:
        """
        Check if the given `level` is registered as allowed.
        """
        with self._thread_lock:
            if level not in self._allowed:
                self._allowed.update({level: level >= self.level})
            return self._allowed.get(level)

    def _log(self, level: int, msg, *args, **kwargs):
        with self._thread_lock:
            row: Row = self.build(level, msg, *args, **kwargs)
            self.handle(row)

    def _reset_allowed(self, level: int):
        """Reset the logging levels dict."""
        self._allowed.clear()
        if level > LEVELS.NOTSET:
            self._allowed.update({level: True})


class Logger(BaseLogger):
    """Logging handler."""

    @check_state
    def debug(self, msg: str, *args, **kwargs):
        """
        Log a message `msg % args` with level `DEBUG`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:

            log.debug("Testing '%s' messages!", "DEBUG", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: Optional keyword arguments.
        """
        self.log(LEVELS.DEBUG, msg, *args, **kwargs)

    @check_state
    def info(self, msg: str, *args, **kwargs):
        """
        Log a message `msg % args` with level `INFO`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:

            log.info("Testing '%s' messages!", "INFO", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: Optional keyword arguments.
        """
        self.log(LEVELS.INFO, msg, *args, **kwargs)

    @check_state
    def warning(self, msg: str, *args, **kwargs):
        """
        Log a message `msg % args` with level `WARNING`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:

            log.warning("Testing '%s' messages!", "WARNING", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: Optional keyword arguments.
        """
        self.log(LEVELS.WARNING, msg, *args, **kwargs)

    def warn(self, msg: str, *args, **kwargs):
        """Don't use this one. Use `warning` instead."""
        self.warning(msg, *args, depth=9, **kwargs)

    @check_state
    def error(self, msg: str, *args, **kwargs):
        """
        Log a message `msg % args` with level `ERROR`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:

            log.error("Testing '%s' messages!", "ERROR", exc_info=True)

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

    @check_state
    def critical(self, msg: str, *args, **kwargs):
        """
        Log a message `msg % args` with level `CRITICAL`.

        To add exception info to the message use the
        `exc_info` keyword argument with a `True` value.

        Example:

            log.critical("Testing '%s' messages!", "CRITICAL", exc_info=True)

        :param msg: The message to be logged.
        :param args: Optional arguments for `msg` formatting.
        :param kwargs: Optional keyword arguments.
        """
        self.log(LEVELS.CRITICAL, msg, *args, **kwargs)

    def fatal(self, msg: str, *args, **kwargs):
        """Don't use this one. Use `critical` instead."""
        self.critical(msg, *args, depth=9, **kwargs)
