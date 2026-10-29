# Outwrite

Keep your logs readable and your progress visible.

Outwrite combines Python's standard logging with one live **status line**:
text that updates in place to show what your program is doing.
Logs stay above it, even when they come from different threads or processes.

Think **"what happened"** above, **"what's happening now"** below:

```text
[10/30/26 12:00:00] INFO     Starting                         app.py:10
[10/30/26 12:00:02] INFO     Finished a batch                 app.py:14
Processing file 12 of 20
```

Update progress without filling your logs. All processes share the same status
line; each update replaces it. The line disappears when the `with` block ends.

Use it for a file converter, a batch job, or a command-line tool that spends a
while working. Keep the milestones in your logs and the running count in status:

```text
Processing file 1 of 20  ->  Processing file 2 of 20  ->  ...
                     same line, updated in place
```

No separate progress bars or numbered tasks to manage: status is just text you
choose. Outwrite coordinates the output; [Rich](https://github.com/Textualize/rich)
handles how it looks.

Python 3.11+. Currently in alpha.

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

Logs appear above the status line. Outwrite finishes printing queued messages
and clears the status line when the `with` block ends.

Use `logger.info(...)`, `logger.warning(...)`, and the other logging methods as
usual. Call `outwrite.status.update(...)` whenever the current task changes.
Each log stays in the output; status is temporary.

## Multiple processes

More workers shouldn't mean a messier terminal.
The main process displays the logs and status. Pass the connection returned by
`outwrite.configure_console()` to each worker process, then call the same
function there:

```text
Main process -----+
Worker A ---------+--> Main process displays --> Logs + one status line
Worker B ---------+
```

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
    with outwrite.configure_console(logger=logger, mp_context=context) as console_connection:
        process = context.Process(target=work, args=(console_connection,))
        process.start()
        process.join()
```

Wait for workers to finish with `process.join()` before leaving the `with` block.
Use the same logger name in the main process and workers (`"my_app"` above).
The example uses the same multiprocessing context to create the connection and
worker, so they work together.

Threads need no extra setup: use the logger and `outwrite.status` directly.

There is one shared status line, not one per worker. If several workers update
it, the last update received is the one shown.

See the [full example](examples/multiprocessing_demo.py) for handling Ctrl+C.

## Options

- `console_level=logging.DEBUG` shows debug logs in the terminal without
  changing which messages are written to existing log files.
- `show_status=False` hides the status line without hiding logs.
- `outwrite.status.clear()` clears the line so it can be used again.
- `outwrite.status.disable()` hides the line and ignores later updates until the
  `with` block ends. Call it in the main process only.

By default, output goes to stderr. When output is redirected to a file or pipe,
logs are still written, but the live status line is hidden.

### Custom appearance

To customize log appearance, pass `console_handler=your_rich_handler`.
Outwrite uses that RichHandler's formatting, console, and log level.
Other logging handlers, such as file handlers, keep receiving messages.
Outwrite won't add your handler twice or close it when the `with` block ends.

To style the status line, pass `render_status=your_status_renderer`.
This function takes `(text, console)` and returns something Rich can display,
such as a `rich.text.Text` object.

Set these options in the main process only. Workers just call
`outwrite.configure_console(console_connection)`.

## License

[MIT](LICENSE).
