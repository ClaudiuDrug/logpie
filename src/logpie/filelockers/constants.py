# -*- coding: UTF-8 -*-

from enum import IntFlag
from os import name as os_name

if os_name == 'nt':
    from msvcrt import LK_UNLCK

    LOCK_EX = 0x1
    LOCK_SH = 0x2
    LOCK_NB = 0x4
    LOCK_UN = LK_UNLCK

elif os_name == 'posix':
    from fcntl import (
        LOCK_EX,
        LOCK_SH,
        LOCK_NB,
        LOCK_UN,
    )

else:
    raise RuntimeError('File locker only defined for nt and posix platforms')


class LOCK(IntFlag):
    """
    Lock types:
        - ``EX``: exclusive lock
        - ``SH``: shared lock

    ----

    Lock flags:
        - ``NB``: non-blocking

    ----

    Manually unlock (only needed internally):
        - ``UN``: unlock
    """
    EX: int = LOCK_EX  # exclusive lock
    SH: int = LOCK_SH  # shared lock
    NB: int = LOCK_NB  # non-blocking
    UN: int = LOCK_UN  # unlock
