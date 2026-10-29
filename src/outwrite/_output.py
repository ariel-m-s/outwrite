"""Parent rendering and worker connections."""

from __future__ import annotations

import atexit
import logging
import multiprocessing as mp
import os
import sys
import threading
import traceback
from dataclasses import dataclass
from logging.handlers import QueueHandler
from multiprocessing.context import BaseContext
from multiprocessing.queues import Queue
from types import TracebackType

from rich.console import Console
from rich.live import Live
from rich.logging import RichHandler
from rich.text import Text

_connection: OutputConnection | None = None
_session: _OutputSession | None = None


class _Status:
    """Send text to the active session's status line."""

    def update(self, text: str | None) -> None:
        """Replace the status text. None or an empty string clears it."""
        if text is not None and not isinstance(text, str):
            raise TypeError("Status text must be a string or None.")
        if _connection is None:
            raise RuntimeError("Call setup_output() before updating status.")
        if _connection._show_status:
            _connection._queue.put("" if text is None else text)

    def clear(self) -> None:
        """Clear the status line without ending the output session."""
        self.update(None)


status = _Status()


@dataclass(frozen=True)
class OutputConnection:
    """Pass this handle to workers; use it as a context manager in the parent."""

    _queue: Queue
    _logger_name: str
    _show_status: bool
    _parent_pid: int

    def __enter__(self) -> OutputConnection:
        if os.getpid() != self._parent_pid:
            raise RuntimeError(
                "Only the parent owns the output context; use setup_output(output) in workers."
            )
        if _session is None or _session.connection is not self:
            raise RuntimeError("This output session is no longer active.")
        if _session.entered:
            raise RuntimeError("An output context cannot be nested.")
        _session.entered = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: TracebackType | None,
    ) -> None:
        if _session is None or _session.connection is not self:
            raise RuntimeError("This output session is no longer active.")
        _session.close()


class _OutputSession:
    """Own everything that must remain in the rendering process."""

    def __init__(
        self,
        connection: OutputConnection,
        logger: logging.Logger,
        console: Console,
        level: int,
    ) -> None:
        self.connection = connection
        self.logger = logger
        self.console = console
        self.previous_handlers = logger.handlers[:]
        self.previous_level = logger.level
        self.previous_propagate = logger.propagate
        self.console_handler = RichHandler(console=console, level=level)
        self.handlers = [*self.previous_handlers, self.console_handler]
        self.queue_handler = QueueHandler(connection._queue)
        self.live = Live(
            console=console,
            transient=True,
            auto_refresh=False,
            redirect_stdout=False,
            redirect_stderr=False,
        )
        self.error: Exception | None = None
        self.entered = False
        self.listener = threading.Thread(
            target=self.listen, name="outwrite-renderer", daemon=True
        )

    def listen(self) -> None:
        while True:
            try:
                message = self.connection._queue.get()
            except (EOFError, OSError) as error:
                self.error = error
                traceback.print_exception(error, file=sys.stderr)
                return
            if message is None:
                return
            try:
                if isinstance(message, logging.LogRecord):
                    for handler in self.handlers:
                        if message.levelno >= handler.level:
                            handler.handle(message)
                elif not message:
                    self.live.stop()
                else:
                    text = Text(
                        message, style="cyan", no_wrap=True, overflow="ellipsis"
                    )
                    text.truncate(max(1, self.console.width - 2), overflow="ellipsis")
                    self.live.update(text, refresh=self.live.is_started)
                    if not self.live.is_started:
                        self.live.start(refresh=True)
            except Exception as error:
                # Keep draining so producers cannot deadlock behind a failed renderer.
                self.error = error
                traceback.print_exception(error, file=sys.stderr)

    def close(self) -> None:
        global _connection, _session
        self.logger.handlers = self.previous_handlers
        self.logger.setLevel(self.previous_level)
        self.logger.propagate = self.previous_propagate
        _connection = None
        try:
            self.connection._queue.put(None)
            self.listener.join()
        finally:
            self.live.stop()
            self.connection._queue.close()
            self.connection._queue.join_thread()
            self.queue_handler.close()
            self.console_handler.close()
            _session = None
            atexit.unregister(_cleanup_at_exit)
        if self.error is not None:
            raise RuntimeError(
                "Outwrite could not render one or more messages."
            ) from self.error


def setup_output(
    connection: OutputConnection | None = None,
    *,
    logger: logging.Logger | None = None,
    level: int = logging.INFO,
    show_status: bool = True,
    mp_context: BaseContext | None = None,
) -> OutputConnection:
    """Start a parent session, or connect a worker to the parent's session.

    Parent usage: ``with setup_output(logger=my_logger) as output: ...``.
    Join workers and logging threads before leaving the block.
    Worker usage: ``setup_output(output)`` before logging or updating status.
    Worker configuration comes from the connection, not the keyword options.
    """
    global _connection, _session
    if _connection is not None:
        raise RuntimeError("Output is already configured in this process.")
    if connection is not None:
        if connection._parent_pid == os.getpid():
            raise RuntimeError(
                "The parent is already responsible for rendering this connection."
            )
        worker_logger = logging.getLogger(connection._logger_name)
        worker_logger.handlers = [QueueHandler(connection._queue)]
        worker_logger.setLevel(logging.DEBUG)
        worker_logger.propagate = False
        _connection = connection
        return connection

    if logger is None:
        logger = logging.getLogger("outwrite")
    if logger is logging.getLogger():
        raise ValueError("Choose a named logger, not the root logger.")
    if not isinstance(level, int):
        raise TypeError("level must be an integer logging level, such as logging.INFO.")
    context = mp_context if mp_context is not None else mp.get_context("spawn")
    if context.get_start_method() == "fork":
        raise ValueError("Use a spawn or forkserver multiprocessing context, not fork.")

    console = Console(stderr=True)
    connection = OutputConnection(
        context.Queue(), logger.name, show_status and console.is_terminal, os.getpid()
    )
    session = _OutputSession(connection, logger, console, level)
    logger.handlers = [session.queue_handler]
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    _connection = connection
    _session = session
    session.listener.start()
    atexit.register(_cleanup_at_exit)
    return connection


def _cleanup_at_exit() -> None:
    if _session is not None:
        _session.close()
