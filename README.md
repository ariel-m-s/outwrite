# Outwrite

Keep your logs readable and your progress visible.

`outwrite` combines Python's standard logging with a live **status line** that updates in place while logs stay readable, including messages from multiple processes or threads. The status is plain text you control, so it fits naturally into existing CLI workflows.

```text
[10/30/26 12:00:00] INFO     Starting                        app.py:10
[10/30/26 12:00:02] INFO     Configuration check passed      app.py:14
Running connection check
```

Status is text you provide, not an automatically calculated progress bar.

Built on [Rich](https://github.com/Textualize/rich). Python 3.11+.

## Install

```sh
pip install outwrite
```

## Quick start

```python
import logging
import time

import outwrite

logger = logging.getLogger("my_app")

with outwrite.configure_console(logger=logger):
    logger.info("Starting")

    for check in ("Configuration", "Connection", "Permissions"):
        outwrite.status.update(f"Running {check.lower()} check")
        time.sleep(0.5)  # Simulate each check.
        logger.info("%s check passed", check)

    logger.info("Done")
```

When the `with` block ends, `outwrite` finishes printing pending messages and removes the status line. Existing file handlers still receive logs, but not status.

## Multiple processes

Pass the connection returned by the main process to each child process and call `outwrite.configure_console(console_connection)` there before logging or updating status.

The [multiprocessing demo](https://github.com/ariel-m-s/outwrite/blob/main/examples/multiprocessing_demo.py) shows the complete setup, including cleanup when interrupted with Ctrl+C.

After installing `outwrite`, run it from a repository checkout:

```sh
python examples/multiprocessing_demo.py
```

- Use the same logger name and multiprocessing context in the main process and workers.
- Join workers before leaving the `with` block so their final messages arrive.
- Workers share one status line; the last update received is shown.

Threads need no extra setup.

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
    outwrite.status.update("Simulation: step 1 of 100")
    time.sleep(1)
    # Do your work here.
```

A supplied handler controls the console and log level; `console_level` does not override it. Status uses the same console. `outwrite` reuses your handler without adding it twice or closing it afterward.

## License

[MIT](LICENSE).
