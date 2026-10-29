"""Console logging, live status, and worker connections."""

from __future__ import annotations

import atexit
import logging
import multiprocessing as mp
import os
from collections.abc import Callable
from dataclasses import dataclass
from logging.handlers import QueueHandler
from multiprocessing.context import BaseContext
from multiprocessing.queues import Queue
from types import TracebackType

from rich.console import Console, ConsoleRenderable
from rich.logging import RichHandler

from ._session import _ConsoleSession

_connection: ConsoleConnection | None = None
_session: _ConsoleSession | None = None


class _Status:
    """Send text to the active session's status line."""

    def update(self, text: str | None) -> None:
        """Replace the status text. None or an empty string clears it."""
        if text is not None and not isinstance(text, str):
            raise TypeError("Status text must be a string or None.")

        if _connection is None:
            raise RuntimeError("Call configure_console() before updating status.")

        if _connection._show_status:
            _connection._queue.put("" if text is None else text)

    def clear(self) -> None:
        """Clear the status line without ending the console session."""
        self.update(None)

    def disable(self) -> None:
        """Immediately clear parent status and ignore further updates for this session."""
        if _session is None:
            raise RuntimeError("Only the parent can disable the status display.")

        with _session.render_lock:
            _session.status_disabled = True
            _session.live.stop()


status = _Status()


@dataclass(frozen=True)
class ConsoleConnection:
    """Pass this handle to workers; use it as a context manager in the parent."""

    _queue: Queue
    _logger_name: str
    _show_status: bool
    _parent_pid: int

    def __enter__(self) -> ConsoleConnection:
        if os.getpid() != self._parent_pid:
            raise RuntimeError(
                "Only the parent owns the console context; "
                "use configure_console(console_connection) in workers."
            )
        if _session is None or _session.connection is not self:
            raise RuntimeError("This console session is no longer active.")
        if _session.entered:
            raise RuntimeError("A console context cannot be nested.")

        _session.entered = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        if _session is None or _session.connection is not self:
            raise RuntimeError("This console session is no longer active.")
        _close_session()


def configure_console(
    console_connection: ConsoleConnection | None = None,
    *,
    logger: logging.Logger | None = None,
    console_level: int = logging.INFO,
    show_status: bool = True,
    mp_context: BaseContext | None = None,
    console_handler: RichHandler | None = None,
    render_status: Callable[[str, Console], ConsoleRenderable] | None = None,
) -> ConsoleConnection:
    """Configure console logging and status, or connect to the parent's console.

    Parent usage: ``with outwrite.configure_console(logger=my_logger) as console_connection: ...``.
    Join workers and logging threads before leaving the block.
    Worker usage: ``outwrite.configure_console(console_connection)`` before logging or status.
    Worker configuration comes from the connection, not the keyword options.
    console_level filters the default console handler, not existing handlers.
    A custom RichHandler supplies the shared console and keeps its own level.
    render_status(text, console) returns a Rich renderable in the parent only.
    """
    global _connection, _session
    if _connection is not None:
        raise RuntimeError(
            "Console logging and status are already configured in this process."
        )

    # Workers forward messages; only the parent owns rendering resources.
    if console_connection is not None:
        if console_connection._parent_pid == os.getpid():
            raise RuntimeError(
                "The parent is already responsible for rendering this connection."
            )
        worker_logger = logging.getLogger(console_connection._logger_name)
        worker_logger.handlers = [QueueHandler(console_connection._queue)]
        worker_logger.setLevel(logging.DEBUG)
        worker_logger.propagate = False
        _connection = console_connection
        return console_connection

    if logger is None:
        logger = logging.getLogger("outwrite")
    if logger is logging.getLogger():
        raise ValueError("Choose a named logger, not the root logger.")
    if not isinstance(console_level, int):
        raise TypeError(
            "console_level must be an integer logging level, such as logging.INFO."
        )

    # Match the application's queue/process context without changing global settings.
    context = mp_context if mp_context is not None else mp.get_context("spawn")
    if context.get_start_method() == "fork":
        # Forking after the rendering thread starts is unsafe.
        raise ValueError("Use a spawn or forkserver multiprocessing context, not fork.")

    console = (
        console_handler.console if console_handler is not None else Console(stderr=True)
    )
    console_connection = ConsoleConnection(
        context.Queue(), logger.name, show_status and console.is_terminal, os.getpid()
    )
    session = _ConsoleSession(
        console_connection,
        logger,
        console,
        console_level,
        console_handler,
        render_status,
    )

    # Route parent logs through the same queue as worker logs and status updates.
    logger.handlers = [session.queue_handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    _connection = console_connection
    _session = session

    session.listener.start()
    atexit.register(_close_session)
    return console_connection


def _close_session() -> None:
    """Close the active parent session and clear process-local state."""
    global _connection, _session

    if _session is not None:
        # Reject new status updates while the listener drains its queue.
        _connection = None
        try:
            _session.close()
        finally:
            _session = None
            atexit.unregister(_close_session)
