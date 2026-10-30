"""Short multiprocessing demo for recording or trying Outwrite."""

import logging
import multiprocessing as mp
import time
from multiprocessing.sharedctypes import Synchronized

import outwrite

logger = logging.getLogger("outwrite.demo")
ITEMS_PER_WORKER = 4


def process_items(
    name: str,
    delay: float,
    console_connection: outwrite.ConsoleConnection,
    completed: Synchronized,
) -> None:
    outwrite.configure_console(console_connection)
    logger.info("%s started", name)
    for item in range(1, ITEMS_PER_WORKER + 1):
        time.sleep(delay)
        with completed.get_lock():
            completed.value += 1
        logger.info("%s processed item %s/%s", name, item, ITEMS_PER_WORKER)
    logger.info("%s finished", name)


def main() -> None:
    context = mp.get_context("spawn")
    completed = context.Value("i", 0)
    workers = (("Worker A", 0.3), ("Worker B", 0.5))

    with outwrite.configure_console(
        logger=logger, mp_context=context
    ) as console_connection:
        processes = [
            context.Process(
                target=process_items,
                args=(name, delay, console_connection, completed),
            )
            for name, delay in workers
        ]
        for process in processes:
            process.start()

        while any(process.is_alive() for process in processes):
            with completed.get_lock():
                count = completed.value
            outwrite.status.update(f"Files processed: {count} of 8")
            time.sleep(0.1)

        for process in processes:
            process.join()
            if process.exitcode != 0:
                raise RuntimeError(f"Worker exited with code {process.exitcode}")

        outwrite.status.update("Files processed: 8 of 8")
        logger.info("All files processed")


if __name__ == "__main__":
    main()
