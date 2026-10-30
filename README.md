# Outwrite

**Readable logs. Live status. Even across processes and threads.**

`outwrite` pairs standard Python logging with one status line that updates in place. Keep the useful messages, skip the progress chatter.

![Illustration: a decaf warning surrounded by repeated brewing progress logs on the left; the same warning with one live "Brewing cup 6/100. Send help." status line on the right.](docs/assets/outwrite-comparison.png?v=97ea83f)

Built on [Rich](https://github.com/Textualize/rich) and standard logging. `outwrite` handles the queue, live display, and cleanup so you don't have to wire them together yourself.

Requires Python 3.11+.

## Install

```sh
pip install outwrite
```

## Quick start

A tiny coffee run. Keep the milestones in the log; let status handle the play-by-play:

```python
import logging
import time

import outwrite

logger = logging.getLogger("coffee")

with outwrite.configure_console(logger=logger):
    logger.info("Beans ready")

    for cup in range(1, 4):
        outwrite.status.update(f"Brewing cup {cup}/3. Almost human.")
        time.sleep(0.5)  # Simulate brewing.

    logger.info("Coffee ready")
```

When the `with` block ends, `outwrite` finishes printing pending messages and removes the status line. Existing file handlers still receive logs, but not status.

Status is text you provide, not an automatically calculated progress bar. Use it for imports, downloads, long-running checks, or whatever your script is doing now.

## Running multiple processes or threads?

Bring their logs into the same console, too. `outwrite` handles the queue, listener, and cleanup for batch jobs, parallel downloads, and multi-stage pipelines. Just need logging? Set `show_status=False`.

![Illustration: downloader, resizer, and uploader tasks send cat-photo processing logs through a shared queue and single listener into one console, with no status line required.](docs/assets/outwrite-concurrency.png?v=1)

Logs and status updates travel through a shared queue to a single listener in the main process, rather than each process writing to the terminal on its own.

Pass the connection returned by the main process to each child process and call `outwrite.configure_console(console_connection)` there before logging or updating status.

```python
import logging
import multiprocessing as mp

import outwrite

logger = logging.getLogger("coffee")


def brew(connection):
    outwrite.configure_console(connection)
    logger.info("Beans ready")
    outwrite.status.update("Brewing coffee")


if __name__ == "__main__":
    context = mp.get_context("spawn")
    with outwrite.configure_console(logger=logger, mp_context=context) as connection:
        process = context.Process(target=brew, args=(connection,))
        process.start()
        process.join()
        if process.exitcode != 0:
            raise RuntimeError(f"Child process exited with code {process.exitcode}")
```

Save this as a Python file and run it, rather than pasting it into a REPL.

The [multiprocessing demo](https://github.com/ariel-m-s/outwrite/blob/main/examples/multiprocessing_demo.py) shows the complete setup, including cleanup when interrupted with Ctrl+C.

After installing `outwrite`, run it from a repository checkout:

```sh
python examples/multiprocessing_demo.py
```

- Use the same logger name and multiprocessing context in the main process and workers.
- Join workers before leaving the `with` block so their final messages arrive.
- Workers share one status line; the last update received is shown.

Threads share the same setup, so there's no connection to pass around. Messages are displayed in queue-receipt order, not globally sorted by timestamp.

## Options

Pass these options to `outwrite.configure_console(...)`:

| Option | Default | What it does |
| --- | --- | --- |
| `console_connection` | `None` | Pass the main process's connection when setting up a worker. Leave unset in the main process. |
| `logger` | `None` | The Python logger to use. If omitted, uses the logger named `"outwrite"`. The root logger is not supported. |
| `console_level` | `logging.INFO` | Minimum log level shown by the default console handler. Accepts integer logging levels, including custom levels. Existing handlers keep their own levels. |
| `show_status` | `True` | Whether to show the status line. Does not affect logs. |
| `mp_context` | `None` | Multiprocessing context used to create the shared queue. Defaults to spawn. Use the same context to create your workers. |
| `console_handler` | `None` | Your own RichHandler for console logs. Its console, formatting, and level replace the defaults. |
| `render_status` | `None` | Function that takes `(text, console)` and returns something Rich can display. The default is cyan text that fits on one line. |

In workers, pass only `console_connection`. The other options configure the main
process; they are ignored when a connection is supplied.

| Call | What it does |
| --- | --- |
| `outwrite.status.clear()` | Remove the current text. The next update can show it again. |
| `outwrite.status.disable()` | Hide status and ignore later updates until the `with` block ends. Call this in the main process only. |

By default, output goes to stderr. When that stream is redirected to a file or pipe, logs are still written, but the live status line is hidden.

## Change how it looks

This example hides the time and source filename in logs and makes status green:

```python
import logging
import time

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
    outwrite.status.update("Brewing coffee. Worth the wait.")
    time.sleep(1)
    # Do your work here.
```

A supplied handler controls the console and log level; `console_level` does not override it. Status uses the same console. `outwrite` reuses your handler without adding it twice or closing it afterward.

## License

[MIT](LICENSE).
