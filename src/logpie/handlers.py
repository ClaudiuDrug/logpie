# -*- coding: UTF-8 -*-

from abc import ABC, abstractmethod
from atexit import register
from datetime import date
from glob import glob
from os import makedirs, walk
from os.path import join, exists
from shutil import rmtree
from sys import stdout
from typing import Union, Any, Generator

from cfgpie import get_config, CfgParser
from customlib.filehandlers import FileHandler

from .constants import BACKUP, ROOT, RLOCK, ROW, FRAME, TRACEBACK, FOLDER
from .utils import get_traceback, get_caller, get_level, get_timestamp, archive

cfg: CfgParser = get_config(name=f"logger.defaults")
cfg.set_defaults(directory=ROOT)
cfg.read_dict(dictionary=BACKUP, source="<backup>")


class OutputHandler(ABC):
    """Base abstract handler for stream output classes."""

    def emit(self, record: str):
        self.write(record)

    @abstractmethod
    def write(self, *args, **kwargs):
        raise NotImplementedError


class StdStream(OutputHandler):
    """Handler used for logging to console."""

    @staticmethod
    def write(record: str):
        """Write the log record to console and flush the handle."""
        stdout.write(f"{record}\n")
        stdout.flush()


class NoStream(OutputHandler):
    """Handler used for... well... nothing."""

    @staticmethod
    def write(record: str):
        """Do nothing for when you actually need it."""
        pass


class FileStream(OutputHandler):
    """Handler used for logging to a file."""

    def __init__(self):

        self._file_path = None
        self._folder_path = None
        self._file_name = None

        self._file_idx: int = 0
        self._file_size: int = 0

    def write(self, record: str):
        with FileHandler(self.get_file_path(), "a", encoding="UTF-8") as fh:
            fh.write(f"{record}\n")
            self._file_size = fh.tell()

    def get_file_path(self):

        if self._file_path is None:
            self._file_path: str = self._get_file_path()

        elif self._file_size >= ((1024 * 1024) - 1024):
            self._file_path: str = self._get_file_path()

        return self._file_path

    def _get_file_path(self):
        file_path = join(self.get_folder_path(), self.get_file_name())

        if exists(file_path):
            return self._get_file_path()

        return file_path

    def get_folder_path(self):
        if self._folder_path is None:
            self._folder_path = self._get_folder_path()

        if not exists(self._folder_path):
            makedirs(self._folder_path)

        return self._folder_path

    def get_file_name(self):
        return f"{date.today()}_{cfg.get('LOGGER', 'basename')}.{self.get_file_idx()}.log"

    def get_file_idx(self):
        self._file_idx += 1
        return self._file_idx

    @staticmethod
    def _get_folder_path() -> str:
        today: date = date.today()
        return join(
            cfg.get("LOGGER", "folder", fallback=FOLDER),
            str(today.year),
            today.strftime("%B").lower()
        )


class RowFactory(object):

    @staticmethod
    def _get_info(exception: Union[BaseException, tuple, bool]) -> Union[TRACEBACK, FRAME]:
        """
        Get information about the most recent exception caught by an except clause
        in the current stack frame or in an older stack frame.
        """
        if exception is not None:
            try:
                return get_traceback(exception)
            except AttributeError:
                pass

        return get_caller(5)

    @staticmethod
    def _attach_info(message: str, frame: Union[TRACEBACK, FRAME]) -> str:
        """Attach traceback info to `message` if `frame` is an exception."""
        if isinstance(frame, TRACEBACK):
            return f"{message} Traceback: {frame.message}"
        return message

    def build(self, message: str, exception: Union[BaseException, tuple, bool]) -> ROW:
        """Take a `message` and `exception` as params and return a `ROW` object."""
        frame = self._get_info(exception)
        return ROW(
            timestamp=get_timestamp(fmt="%Y-%m-%d %H:%M:%S.%f"),
            level=get_level(3),
            file=frame.file,
            line=frame.line,
            code=frame.code,
            message=self._attach_info(message, frame),
        )


