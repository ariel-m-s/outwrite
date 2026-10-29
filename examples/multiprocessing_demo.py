"""Run with: python examples/multiprocessing_demo.py"""

import logging
import multiprocessing as mp
import signal
from multiprocessing.synchronize import Event

import outwrite

logger = logging.getLogger("demo")


def worker(console_connection: outwrite.ConsoleConnection, stop: Event) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    outwrite.configure_console(console_connection)
    for index in range(10):
        if stop.is_set():
            break
        outwrite.status.update(f"Processing file {index + 1} of 10")
        if index % 3 == 0:
            logger.info("Finished a batch")
        stop.wait(0.2)
    outwrite.status.clear()
    logger.info("Worker finished")


if __name__ == "__main__":
    context = mp.get_context("spawn")
    stop = context.Event()
    with outwrite.configure_console(
        logger=logger, mp_context=context
    ) as console_connection:
        process = context.Process(target=worker, args=(console_connection, stop))
        process.start()
        try:
            process.join()
        finally:
            stop.set()
            process.join()
        if process.exitcode != 0:
            raise SystemExit(f"Worker exited with code {process.exitcode}")
