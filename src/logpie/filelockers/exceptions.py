# -*- coding: UTF-8 -*-

from typing import Any, Optional, IO


class BaseLockException(Exception):
    """Base exception class."""

    # Error codes:
    LOCK_FAILED = 1

    def __init__(self, *args: Any, handle: Optional[IO] = None):
        super(BaseLockException, self).__init__(*args)

        self.handle = handle


class LockException(BaseLockException):
    """Exception class for file locking errors."""


class AlreadyLocked(LockException):
    """Exception class for files already locked."""


class FileToLarge(LockException):
    """Exception class for files too large to handle."""


class LockFlagsError(LockException):
    """Exception class for wrong flags on handle operating mode."""
