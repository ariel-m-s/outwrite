import io
import logging
import multiprocessing as mp
import threading
import time
import unittest
from contextlib import redirect_stderr

import outwrite
from outwrite import _console
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text


def log_from_worker(console_connection: outwrite.ConsoleConnection) -> None:
    outwrite.configure_console(console_connection)
    logger = logging.getLogger("outwrite.tests")
    for index in range(100):
        logger.info("Worker message %03d", index)
    logger.info("Worker finished")


class OutwriteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stream = io.StringIO()
        self.handler = RichHandler(
            console=Console(
                file=self.stream, force_terminal=True, color_system=None, width=120
            ),
            show_time=False,
            show_path=False,
            level=logging.INFO,
        )
        self.logger = logging.getLogger("outwrite.tests")
        self.previous_handlers = self.logger.handlers[:]
        self.previous_level = self.logger.level
        self.previous_propagate = self.logger.propagate
        self.logger.handlers = [self.handler]
        self.logger.setLevel(logging.WARNING)
        self.logger.propagate = True

    def tearDown(self) -> None:
        self.logger.handlers = self.previous_handlers
        self.logger.setLevel(self.previous_level)
        self.logger.propagate = self.previous_propagate
        self.handler.close()

    def test_exception_drains_logs_and_restores_existing_handlers(self) -> None:
        file_stream = io.StringIO()
        file_handler = logging.StreamHandler(file_stream)
        file_handler.setLevel(logging.DEBUG)
        self.addCleanup(file_handler.close)
        self.logger.addHandler(file_handler)

        with self.assertRaisesRegex(ValueError, "Work failed"):
            with outwrite.configure_console(
                logger=self.logger,
                console_handler=self.handler,
                console_level=logging.CRITICAL,
            ):
                self.logger.debug("File only")
                self.logger.info("Saved results")
                raise ValueError("Work failed")

        self.assertEqual(self.stream.getvalue().count("Saved results"), 1)
        self.assertNotIn("File only", self.stream.getvalue())
        self.assertIn("File only", file_stream.getvalue())
        self.assertEqual(file_stream.getvalue().count("Saved results"), 1)
        self.assertEqual(self.logger.handlers, [self.handler, file_handler])
        self.assertEqual(self.logger.level, logging.WARNING)
        self.assertTrue(self.logger.propagate)

        # A supplied handler must still work after Outwrite releases it.
        self.logger.warning("After cleanup")
        self.assertIn("After cleanup", self.stream.getvalue())

    def test_renderer_failure_is_reported_without_losing_later_logs(self) -> None:
        def broken_renderer(text: str, console: Console) -> Text:
            raise ValueError("Cannot render status")

        errors = io.StringIO()
        with redirect_stderr(errors):
            with self.assertRaisesRegex(RuntimeError, "could not render") as raised:
                with outwrite.configure_console(
                    logger=self.logger,
                    console_handler=self.handler,
                    render_status=broken_renderer,
                ):
                    outwrite.status.update("Broken status")
                    self.logger.info("Log after broken status")

        self.assertIsInstance(raised.exception.__cause__, ValueError)
        self.assertEqual(str(raised.exception.__cause__), "Cannot render status")
        self.assertIn("Cannot render status", errors.getvalue())
        self.assertEqual(self.stream.getvalue().count("Log after broken status"), 1)

        # Rendering failure must not leave the process permanently configured.
        with outwrite.configure_console(
            logger=self.logger, console_handler=self.handler
        ):
            self.logger.info("Started again")

        self.assertIn("Started again", self.stream.getvalue())

    def test_spawned_worker_logs_are_drained_on_exit(self) -> None:
        context = mp.get_context("spawn")
        with outwrite.configure_console(
            logger=self.logger, console_handler=self.handler, mp_context=context
        ) as console_connection:
            process = context.Process(
                target=log_from_worker, args=(console_connection,)
            )
            process.start()
            try:
                process.join(timeout=10)
                self.assertEqual(process.exitcode, 0)
            finally:
                if process.is_alive():
                    process.terminate()
                    process.join()

        self.assertEqual(self.stream.getvalue().count("Worker finished"), 1)
        for index in range(100):
            self.assertEqual(
                self.stream.getvalue().count(f"Worker message {index:03d}"), 1
            )

    def test_status_can_clear_restart_and_disable(self) -> None:
        rendered = threading.Event()
        updates = []

        def render_status(text: str, console: Console) -> Text:
            self.assertIs(console, self.handler.console)
            updates.append(text)
            rendered.set()
            return Text(text)

        with outwrite.configure_console(
            logger=self.logger,
            console_handler=self.handler,
            render_status=render_status,
        ):
            session = _console._session
            self.assertIsNotNone(session)

            outwrite.status.update("First status")
            self.assertTrue(rendered.wait(timeout=5))
            with session.render_lock:
                self.assertTrue(session.live.is_started)

            outwrite.status.clear()
            deadline = time.monotonic() + 5
            while session.live.is_started and time.monotonic() < deadline:
                time.sleep(0.01)
            self.assertFalse(session.live.is_started)

            rendered.clear()
            outwrite.status.update("Restarted status")
            self.assertTrue(rendered.wait(timeout=5))

            # Keep the listener blocked until disable wins over an already queued update.
            with session.render_lock:
                outwrite.status.update("Queued before disable")
                outwrite.status.disable()
                self.assertFalse(session.live.is_started)
                outwrite.status.update("Queued after disable")

        self.assertEqual(updates, ["First status", "Restarted status"])
        self.assertFalse(session.live.is_started)


if __name__ == "__main__":
    unittest.main()
