# Outwrite

Keep your logs readable and your progress visible.

Outwrite combines Python's standard logging with one live **status line**:
text that updates in place to show what your program is doing.
Logs stay above it, even when they come from different threads or processes.

Log messages stay in the output. The status line changes in place:

```text
[10/30/26 12:00:00] INFO     Starting                         app.py:10
[10/30/26 12:00:02] INFO     Finished file 2                  app.py:14
                    Processing file 3 of 5
```

The last line might change to “Processing file 4 of 5” without adding another
line. Status is text you provide, not an automatically calculated progress bar.
It can show a count, a task name, or the time of the last save.

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

Keep using Python's logging methods as usual; only status updates need a new
call. Outwrite doesn't create log files. If your logger already has a file
handler, it continues to receive log messages, but not status updates.

## Multiple processes

The main process handles all terminal output. Workers send messages to it
through a shared connection:

| Where | Setup |
| --- | --- |
| Main process | Call `outwrite.configure_console()` to get the connection. |
| Each worker | Pass in the connection and call `outwrite.configure_console(console_connection)`. |

Wait for workers to finish before leaving the main process's `with` block.
Otherwise, Outwrite may close before their final messages arrive.

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

Use the same logger name in the main process and workers (“my_app” above).
Outwrite forwards that logger's messages and messages from its child loggers
that propagate to it, not every logger in the program.

`multiprocessing.get_context("spawn")` chooses how Python starts workers:
each gets a fresh Python interpreter. Use that same `context` for Outwrite and
your processes so their shared queues work together. Outwrite defaults to spawn
and also supports forkserver, but not fork. Keep process creation
inside `if __name__ == "__main__":` so workers don't start more workers.

Threads need no extra setup: use the logger and `outwrite.status` directly.

There is one shared status line, not one per worker. If several workers update
it, the last update received is the one shown.

See the [full example](examples/multiprocessing_demo.py) for handling Ctrl+C.

## Options

Pass these options to `outwrite.configure_console(...)`:

| Option | Default | What it does |
| --- | --- | --- |
| `console_connection` | `None` | Pass the main process's connection when setting up a worker. Leave unset in the main process. |
| `logger` | `None` | The Python logger to use. If omitted, uses the logger named “outwrite”. The root logger is not supported. |
| `console_level` | `logging.INFO` | Minimum log level shown by the default console handler. Accepts integer logging levels, including custom levels. Existing handlers keep their own levels. |
| `show_status` | `True` | Whether to show the status line. Does not affect logs. |
| `mp_context` | `None` | Multiprocessing context used to create the shared queue. Defaults to spawn. Use the same context to create your workers. |
| `console_handler` | `None` | Your own RichHandler for console logs. Its console, formatting, and level replace the defaults. |
| `render_status` | `None` | Function that takes `(text, console)` and returns something Rich can display. The default is cyan text that fits on one line. |

In workers, pass only `console_connection`. The other options configure the main
process; they are ignored when a connection is supplied.

You can also control the status line while working:

| Call | What it does |
| --- | --- |
| `outwrite.status.clear()` | Remove the current text. The next update can show it again. |
| `outwrite.status.disable()` | Hide status and ignore later updates until the `with` block ends. Call this in the main process only. |

By default, output goes to stderr. When that stream is redirected to a file or
pipe, logs are still written, but the live status line is hidden.

## Change how it looks

Outwrite uses Rich for formatting. You can change the logs, the status line,
or both. This example hides the time and source filename in logs and makes
status text green:

```python
import logging

import outwrite
from rich.console import Console
from rich.logging import RichHandler
from rich.text import Text

logger = logging.getLogger("my_app")
handler = RichHandler(show_time=False, show_path=False, level=logging.INFO)


def render_status(text: str, console: Console) -> Text:
    status_text = Text(text, style="green", no_wrap=True)
    status_text.truncate(max(1, console.width - 2), overflow="ellipsis")
    return status_text


with outwrite.configure_console(
    logger=logger, console_handler=handler, render_status=render_status
):
    logger.info("Starting")
    outwrite.status.update("Processing files")
    # Do your work here.
```

Both settings are optional. A supplied handler controls the console and log
level; `console_level` does not override it. Outwrite uses that same console
for status and passes it to your rendering function so you can fit the text
to its width.

Existing file handlers keep receiving logs. Outwrite doesn't add your console
handler twice if it's already attached, and leaves it open when finished.
Set appearance options in the main process only; workers need no changes.

## License

[MIT](LICENSE).
