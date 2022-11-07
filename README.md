# logpie
Logging made simple.

This is a simple logging module with thread & file locking abilities.

---

#### Installation:

```commandline
python -m pip install [--upgrade] logpie
```

---

#### Usage:

```python
# your `main.py` module

from os.path import dirname, realpath, join
from sys import modules
from types import ModuleType

from cfgpie import get_config, CfgParser
from logpie import get_logger, Logger

# **************************** config constants: **************************** #

# main module
MODULE: ModuleType = modules.get("__main__")

# root directory
ROOT: str = dirname(realpath(MODULE.__file__))

# default config file path:
CONFIG: str = join(ROOT, "config", "cfgpie.ini")

# backup config params:
BACKUP: dict = {
    "LOGGER": {
        "basename": "logpie",  # if handler is `file`
        "folder": r"${DEFAULT:directory}\logs",
        "handlers": ["file"],  # or `console` or both (always as list)
        "level": 0,  # logs all messages above this level
    }
}

# NOTE: The constants above serve the usage example,
#       and you can use whatever suits you best.

# ********************** get `ConfigParser` instance: *********************** #

cfg: CfgParser = get_config(name="my_config")
cfg.set_defaults(directory=ROOT)
cfg.open(file_path=CONFIG, encoding="UTF-8", fallback=BACKUP)

# ************************* get `Logger` instance: ************************** #

# we can pass a config instance:
log: Logger = get_logger(name="my_logger", config=cfg)
```

or

```python
# it will look for a config instance named `my_config`:
log: Logger = get_logger(name="my_logger", config="my_config")
```

or

```python
# it will create and use its own config instance:
log: Logger = get_logger(name="my_logger", level="debug", handlers="file", basename="logpie")


if __name__ == '__main__':
    log.debug("Testing debug messages...")
    log.info("Testing info messages...")
    log.warning("Testing warning messages...")
    log.error("Testing error messages...")
    log.critical("Testing critical messages...")
```

By default, logging `level` is set to `NOTSET` (0) and it logs all messages.

The log file is prefixed with a date and will have an index number attached before the extension (ex: `2022-08-01_logpie.1.log`).
When it reaches `1 Mb` the file handler will switch to another file by incrementing its index with `1`.

The folder tree is by default structured as follows:

```markdown
.
└───logs
    └───year (ex: 2022)
        └───month (ex: january)
            ├───2022-08-01_logpie.1.log
            ├───2022-08-01_logpie.2.log
            └───2022-08-01_logpie.3.log
```

When the current month changes, a new folder is created and the previous one is archived.

---
