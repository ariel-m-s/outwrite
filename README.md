# Outwrite

Keep your logs readable and your progress visible.

Outwrite combines Python's standard logging with one live **status line**:
text that updates in place to show what your program is doing.
Logs stay above it, even when they come from different threads or processes.

For example:

```text
[10/30/26 12:00:00] INFO     Starting                         app.py:10
[10/30/26 12:00:02] INFO     Finished a batch                 app.py:14
Processing file 12 of 20
```

Update progress without filling your logs. All processes share the same status
line; each update replaces it. The line disappears when the `with` block ends.

Built on [Rich](https://github.com/Textualize/rich). Python 3.11+. Currently in alpha.

## Install

```sh
python -m pip install outwrite==0.1.0a3
```

## Quick start

Use a standard Python logger and update the status as you work:

```python
import logging

import outwrite

logger = logging.getLogger("my_app")

with outwrite.configure_console(logger=logger):
    logger.info("Starting")
    outwrite.status.update("Processing files")
    # Do your work here.
    outwrite.status.clear()
    logger.info("Done")
```

Logs appear above the status line. Outwrite finishes printing queued messages
and clears the status line when the `with` block ends.

## Multiple processes

The main process displays the logs and status. Pass the connection returned by
`outwrite.configure_console()` to each worker process, then call the same
function there:

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
