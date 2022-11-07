# -*- coding: UTF-8 -*-

from datetime import date, datetime, timezone
from functools import wraps
from glob import glob
from os import makedirs, walk
from os.path import basename, isdir, join, exists
from re import finditer, MULTILINE
from shutil import rmtree
from threading import RLock
from typing import Union, List, Generator
from weakref import WeakValueDictionary
from zipfile import ZipFile


def update(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if "timestamp" not in kwargs:
            kwargs.update(timestamp=get_local())

        if "depth" not in kwargs:

            if func.__name__ == "log":
                kwargs.update(depth=6)

            else:
                kwargs.update(depth=8)

        func(*args, **kwargs)

    return wrapper


def get_local() -> datetime:
    """Returns an aware localized `datetime` object."""
    utc = get_utc()
    return utc.astimezone()


def get_utc() -> datetime:
    """Returns a UTC `datetime`."""
    return datetime.now(timezone.utc)


def get_fields(pattern: str, text: str) -> List[str]:
    """Find and return a dictionary of row dictionary."""
    matches = finditer(pattern, text, MULTILINE)
    return [
        match.group("name")
        for match in matches
    ]


def cleanup(folder_path: str):
    if exists(folder_path) and isdir(folder_path):
        results = scan(folder_path)

        for folder, files in results:
            archive(f"{folder}.zip", files)
            rmtree(folder)


def scan(target: str) -> Generator:
    today: date = date.today()
    month: str = today.strftime("%B").lower()
    months: list = months_list(today)

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


def months_list(today: date) -> List[str]:
    return [
        date(today.year, n, 1).strftime("%B").lower()
        for n in range(1, 13)
        if n != today.month
    ]


def archive(file_path: str, data: Union[Generator, str]):
    """Archive `data` to the given `file_path`."""
    with ZipFile(file_path, "w") as zip_handle:
        if isinstance(data, Generator) is True:
            for file in data:
                path, name = file, basename(file)
                zip_handle.write(path, name)
        else:
            path, name = data, basename(data)
            zip_handle.write(path, name)


def dispatch_lock(name: str, container: WeakValueDictionary) -> RLock:
    if name not in container:
        # a strong reference is required
        instance = RLock()
        container[name] = instance
    return container[name]


def ensure_tree(path: str):
    if not exists(path):
        create_tree(path)


def create_tree(path: str):
    try:
        makedirs(path)
    except FileExistsError:
        pass
