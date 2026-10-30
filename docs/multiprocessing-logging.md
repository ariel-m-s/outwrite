# Python multiprocessing logging with a live status line

A batch job can be busy without saying anything useful. Logging every progress
update fixes the silence, but leaves you scrolling past hundreds of updates to
find the messages you actually need.

There are two separate jobs here:

- **Logs:** a history of events worth keeping.
- **Status:** what the application is doing now, replaced as work progresses.

When multiple processes produce both, it helps to give one process responsibility
for the console.

## The standard Python logging approach

Python provides the building blocks for centralized multiprocessing logging:

1. Create a multiprocessing queue.
2. Attach a [`QueueHandler`](https://docs.python.org/3/library/logging.handlers.html#queuehandler)
   to each process's logger.
3. Use a listener in the main process to dispatch records to output handlers.
   [`QueueListener`](https://docs.python.org/3/library/logging.handlers.html#queuelistener)
   provides this pattern for log records.
4. Join producers, drain pending records, and close the listener and queue.

For threads, standard logging already provides thread-safe handlers. A queue
can still centralize handler work, but it isn't necessary just to make ordinary
thread logging safe.

See Python's [logging cookbook](https://docs.python.org/3/howto/logging-cookbook.html#logging-to-a-single-file-from-multiple-processes)
for the queue-based multiprocessing pattern.

## Adding Rich logging and a live display

[RichHandler](https://rich.readthedocs.io/en/stable/logging.html) formats log
records, while [Rich's live display](https://rich.readthedocs.io/en/stable/live.html)
can show changing status with logs above it. Rich supplies the rendering; your
application still needs to coordinate message delivery and resource ownership.

You can wire these pieces together yourself. Keep rendering in the main process,
send status updates as well as log records to it, and arrange shutdown so final
messages arrive before the display closes.

## What outwrite handles for you

`outwrite` packages that coordination: one shared queue for log records and status
text, one listener in the main process, a Rich console, and cleanup when the
console context ends. It uses its own listener to handle both kinds of message.

Install with `pip install outwrite` (Python 3.11+). The
[README's multiprocessing snippet](../README.md#logging-across-multiple-processes-and-threads)
shows the connection handoff. The
[runnable example](../examples/multiprocessing_demo.py) also handles interruption
and checks the child process's exit code.

Use the same multiprocessing context for the queue and child processes.
`outwrite` defaults to `spawn` for its queue; it doesn't change your application's
global start method. Use `spawn` or `forkserver`, not `fork`.

## When it fits, and when it doesn't

- **Concurrent CLI logging:** collect records in one console. Set
  `show_status=False` if you don't need status.
- **Long-running jobs:** keep milestones in the log and put changing progress
  text on the status line.
- **Existing logging setups:** choose a named logger; existing parent file
  handlers still receive logs, but not status text.
- **Ordering:** output follows queue-receipt order, not a global timestamp sort.
- **Status:** one shared text line, not an automatic progress bar or independent
  display for every task. The last update received is shown.
- **Redirection:** when stderr isn't a terminal, logs remain but live status is
  hidden.

If you already have a queue-based logging setup and a Rich live display you're
happy with, you may not need another dependency. `outwrite` is for the cases
where you'd rather use those pieces than maintain the glue between them.
