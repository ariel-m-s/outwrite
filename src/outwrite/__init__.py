"""Standard logging and one live status line, across processes."""

from ._console import ConsoleConnection, configure_console, status

__all__ = ["ConsoleConnection", "configure_console", "status"]
