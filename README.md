# logpie

A versatile logging framework.

Simple, efficient, and configurable logging framework to manage and streamline your application logs.


### Installation:

```commandline
python -m pip install [--upgrade] logpie
```


### Key Features:

* Supports both file-based and console logging.
* Allows chronological organization of log files by year and month.
* Automatic log file cycling based on file size.
* Thread-safe operations for reliable logging.
* Customize your logs with configurable formatters.
* Can prefix log files with dates for easy tracking.


### Usage:

```python
# -*- coding: UTF-8 -*-

from logpie import Logger

log = Logger("my_logger")

if __name__ == '__main__':
    log.debug("Testing debug messages...")
    log.info("Testing info messages...")
    log.warning("Testing warning messages...")
    log.error("Testing error messages...")
    log.critical("Testing critical messages...")
```


### Components:

#### _class_ logpie.Logger

###### Parameters:

| Parameter  | Type      | Default         | Description                                                                           |
|:-----------|:----------|:----------------|:--------------------------------------------------------------------------------------|
| `name`     | `str`     | `logpie`        | The name of the logger. The name of the logger cannot be changed after instantiation! |
| `level`    | `Level`   | `NOTSET`        | The severity level for this logger.                                                   |
| `handlers` | `Handler` | `StreamHandler` | A handler or a tuple of handlers for this logger.                                     |


###### Methods:

* `name`

    A property that returns the name of the logger.
    
    > NOTE:
    >
    > Cannot be changed after instantiation!


* `level`

    A property that returns the severity level used by the logger.


* `level.setter`

    Sets the attribute `level` of the logger to _value_.
    All other messages with severity level less than this _value_ will be ignored.
    By default, the logger is instantiated with severity level `NOTSET` (0) and therefore all messages are logged.

    Available levels:
    * `DEBUG`
    * `INFO`
    * `WARNING`
    * `ERROR`
    * `CRITICAL`


* `handlers`

    A property that returns the handlers used by the logger.


* `handlers.setter`

    Sets the logging handlers for the logger.

    Available handlers:
    * `StreamHandler`
    * `FileHandler`


* `add_handler(value: Handler)`

    Add a handler to the logger.


* `remove_handler(value: Handler)`

    Remove a handler from the logger.


* `has_handlers`

    Check if the logger instance has any handlers.


* `close()`

    Close the handlers of the logger and release the resources.


* `debug(msg: str, *args, **kwargs)`

    Log a `msg % args` with level `DEBUG`.
    To add exception info to the message use the `exc_info` keyword argument with a True value.

    **Example:**

    ```python
    log.debug("Testing '%s' messages!", "DEBUG", exc_info=True)
    ```

    or

    ```python
    log.debug("Testing '%(level)s' messages!", {"level": "DEBUG"}, exc_info=True)
    ```


* `info(msg: str, *args, **kwargs)`

    Log a `msg % args` with level `INFO`.
    To add exception info to the message use the `exc_info` keyword argument with a True value.

    **Example:**

    ```python
    log.info("Testing '%s' messages!", "INFO", exc_info=True)
    ```

    or

    ```python
    log.info("Testing '%(level)s' messages!", {"level": "INFO"}, exc_info=True)
    ```


* `warning(msg: str, *args, **kwargs)`

    Log a `msg % args` with level `WARNING`.
    To add exception info to the message use the `exc_info` keyword argument with a True value.

    **Example:**

    ```python
    log.warning("Testing '%s' messages!", "WARNING", exc_info=True)
    ```
    
    or
    
    ```python
    log.warning("Testing '%(level)s' messages!", {"level": "WARNING"}, exc_info=True)
    ```


* `error(msg: str, *args, **kwargs)`

    Log a `msg % args` with level `ERROR`.
    To add exception info to the message use the `exc_info` keyword argument with a True value.

    **Example:**

    ```python
    try:
        raise TypeError("Type error occurred!")
    except TypeError:
        log.error("Action failed!", exc_info=True)
    ```
    
    or
    
    ```python
    try:
        raise TypeError("Type error occurred!")
    except TypeError as type_error:
        log.error("Action failed!", exc_info=type_error)
    ```


* `critical(msg: str, *args, **kwargs)`

    Log a `msg % args` with level `CRITICAL`.
    To add exception info to the message use the `exc_info` keyword argument with a True value.

    **Example:**

    ```python
    try:
        raise TypeError("Critical error occurred!")
    except TypeError:
        log.critical("Action failed!", exc_info=True)
    ```

    or

    ```python
    try:
        raise TypeError("Critical error occurred!")
    except TypeError as critical_error:
        log.critical("Action failed!", exc_info=critical_error)
    ```


### Handlers:


