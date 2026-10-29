import io
import logging
import multiprocessing as mp
import threading
import time
import unittest

import outwrite
from outwrite import _console
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text


def log_from_worker(console_connection: outwrite.ConsoleConnection) -> None:
    outwrite.configure_console(console_connection)
    logging.getLogger("outwrite.tests").info("Worker finished")


class ConsoleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stream = io.StringIO()
        self.handler = RichHandler(
            console=Console(file=self.stream, force_terminal=True),
            show_time=False,
            show_path=False,
        )
        self.logger = logging.getLogger("outwrite.tests")
        self.previous_handlers = self.logger.handlers[:]
        self.previous_level = self.logger.level
        self.previous_propagate = self.logger.propagate
        self.logger.handlers = [self.handler]
        self.logger.setLevel(logging.WARNING)
        self.logger.propagate = False

    def tearDown(self) -> None:
        self.logger.handlers = self.previous_handlers
        self.logger.setLevel(self.previous_level)
        self.logger.propagate = self.previous_propagate
        self.handler.close()

    def test_logging_reuses_handler_and_restores_logger(self) -> None:
        with outwrite.configure_console(
            logger=self.logger, console_handler=self.handler
        ):
            self.logger.info("Saved results")

        self.assertEqual(self.stream.getvalue().count("Saved results"), 1)
        self.assertEqual(self.logger.handlers, [self.handler])
        self.assertEqual(self.logger.level, logging.WARNING)
        self.assertFalse(self.logger.propagate)
        self.assertFalse(self.handler._closed)

    def test_exception_cleans_up_and_allows_another_session(self) -> None:
        with self.assertRaisesRegex(ValueError, "Work failed"):
            with outwrite.configure_console(
                logger=self.logger, console_handler=self.handler
            ):
                raise ValueError("Work failed")

        self.assertEqual(self.logger.handlers, [self.handler])
        self.assertEqual(self.logger.level, logging.WARNING)

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

    def test_status_can_clear_restart_and_disable(self) -> None:
        rendered = threading.Event()
        updates = []

        def render_status(text: str, console: Console) -> Text:
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

            outwrite.status.disable()
            self.assertFalse(session.live.is_started)
            outwrite.status.update("Must stay hidden")

        self.assertEqual(updates, ["First status", "Restarted status"])
        self.assertFalse(session.live.is_started)


if __name__ == "__main__":
    unittest.main()
