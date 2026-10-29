# Outwrite

Keep your logs readable and your progress visible.

Outwrite combines Python's standard logging with one live **status line**:
text that updates in place to show what your program is doing.
Logs stay above it, even when they come from different threads or processes.

Think **"what happened"** above, **"what's happening now"** below:

```text
[10/30/26 12:00:00] INFO     Starting                         app.py:10
[10/30/26 12:00:02] INFO     Finished file 2                  app.py:14
Processing file 3 of 5
```

Show progress without printing a new line for every update. All processes share
the same status line; each update replaces it.

Keep important events in your logs and show what you're doing on the status line:

```text
Logs:    "Starting"         "Finished file 1"         "Finished file 2"
         Each message adds a line.

Status:  "File 1 of 5"  ->  "File 2 of 5"         ->  "File 3 of 5"
         Each update replaces the same line.
```

Status can be any text: `"Downloading files"`, `"12 of 20 complete"`, or
`"Last saved 10 seconds ago"`. Your code decides what it says and when it changes.

Built on [Rich](https://github.com/Textualize/rich). Python 3.11+. Currently in alpha.

## Install

```sh
python -m pip install outwrite==0.1.0a3
```

## Quick start

Try this small example to see the status change while logs appear:

```python
import logging
import time

import outwrite

logger = logging.getLogger("my_app")

with outwrite.configure_console(logger=logger):
    logger.info("Starting")

    for number in range(1, 6):
        outwrite.status.update(f"Processing file {number} of 5")
        time.sleep(0.5)  # Your work goes here.
        logger.info("Finished file %s", number)

    logger.info("Done")
```

Run this in a terminal to see the last line change. When the `with` block ends,
Outwrite finishes printing pending messages and removes the status line.

Use `logger.info(...)`, `logger.warning(...)`, and the other logging methods as
usual. Call `outwrite.status.update(...)` whenever the current task changes.
Log messages stay visible; status is temporary. Neither call writes to a log
file unless you have added a file handler to your logger.

### A few useful options

Pass these options to `outwrite.configure_console(...)`:

| Option | What it does |
| --- | --- |
| `console_level=logging.DEBUG` | Show debug messages too. The default is `logging.INFO`. Existing log files keep their own settings. |
| `show_status=False` | Hide status but keep showing logs. |

You can also control the status line while working:

| Call | What it does |
| --- | --- |
| `outwrite.status.clear()` | Remove the current text. The next update can show it again. |
| `outwrite.status.disable()` | Hide status and ignore later updates until the `with` block ends. Call this in the main process only. |

By default, output goes to stderr, Python's usual stream for log messages.
If you send that output to a file or pipe instead of a terminal, logs are still
written, but the live status line is hidden.

## Multiple processes

Worker processes send their logs and status to the main process, which displays
them together:

```text
Worker A --+
           +--> Main process --> Logs above, one status line below
Worker B --+
```

There are three steps:

1. In the main process, call `outwrite.configure_console()` to get a connection.
2. Pass that connection to each worker and call the same function there.
3. Wait for workers to finish before leaving the main process's `with` block.

```python
import logging
import multiprocessing as mp

import outwrite

logger = logging.getLogger("my_app")


def work(console_connection: outwrite.ConsoleConnection):
    outwrite.configure_console(console_connection)
    logger.info("Worker started")
    outwrite.status.update("Processing files")
    # Do your work here.
    logger.info("Worker finished")


if __name__ == "__main__":
    context = mp.get_context("spawn")
    with outwrite.configure_console(
        logger=logger, mp_context=context
    ) as console_connection:
        process = context.Process(target=work, args=(console_connection,))
        process.start()
        process.join()
```

Here, `process.join()` waits for the worker. Use the same logger name in the main
process and workers (`"my_app"` above).

`multiprocessing.get_context("spawn")` chooses how Python starts workers:
each gets a fresh Python interpreter. Use that same `context` for Outwrite and
your processes so their shared queues work together. Keep process creation
inside `if __name__ == "__main__":` so workers don't start more workers.

Threads need no extra setup: use the logger and `outwrite.status` directly.

There is one shared status line, not one per worker. If several workers update
it, the last update received is the one shown.

See the [full example](examples/multiprocessing_demo.py) for handling Ctrl+C.

## Custom appearance

To customize log appearance, pass `console_handler=your_rich_handler`.
Outwrite uses that RichHandler's formatting, console, and log level.
Other logging handlers, such as file handlers, keep receiving messages.
If your handler is already on the logger, it won't print messages twice.
Outwrite leaves your handler open when the `with` block ends.

To style the status line, pass `render_status=your_status_renderer`.
This function takes `(text, console)` and returns something Rich can display,
such as a `rich.text.Text` object.

Set these options in the main process only. Workers just call
`outwrite.configure_console(console_connection)`.

## License

[MIT](LICENSE).
