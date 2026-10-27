# Java integration QA harness

This directory contains an independent black-box test harness for the Python
workout application. Java is intentionally outside the application layers:
the harness starts the real Python entry points, supplies user input, and
verifies observable results such as exit codes, console output, and exported
files.

## Why Java?

The Python unit tests validate internal classes and use cases. This harness
uses a separate runtime and implementation to validate deployable behavior:

- process startup and shutdown;
- CLI input and exit-code contracts;
- simulation output;
- CSV export structure and duration validity; and
- Windows console encoding behavior.

It does not duplicate Python domain logic or import Python modules.

## Requirements

- Java 17 or newer;
- Python 3.11 or newer;
- the repository virtual environment at `.venv\Scripts\python.exe`, or
  `python` available on `PATH`.

## Run

From the repository root on Windows:

```powershell
.\qa-java\run.ps1
```

The script compiles the harness into `qa-java\out` and runs it. The harness
uses temporary directories for generated files and cleans them up when it
finishes.

To run it manually:

```powershell
Get-ChildItem -Recurse qa-java\src\main\java -Filter *.java |
  ForEach-Object { $_.FullName } |
  javac -d qa-java\out
java -cp qa-java\out qa.QaTestRunner
```

## Current expected findings

The first run is expected to report defects that the existing Python tests do
not cover:

1. The CLI can fail under the default Windows `cp1252` output encoding because
   it writes Unicode status symbols.
2. The CLI can print event-processing errors while still returning exit code
   `0`.
3. A stale event fixture can produce negative exported durations.

These are intentional integration assertions. A future application fix should
make the harness pass rather than weakening the assertions.