class FormatFactory(object):

    @staticmethod
    def _apply_format(row: ROW) -> str:
        """Construct and return a string from the `ROW` object."""
        return f"[{row.timestamp}] - {row.level} - <{row.file}, {row.line}, {row.code}>: {row.message}"

    def build(self, row: ROW) -> str:
        """Construct and return a new ROW object."""
        return self._apply_format(row)


class Handlers(object):

    def __init__(self):
        self.console: StdStream = StdStream()
        self.nostream: NoStream = NoStream()
        self.file: FileStream = FileStream()

    def get(self, target: str) -> Any:
        return self.__dict__.get(target)


class StreamHandler(object):

    _handlers: Handlers = Handlers()

    @property
    def handler(self) -> OutputHandler:
        return self._handlers.get(
            target=cfg.get("LOGGER", "handler")
        )

    def emit(self, message: str):
        self.handler.emit(message)


class BaseLogger(object):
    """Base logging facility."""

    @staticmethod
    def _set_config(**kwargs):
        global cfg

        if "config" in kwargs:
            cfg = kwargs.pop("config")

            if isinstance(cfg, str):
                cfg = get_config(name=cfg)

        else:
            options: dict = BACKUP.get("LOGGER").copy()
            options.update(**kwargs)

            cfg.read_dict(
                dictionary={"LOGGER": options},
                source="<logging>"
            )

    @staticmethod
    def _months_list(today: date):
        return [
            date(today.year, n, 1).strftime("%B").lower()
            for n in range(1, 13)
            if n != today.month
        ]

    def __init__(self, **kwargs):
        self.set_config(**kwargs)

        self.factory = RowFactory()
        self.formatter = FormatFactory()
        self.stream = StreamHandler()

        register(self.cleanup)

    def set_config(self, **kwargs):
        if len(kwargs) > 0:
            self._set_config(**kwargs)

    def cleanup(self):
        root: str = cfg.get("LOGGER", "folder", fallback=FOLDER)

        if exists(root):

            results = self._scan(root)

            for folder, files in results:
                archive(f"{folder}.zip", files)
                rmtree(folder)

    def _scan(self, target: str) -> Generator:
        today: date = date.today()
        month: str = today.strftime("%B").lower()
        months: list = self._months_list(today)

        for root, folders, files in walk(target):

            if (root == target) or (len(folders) == 0):
                continue

            for folder in folders:
                if folder == month:
                    continue

                if folder in months:

                    folder: str = join(root, folder)
                    files: str = join(folder, "*.log")

                    yield folder, (file for file in glob(files))

    def emit(self, message: str, exception: Union[BaseException, tuple, bool]):
        with RLOCK:
            row: ROW = self.factory.build(message, exception)
            message: str = self.formatter.build(row)
            self.stream.emit(message)


class Logger(BaseLogger):
    """Logging facility with thread & file lock abilities."""

    def debug(self, message: str, exception: Union[BaseException, tuple, bool] = None):
        """
        Log a message with level `DEBUG`.

        :param message: The message to be logged.
        :param exception: Add exception info to the log message.
        """
        if cfg.getboolean("LOGGER", "debug") is True:
            self.emit(message=message, exception=exception)

    def info(self, message: str, exception: Union[BaseException, tuple, bool] = None):
        """
        Log a message with level `INFO`.

        :param message: The message to be logged.
        :param exception: Add exception info to the log message.
        """
        self.emit(message=message, exception=exception)

    def warning(self, message: str, exception: Union[BaseException, tuple, bool] = None):
        """
        Log a message with level `WARNING`.

        :param message: The message to be logged.
        :param exception: Add exception info to the log message.
        """
        self.emit(message=message, exception=exception)

    def error(self, message: str, exception: Union[BaseException, tuple, bool] = None):
        """
        Log a message with level `ERROR`.

        :param message: The message to be logged.
        :param exception: Add exception info to the log message.
        """
        self.emit(message=message, exception=exception)

    def critical(self, message: str, exception: Union[BaseException, tuple, bool] = None):
        """
        Log a message with level `CRITICAL`.

        :param message: The message to be logged.
        :param exception: Add exception info to the log message.
        """
        self.emit(message=message, exception=exception)
