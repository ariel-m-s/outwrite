# Outwrite

**Standard Python logging and one live status line, across threads and processes.**

Outwrite connects Python's logging module to [Rich](https://github.com/Textualize/rich)
and relays worker output to one renderer in the parent process. Use your existing
processes and ordinary loggers. No queue management in application code.

This is an early alpha. APIs may change; it is not production-certified.
Python 3.11+ is required. Rich is the only runtime dependency.

## Installation

The first release is a prerelease:

```sh
python -m pip install outwrite==0.1.0a1
```

Or use `python -m pip install --pre outwrite` to allow the latest prerelease.
These commands become available once the release is published to PyPI.

To install from a local checkout:

```sh
python -m pip install .
```

## One process

```python
import logging
from outwrite import setup_output, status

logger = logging.getLogger("my_app")

with setup_output(logger=logger) as output:
    logger.info("Starting")
    status.update("Processing files")
    # Do some work.
    status.clear()
    logger.info("Done")
```

## Worker processes

Pass the connection returned by the parent to each worker. Call the **same**
setup function inside each worker:

```python
import logging
import multiprocessing as mp
import signal
from outwrite import setup_output, status

logger = logging.getLogger("my_app")

def work(output, stop):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    setup_output(output)
    logger.info("Worker started")
    for index in range(10):
        if stop.is_set():
            break
        status.update(f"Processing file {index + 1}")
        stop.wait(0.1)

if __name__ == "__main__":
    ctx = mp.get_context("spawn")
    stop = ctx.Event()
    with setup_output(logger=logger, mp_context=ctx) as output:
        process = ctx.Process(target=work, args=(output, stop))
        process.start()
        try:
            process.join()
        finally:
            stop.set()
            process.join()
```

Always join workers and logging threads **inside** the parent context. On exit,
Outwrite drains queued messages, clears the status, and releases its resources.
Exit cleanup is also registered as a fallback; it does not stop or join workers
for you. Forced process termination can lose messages or damage multiprocessing
queues, so prefer a cooperative worker stop in real applications.

See [the runnable example](https://github.com/ariel-m-s/outwrite/blob/main/examples/multiprocessing_demo.py).

## API

- `setup_output(logger=logger, level=logging.INFO, show_status=True, mp_context=ctx)`
  starts parent output and returns an `OutputConnection` context handle.
- `setup_output(output)` connects a worker. The parent's logger name and status
  setting are carried by the connection; keyword options are for parent setup.
- `status.update(text)` replaces the status line. `None` or `""` clears it.
- `status.clear()` clears the line without ending the session.

Status calls are safe from threads. Only one session and one status line are
active per process; concurrent writers replace the same line. Status calls before
setup or after parent cleanup raise `RuntimeError`.

The console uses stderr. Status is automatically disabled outside terminals;
logs still appear. `show_status=False` disables only status, and `level` controls
only the Rich console handler. Use integer logging levels, such as `logging.DEBUG`.

## Logging behavior

Only the selected **named logger** and its propagating descendants are routed.
The root logger and unrelated loggers are not configured. Child loggers with
their own handlers or `propagate=False` retain their normal logging behavior.

Existing handlers on the selected logger also receive records in the parent.
For example, attach a standard `logging.FileHandler` before setup to retain file
logging. Outwrite does not close your handlers. It adds a Rich console handler,
so remove an existing console handler yourself if you do not want duplicate
console output. The logger's original handlers, level, and propagation are
restored when the parent context exits.

Records pass through standard `QueueHandler` preparation: exception tracebacks
become message text. Extra record attributes must be picklable. Cross-process
delivery is asynchronous; use a cooperative worker shutdown and join workers to
flush their messages. Ordering between different producers is not guaranteed.

The default queue context is `spawn`. If using `forkserver`, pass that same
context to setup and use it to create processes. `fork` is deliberately unsupported
because the parent has an active rendering thread. Do not send a connection to
an already-running pool; pass it when creating workers or through a pool initializer.

Rendering failures are reported to stderr and raised when the parent context
exits. Standard logging handlers retain their usual error-reporting behavior.
No arbitrary stdout/stderr capture is performed.

## Why not just Rich?

Rich already supplies the columns, colors, links, and live display. Outwrite adds
the connection between existing worker processes, standard logging, and one live
status line. It is not a new renderer, process pool, or progress-bar framework.

## Development

```sh
python -m pip install -e .
python examples/multiprocessing_demo.py
python -m pip install build
python -m build
```

No persisted test suite is included in this initial iteration. Add regression
tests before a production release, particularly for process shutdown and terminal
cleanup.

The initial wheel was verified on macOS ARM64 with Python 3.13.7 and 3.14.0,
including spawn/forkserver workers and real-terminal Ctrl+C cleanup. Python
3.11/3.12 and other operating systems have not yet been runtime-tested.

## License

MIT. The initial implementation adapts output coordination developed in Firefly,
with its author's permission.

## Publishing

Maintainers use PyPI Trusted Publishing; no permanent upload token is stored in
GitHub. The GitHub environment `pypi` requires approval before publication.

1. Update the version in `pyproject.toml`, and commit and push the change.
2. Create a GitHub release with a matching tag, such as `v0.1.0a1`.
   Mark alpha/beta/RC versions as prereleases.
3. Review the build job and approve the `pypi` environment deployment.
4. Verify the uploaded version on PyPI and install it in a fresh environment.

The workflow builds and validates the distributions before publishing. Release
files cannot be replaced on PyPI; use a new version to correct a release.
The initial pending publisher must be configured on PyPI for repository
`ariel-m-s/outwrite`, workflow `publish.yml`, and environment `pypi`.
