# Outwrite launch kit

## One-line pitch

Outwrite adds a live, plain-text status line to Python logging, keeping progress
visible while log messages—including messages from worker processes—stay
readable.

## Short description

Keep your logs readable and your progress visible. Outwrite combines Python's
standard logging with one live status line for CLI applications. Update the
text from your code, keep your existing file handlers, and route messages from
multiple processes to the same console.

## Ready-to-post announcement

I made Outwrite, a small Python library for CLIs that need to show what they're
doing without turning the terminal into a wall of progress updates.

It adds one live status line alongside standard logging. Log messages stay
readable above it, and worker processes can share the same console output.
The status is text your code provides, not an automatic progress bar.

It's early and in alpha, so feedback is very welcome.

Install: `python -m pip install outwrite==0.1.0a3`
Project: https://github.com/ariel-m-s/outwrite

## Short social post

I made Outwrite: a small Python library that keeps one live status line visible
alongside readable logs, even with multiple worker processes. You provide the
status text; it isn't an automatic progress bar. Early alpha; feedback welcome:
https://github.com/ariel-m-s/outwrite

## Demo

Run the short multiprocessing example from the repository root:

```sh
python examples/quick_demo.py
```

For a recording, use a terminal window around 90 columns wide, start the
command with a clean prompt, and capture the few seconds until “All files
processed” appears. Keep the output unedited so viewers can see ordinary logs
and the status line working together. The example uses simulated work and
requires no external services.

## Suggested first audiences

- Python CLI and developer-tool maintainers
- People running batch, ETL, or file-processing jobs
- Projects whose multiprocessing workers currently produce hard-to-follow
  terminal output

When sharing, say what problem prompted the project, show the demo, and ask
people what would make it useful in their own workflow. Be clear that the
package is currently alpha.
