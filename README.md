# Outwrite

Keep your logs readable and your progress visible.

Outwrite combines Python's standard logging with a live **status line** that
updates in place while logs stay readable, including logs from worker processes.
The status is plain text you control, so it fits naturally into existing CLI
workflows.

Try the [short multiprocessing demo](examples/quick_demo.py), or read on for the
full setup and configuration options.

```text
[10/30/26 12:00:00] INFO     Starting                         app.py:10
[10/30/26 12:00:02] INFO     Configuration check passed      app.py:14
                    Running connection check
```

Status is text you provide, not an automatically calculated progress bar.

Built on [Rich](https://github.com/Textualize/rich). Python 3.11+. Currently in alpha.

## Install

```sh
python -m pip install outwrite==0.1.0a3
```

Outwrite is in alpha; the install command pins the version shown.

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

When the `with` block ends, Outwrite finishes printing pending messages and
removes the status line. Existing file handlers still receive logs, but not status.

### Hide and show status

Use `clear()` to hide the line. The next `update()` shows it again:

```python
import time

import outwrite

with outwrite.configure_console():
    outwrite.status.update("Waiting for the next task")
    time.sleep(1)

    outwrite.status.clear()
    time.sleep(1)  # No status line during this pause.

    outwrite.status.update("Running the next task")
    time.sleep(1)
```

Use `clear()`, not `disable()`, if you want to show status again in the same block.

## Multiple processes

Pass the connection to each worker and call `outwrite.configure_console()` there:
Both workers log their own messages. The main process shows their combined
progress on the status line:

```python
import logging
import multiprocessing as mp
import time

import outwrite

logger = logging.getLogger("my_app")


def work(name: str, delay: float, console_connection: outwrite.ConsoleConnection, completed):
    outwrite.configure_console(console_connection)
    logger.info("%s started", name)
    for number in range(1, 6):
        time.sleep(delay)  # Simulate workers running at different speeds.
        with completed.get_lock():
            completed.value += 1
        logger.info("%s finished file %s", name, number)
    logger.info("%s finished", name)


if __name__ == "__main__":
    context = mp.get_context("spawn")
    completed = context.Value("i", 0)  # Shared integer, initially zero.
    with outwrite.configure_console(logger=logger, mp_context=context) as console_connection:
        processes = [
            context.Process(target=work, args=(name, delay, console_connection, completed))
            for name, delay in (("Worker A", 0.3), ("Worker B", 0.7))
        ]
        for process in processes:
            process.start()

        while any(process.is_alive() for process in processes):
            with completed.get_lock():
                count = completed.value
            outwrite.status.update(f"Total files ready: {count} of 10")
            time.sleep(0.1)

        for process in processes:
            process.join()
            if process.exitcode != 0:
                raise RuntimeError(f"Worker exited with code {process.exitcode}")

        logger.info("Total files ready: %s of 10", completed.value)
```

The shared counter tracks completed files; Outwrite only displays the text.
The lock prevents workers from changing the counter at the same time.

- Use the same logger name and multiprocessing context in the main process and workers.
- Join workers before leaving the `with` block so their final messages arrive.
- Use spawn or forkserver, not fork.
- Workers share one status line; the last update received is shown.

Threads need no extra setup.
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

| Call | What it does |
| --- | --- |
| `outwrite.status.clear()` | Remove the current text. The next update can show it again. |
| `outwrite.status.disable()` | Hide status and ignore later updates until the `with` block ends. Call this in the main process only. |

By default, output goes to stderr. When that stream is redirected to a file or
pipe, logs are still written, but the live status line is hidden.

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

A supplied handler controls the console and log level; `console_level` does not
override it. Status uses the same console. Outwrite reuses your handler without
adding it twice or closing it afterward.

## License

[MIT](LICENSE).
