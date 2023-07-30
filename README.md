# logpie

A versatile logging framework.

Simple, efficient, and configurable logging framework to manage and streamline your application logs.


### Installation:

```commandline
python -m pip install [--upgrade] logpie
```


#### Key Features

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


#### _class_ logpie.Logger

###### Parameters:

  * `name` (required): str - The name of the logger (defaults to `logpie`).

    The name of the logger cannot be changed after instantiation!


  * `level` (optional): LEVEL - Logging level of the logger (defaults to `LEVEL.NOTSET`).


  * `state` (optional): STATE - State of the logger (defaults to `STATE.ON`).


  * `handlers` (optional): Handler - A handler or a list/tuple of handlers for the logger (defaults to `None`).

    `StreamHandler` will use the default handler `StdStream`.

###### Methods:

  * `name`

    A property that returns the name of the logger.
    > NOTE: Cannot be changed after instantiation!


  * `set_level(value: LEVEL)`

    Sets the attribute `level` of the logger to _value_.
    All other messages with severity level less than this _value_ will be ignored.
    By default, the logger is instantiated with severity level `LEVEL.NOTSET` (0) and therefore all messages are logged.

    Available levels:
    * `DEBUG`
    * `INFO`
    * `WARNING`
    * `ERROR`
    * `CRITICAL`


  * `set_state(value: STATE)`
  
    Sets the attribute `state` of the logger to _value_.
    If set to `STATE.OFF` (disabled) no message will be recorded.
    By default, the logger is instantiated with state `STATE.ON` (enabled) and therefore all messages are logged.

  * `set_handlers(value: Union[Handler, List[Handler], Tuple[Handler]])`

    Sets the stream handlers for the logger to __value__.

    Available handlers:
      * `StdStream`  
      * `FileStream`  


  * `del_handlers()`

    Delete the handlers of the logger.


  * `add_handler(value: Handler)`

    Add a handler to the logger.


  * `remove_handler(value: Handler)`

    Remove a handler from the logger.


  * `is_enabled()`

    Return `True` if the logger is enabled and `False` otherwise.


  * `log(level: LEVEL, msg: str, *args, **kwargs)`
  
    Log a message with `msg % args` with level `level`.
    To add exception info to the message use the `exc_info` keyword argument with a `True` value.
  
    Example:
  
      ```python
      log(LEVEL.ERROR, "Testing '%s' messages!", "ERROR", exc_info=True)
      ```

      or

      ```python
      log(LEVEL.ERROR, "Testing '%(level)s' messages!", {"level": "ERROR"}, exc_info=True)
      ```

    To get the correct frame from the stack, when called, the `depth` param must be set to 8 or called inside a logging function.

    Example:
  
      ```python
      log(LEVEL.DEBUG, "Testing 'DEBUG' messages!", depth=8)
      ```

      or

      ```python
      def debug(self, msg: str, *args, **kwargs):
        self.log(LEVEL.DEBUG, msg, *args, **kwargs)
      ```


  * `close()`

    Close the handlers of the logger and release the resources.


  * `debug(msg: str, *args, **kwargs)`

    Log a message with `msg % args` with level `DEBUG`.
    To add exception info to the message use the `exc_info` keyword argument with a `True` value.

    Example:

      ```python
      log.debug("Testing 'DEBUG' messages!")
      ```

  * `info(msg: str, *args, **kwargs)`

    Log a message with `msg % args` with level `INFO`
    The arguments and keyword arguments are interpreted as for `debug()` 

    Example:

      ```python
      log.info("Testing 'INFO' messages!")
      ```

  * `warning(msg: str, *args, **kwargs)`

    Log a message with `msg % args` with level `WARNING`
    The arguments and keyword arguments are interpreted as for `debug()` 

    Example:

      ```python
      log.warning("Testing 'WARNING' messages!")
      ```


  * `error(msg: str, *args, **kwargs)`

    Log a message with `msg % args` with level `ERROR`
    The arguments and keyword arguments are interpreted as for `debug()` 

    Example:

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


  * `exception(msg: str, *args, **kwargs)`

    Just a more convenient way of logging an `ERROR` message with `exc_info=True`.

    Example:

      ```python
      try:
          raise TypeError("Type error occurred!")
      except TypeError:
          log.exception("Action failed!")
      ```


  * `critical(msg: str, *args, **kwargs)`

    Log a message with `msg % args` with level `CRITICAL`
    The arguments and keyword arguments are interpreted as for `debug()` 

    Example:

      ```python
      try:
          raise TypeError("Critical error occurred!")
      except TypeError as critical_error:
          log.critical("Action failed!", exc_info=critical_error)
      ```


