# -*- coding: UTF-8 -*-

__all__ = [
    "LoggingError",
    "UnknownLevelError",
    "UnknownStateError",
    "UnknownHandlerError",
    "UnknownFormatterError",
]


class LoggingError(Exception):
    """Base logging exception."""


class UnknownLevelError(LoggingError):
    """Exception raised for unknown level errors."""


class UnknownStateError(LoggingError):
    """Exception raised for unknown state errors."""


class UnknownHandlerError(LoggingError):
    """Exception raised for unknown handler errors."""


class UnknownFormatterError(LoggingError):
    """Exception raised for unknown formatter errors."""
