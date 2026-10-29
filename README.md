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

Update progress without filling your logs. Workers share the same status line;
each update replaces it. The line disappears when you're done.

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

Logs appear above the status line. Cleanup happens automatically when the
`with` block ends.

## Multiple processes

Pass the console connection to each worker and configure it there:

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
    ctx = mp.get_context("spawn")
    with outwrite.configure_console(logger=logger, mp_context=ctx) as console_connection:
        process = ctx.Process(target=work, args=(console_connection,))
        process.start()
        process.join()
```

Join workers before leaving the `with` block. Use the same named logger in the
parent and workers. Threads can use the configured logger and `outwrite.status` directly.

See the [full example](examples/multiprocessing_demo.py) for handling Ctrl+C.

## Options

- `console_level=logging.DEBUG` includes debug logs in the console, without
  changing existing file handlers.
- `show_status=False` hides the status line without hiding logs.
- `outwrite.status.clear()` clears the line so it can be used again.
- `outwrite.status.disable()` immediately hides status in the parent and ignores further
  updates for the rest of the session.

Output goes to stderr. Outside a terminal, logs still appear but the status line
is hidden.

### Custom appearance

Pass `console_handler=your_rich_handler` to use your own RichHandler formatting,
console, and log level. Existing handlers still receive logs; a supplied console
handler is not added twice or closed by Outwrite.

For custom status styling, pass `render_status=your_status_renderer`, where
`your_status_renderer(text, console)` returns a Rich renderable. Both options are
parent-only; workers call `outwrite.configure_console(console_connection)` without customization.

## License

[MIT](LICENSE).