By default, the logger streams all messages to the console output `sys.stdout` using the `StreamHandler()` handler.
To log messages into a file we must use the `FileHandler()` handler.


To use a different handler or more:

```python
from logpie import Logger, StreamHandler, FileHandler

console = StreamHandler()
file = FileHandler("my_log_file.log")

log = Logger("my_logger", handlers=(console, file))


if __name__ == '__main__':
    log.debug("Logging debug messages!")

```


#### _class_ logpie.StreamHandler

###### Parameters:

| Parameter   | Type        | Default | Description                                            |
|:------------|:------------|:--------|:-------------------------------------------------------|
| `formatter` | `Formatter` | `None`  | Formatter object used to format the log messages.      |
| `handle`    | `TextIO`    | `None`  | The handle used to output the messages to the console. |


###### Methods:

* `handle`

    A property that returns the handle in use.


* `handle.setter`

    Set the handle used by the handler.


* `emit(row: Row)`

    Emit a log row.
    This method acquires the thread lock and passes the log row formatted as
    a string to the `write()` method.


* `write(message: str)`

    Write the log `message` using the given `handle`.


#### _class_ logpie.FileHandler

###### Parameters:

| Parameter       | Type        | Default                  | Description                                                                                                                                                                        |
|:----------------|:------------|:-------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `filename`      | `str`       | `None`                   | Name of the file to write logs into.                                                                                                                                               |
| `mode`          | `str`       | `a`                      | Mode of file opening: `a` for appending and `w` for truncating the file.                                                                                                           |
| `encoding`      | `str`       | `UTF-8`                  | Encoding of the file.                                                                                                                                                              |
| `max_size`      | `int`       | `(1024 ** 2) * 4` (4 MB) | Maximum size of the log file, in bytes. If `cycle` is enabled, when the file reaches the maximum size, the handler will switch to another file by incrementing the index with `1`. |
| `cycle`         | `bool`      | `False`                  | Whether to cycle files when maximum size is reached. When the file reaches the maximum size, the handler will switch to another file by incrementing the index with `1`.           |
| `chronological` | `bool`      | `False`                  | Whether to sort files chronologically.                                                                                                                                             |
| `date_prefix`   | `bool`      | `False`                  | Whether to add date prefix to filename.                                                                                                                                            |
| `date_aware`    | `bool`      | `False`                  | Whether to use date awareness to the log file. If `date_prefix` is enabled this will enforce the current date to be used rather than the date when the handler was created.        |
| `formatter`     | `Formatter` | `None`                   | Formatter object to format the logs.                                                                                                                                               |

When `chronological` is enabled, the folder tree is by default structured as follows:

```markdown
.
└─logs
    └─year (ex: 2022)
        └─month (ex: january)
            ├─2022-08-01_logpie.1.log
            ├─2022-08-01_logpie.2.log
            └─2022-08-01_logpie.3.log
```


###### Methods:

* `emit(row: Row)`

    Emit a log row.
    This method acquires the thread lock and passes the log `row` formatted as
    a string to the `write()` method.


* `write(message: str)`

    Write a log `message` into the file.


#### _class_ logpie.Formatter

The log rows are formatted with the help of the `Formatter` class.

**Example:**

```python
from logpie import Logger, FileHandler, Formatter

# here we're also adding a new field (e.g. 'ip') used by the 'extra' keyword arguments.
my_formatter = Formatter(
    row="${timestamp} - ${ip} - ${level} - ${source}: ${message}",
    timestamp="[%Y-%m-%d %H:%M:%S.%f]",
    stack="<${file}, ${line}, ${code}>",
)
my_handler = FileHandler("my_log_file.log", formatter=my_formatter)
log = Logger("my_logger", handlers=my_handler)


if __name__ == '__main__':
    # here we are passing the 'ip' keyword argument for the 'extra' field
    log.debug("Testing 'DEBUG' messages!", ip="192.168.1.100")
```


###### Parameters:

| Parameter | Type | Default                                           | Description                                                                                                             |
|:----------|:-----|:--------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------|
| row       | str  | '${timestamp} - ${level} - ${source}: ${message}' | The row formatting template. This template uses the `string.Template` style with placeholders (e.g. `${field}`).        |
| time      | str  | '[%Y-%m-%d %H:%M:%S.%f]'                          | The timestamp formatting template. This template uses the `datetime.strftime()` style (e.g. `%Y-%m-%d %H:%M:%S.%f`).    |
| stack     | str  | '<${file}, ${line}, ${code}>'                     | The stack info formatting template. This template uses the `string.Template` style with placeholders (e.g. `${field}`). |


###### Methods:

* `as_string(row: Row)`

    Format a given row into a string based on predefined templates.
