"""Standard logging and one live status line, across processes."""

from ._output import ConsoleConnection, configure_console, status

__all__ = ["ConsoleConnection", "configure_console", "status"]
