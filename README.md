# Outwrite

Python logs and live status updates, shared across processes.

Built on [Rich](https://github.com/Textualize/rich).

Requires Python 3.11+. Currently in alpha.

## Install

```sh
python -m pip install outwrite==0.1.0a2
```

## Quick start

Use a standard Python logger and update the status as you work:

```python
import logging
from outwrite import setup_output, status

logger = logging.getLogger("my_app")

with setup_output(logger=logger):
    logger.info("Starting")
    status.update("Processing files")
    # Do your work here.
    status.clear()
    logger.info("Done")
```

Logs appear above the status line. Cleanup happens automatically when the
`with` block ends.

## Multiple processes

Pass the output connection to each worker and call `setup_output(output)` there:

```python
import logging
import multiprocessing as mp
from outwrite import setup_output, status

logger = logging.getLogger("my_app")

def work(output):
    setup_output(output)
    logger.info("Worker started")
    status.update("Processing files")
    # Do your work here.
    logger.info("Worker finished")

if __name__ == "__main__":
    ctx = mp.get_context("spawn")
    with setup_output(logger=logger, mp_context=ctx) as output:
        process = ctx.Process(target=work, args=(output,))
        process.start()
        process.join()
```

Join workers before leaving the `with` block. Use the same named logger in the
parent and workers. Threads can use the configured logger and `status` directly.

See the [full example](examples/multiprocessing_demo.py) for handling Ctrl+C.

## Options

- `level=logging.DEBUG` includes debug logs.
- `show_status=False` hides the status line without hiding logs.
- `status.clear()` clears the line so it can be used again.
- `status.stop()` immediately hides status in the parent for the rest of the session.

Output goes to stderr. Outside a terminal, logs still appear but the status line
is hidden.

### Custom appearance

Pass `console_handler=your_rich_handler` to use your own RichHandler formatting,
console, and log level. Existing handlers still receive logs; a supplied console
handler is not added twice or closed by Outwrite.

For custom status styling, pass `status_renderer=format_status`, where
`format_status(text, console)` returns a Rich renderable. Both options are
parent-only; workers still call `setup_output(output)` without customization.

## License

[MIT](LICENSE).
