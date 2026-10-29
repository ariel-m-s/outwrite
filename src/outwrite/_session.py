"""Parent-side rendering and console resource ownership."""

from __future__ import annotations

import logging
import sys
import threading
import traceback
from collections.abc import Callable
from logging.handlers import QueueHandler
from typing import TYPE_CHECKING

from rich.console import Console, ConsoleRenderable
from rich.live import Live
from rich.logging import RichHandler
from rich.text import Text

if TYPE_CHECKING:
    from ._console import ConsoleConnection


class _ConsoleSession:
    """Keep handlers, rendering, and listener resources in the parent process."""

    def __init__(
        self,
        console_connection: ConsoleConnection,
        logger: logging.Logger,
        console: Console,
        console_level: int,
        console_handler: RichHandler | None,
        render_status: Callable[[str, Console], ConsoleRenderable] | None,
    ) -> None:
        self.connection = console_connection
        self.logger = logger
        self.console = console

        # Restore the caller's logging configuration when the session closes.
        self.previous_handlers = logger.handlers[:]
        self.previous_level = logger.level
        self.previous_propagate = logger.propagate

        self.console_handler = console_handler or RichHandler(
            console=console, level=console_level
        )
        self.owns_console_handler = console_handler is None

        # A supplied handler may already be attached; dispatch to it only once.
        self.handlers = [
            handler
            for handler in self.previous_handlers
            if handler is not self.console_handler
        ] + [self.console_handler]
        self.queue_handler = QueueHandler(console_connection._queue)

        self.render_status = render_status
        self.status_disabled = False
        self.render_lock = threading.RLock()
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
        """Render queued messages serially, until the shutdown sentinel arrives."""
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
                with self.render_lock:
                    self._render_message(message)
            except Exception as error:
                # Keep draining so producers cannot deadlock behind a failed renderer.
                self.error = error
                traceback.print_exception(error, file=sys.stderr)

    def _render_message(self, message: logging.LogRecord | str) -> None:
        if isinstance(message, logging.LogRecord):
            for handler in self.handlers:
                if message.levelno >= handler.level:
                    handler.handle(message)
            return

        # Empty text clears status; None is reserved for listener shutdown.
        if not message:
            self.live.stop()
            return

        if self.status_disabled:
            return

        if self.render_status is None:
            text = Text(message, style="cyan", no_wrap=True, overflow="ellipsis")
            text.truncate(max(1, self.console.width - 2), overflow="ellipsis")
            content = text
        else:
            content = self.render_status(message, self.console)

        self.live.update(content, refresh=self.live.is_started)
        if not self.live.is_started:
            self.live.start(refresh=True)

    def close(self) -> None:
        """Restore logging, drain pending messages, and release owned resources."""
        self.logger.handlers = self.previous_handlers
        self.logger.setLevel(self.previous_level)
        self.logger.propagate = self.previous_propagate

        # Workers must already be joined so their final messages precede shutdown.
        try:
            self.connection._queue.put(None)
            self.listener.join()
        finally:
            self.live.stop()
            self.connection._queue.close()
            self.connection._queue.join_thread()
            self.queue_handler.close()

            # Caller-supplied handlers remain usable after the session.
            if self.owns_console_handler:
                self.console_handler.close()

        if self.error is not None:
            raise RuntimeError(
                "Outwrite could not render one or more messages."
            ) from self.error