### StreamHandlers:


By default, the logger streams all messages to the console output `sys.stdout` and `sys.stderr` using the `StdStream` handler.
To log messages into a file we must use the `FileStream` handler.


To use a different handler or more:

```python
from logpie import Logger, StdStream, FileStream

console_hdlr = StdStream()
file_hdlr = FileStream("my_log_file.log")

log = Logger("my_logger", handlers=[console_hdlr, file_hdlr])


if __name__ == '__main__':
    log.debug("Logging debug messages!")

```


#### _class_ logpie.StdStream

###### Parameters:

* `formatter`: Formatter - Formatter object to format the logs (defaults to `None`).


###### Methods:

* `emit(row: Row)`

    Emit a log row.
    This method acquires the thread lock and passes the log row formatted as
    a string along with the handle associated with the logging level to the `write()` method.


* `write(handle: TextIO, message: str)`

    Write the log `message` using the given `handle`.


#### _class_ logpie.FileStream

###### Parameters:

* `filename` (required): str - Name of the file to write logs into.


* `mode` (optional): str - Mode of file opening (defaults to `a`).
    
    * `a` for appending to file.
    * `w` for truncating the file.


* `encoding` (optional): str - Encoding of the file (defaults to `UTF-8`).


* `folder`: str - Folder to write logs in (defaults to `None`).

    If omitted and filename is not a full file path it defaults to
    the `logs` folder at the root of your project.


* `max_size`: int - Maximum size of the log file (defaults to `(1024 ** 2) * 4`, 4 MB).

    If `cycle` is enabled, when the file reaches the maximum size,
    the handler will switch to another file by incrementing the index with `1`.


* `cycle`: bool - Whether to cycle files when maximum size is reached (defaults to `False`).

    When the file reaches the maximum size,
    the handler will switch to another file by incrementing the index with `1`


* `chronological`: bool - Whether to sort files chronologically (defaults to `False`).

    The folder tree is by default structured as follows:

    ```markdown
    .
    └─logs
      └─year (ex: 2022)
        └─month (ex: january)
          ├─2022-08-01_logpie.1.log
          ├─2022-08-01_logpie.2.log
          └─2022-08-01_logpie.3.log
    ```


* `date_prefix`: bool - Whether to add date prefix to filename (defaults to `False`).


* `date_aware`: bool - Whether to use date awareness to the log file (defaults to `False`).

    If `date_prefix` is enabled this will enforce the current date to be
    used rather than the date when the handler was created.


* `formatter`: Formatter - Formatter object to format the logs (defaults to `None`).


###### Methods:

* `emit(row: Row)`

    Emit a log row.
    This method acquires the thread lock and passes the log `row` formatted as
    a string to the `write()` method.


* `write(message: str)`

    Write a log `message` into the file.


The log rows are formatted with the help of the `Formatter` class.

To change the formatting:

```python
from src.logpie import Logger, FileStream, Formatter

# here we're also adding a new field (e.g. 'ip') used by the 'extra' keyword arguments.
my_formatter = Formatter(
    row="${timestamp} - ${ip} - ${level} - ${source}: ${message}",
    timestamp="[%Y-%m-%d %H:%M:%S.%f]",
    stack="<${file}, ${line}, ${code}>",
)
my_handler = FileStream("my_log_file.log", formatter=my_formatter)
log = Logger("my_logger", handlers=my_handler)


if __name__ == '__main__':
    # here we are passing the 'ip' keyword argument for the 'extra' field
    log.debug("Testing 'DEBUG' messages!", ip="192.168.1.100")
```


#### _class_ logpie.Formatter

###### Parameters:

* `row`: str - The row formatting template.

    This template uses the `string.Template` style with placeholders (e.g. `${field}`).


* `timestamp`: str - The timestamp formatting template.

    This template uses the `datetime.strftime()` style (e.g. `%Y-%m-%d %H:%M:%S.%f`).


* `stack`: str - The stack info formatting template.

    This template uses the `string.Template` style with placeholders (e.g. `${field}`).


###### Methods:

* `as_string(row: Row)`

    Format a given row into a string based on predefined templates.
