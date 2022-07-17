from ntpath import join
import os
import time
from enum import Enum


def log(output, before_text=""):
    """Log the output with a timestamp."""

    if before_text == "":
        print(time.strftime("[%d/%b/%Y:%H:%M:%S] ") + output)
    else:
        print(before_text +
              time.strftime(" - - [%d/%b/%Y:%H:%M:%S] ") + output)


def get_absolute_path(*path):
    """Returns the absolute path based on a path relative to this folder."""
    joined_path = os.path.dirname(__file__)
    for item in path:
        joined_path = os.path.join(joined_path, item)
    return os.path.abspath(joined_path)


class ConnectionStatus(Enum):
    """The connection status of a single module."""

    DISCONNECTED = 0
    WARNING = 1
    CONNECTED = 2
