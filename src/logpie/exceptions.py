# -*- coding: UTF-8 -*-


class LogPieError(Exception):
    """Base exception class."""


class UnknownModeError(LogPieError):
    """Exception raised for unknown mode errors."""


class UnknownLevelError(LogPieError):
    """Exception raised for unknown level errors."""


class UnknownStateError(LogPieError):
    """Exception raised for unknown state errors."""


class HandlerKeyError(LogPieError):
    """Exception raised for handler key errors."""


class RegistryKeyError(KeyError):
    """Exception raised for registry key errors."""


class DuplicateKeyError(RegistryKeyError):
    """Exception raised for duplicate registry keys."""


class MissingKeyError(RegistryKeyError):
    """Exception raised for missing registry keys."""
