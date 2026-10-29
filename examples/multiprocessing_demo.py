"""Run with: python examples/multiprocessing_demo.py"""

import logging
import multiprocessing as mp
import signal
from multiprocessing.synchronize import Event

from outwrite import OutputConnection, setup_output, status

logger = logging.getLogger("demo")


def worker(output: OutputConnection, stop: Event) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    setup_output(output)
    for index in range(10):
        if stop.is_set():
            break
        status.update(f"Processing file {index + 1} of 10")
        if index % 3 == 0:
            logger.info("Finished a batch")
        stop.wait(0.2)
    status.clear()
    logger.info("Worker finished")


if __name__ == "__main__":
    context = mp.get_context("spawn")
    stop = context.Event()
    with setup_output(logger=logger, mp_context=context) as output:
        process = context.Process(target=worker, args=(output, stop))
        process.start()
        try:
            process.join()
        finally:
            stop.set()
            process.join()
        if process.exitcode != 0:
            raise SystemExit(f"Worker exited with code {process.exitcode}")
