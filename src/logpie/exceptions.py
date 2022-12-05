# -*- coding: UTF-8 -*-


class LogPieError(Exception):
    """Base exception class."""


class UnknownLevelError(LogPieError):
    """Exception raised for unknown logging level errors."""


class UnknownStateError(LogPieError):
    """Exception raised for unknown state errors."""


class RegistryKeyError(KeyError):
    """Exception raised for registry key errors."""


class DuplicateKeyError(RegistryKeyError):
    """Exception raised for duplicate registry keys."""


class MissingKeyError(RegistryKeyError):
    """Exception raised for missing registry keys."""


class UnknownHandlerError(LogPieError):
    """Exception raised for unknown handler error."""
