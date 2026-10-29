# Outwrite

Python logging and a live status line that work together, across threads and
processes. Built on [Rich](https://github.com/Textualize/rich).

Requires Python 3.11+. Currently in alpha.

## Install

```sh
python -m pip install outwrite==0.1.0a1
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

Output goes to stderr. Outside a terminal, logs still appear but the status line
is hidden.

## License

[MIT](LICENSE).
