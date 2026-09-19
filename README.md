#runnning software

## What you need

- Python 3.11+ recommended
- pip

## Setup

Run from the project root:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the program

### 1) Demo flow

Runs a built-in interval workout example:

```bash
python main.py
```

### 2) CSV simulation flow

Uses athletes and event input files:

```bash
python simulation.py data/athletes.csv data/events.csv
```

### 3) CLI

Interactive mode:

```bash
python controller/cli.py
```

One-command mode examples:

```bash
python controller/cli.py help
python controller/cli.py "2 data/athletes.csv"
python controller/cli.py "status"
```

## Run tests

Run all tests:

```bash
pytest
```

Optional (single test file):

```bash
pytest tests/test_integration/test_workout_flow.py
```

Note: pytest percentages (example: 55%) show progress through collected tests, not a grade.

## Directory guide

- `application/` - use cases, DTOs, validation, repositories
- `controller/` - command-line controller and command handling
- `domain/` - core business entities and state
- `externalInterface/` - CSV parsing and external adapters
- `data/` - sample CSV files (athletes, events, summaries)
- `tests/` and `test/` - automated tests
- `.github/workflows/` - CI workflow (runs pytest)
- `main.py` - simple end-to-end demo
- `simulation.py` - CSV-driven simulation entry point

## Included docs

- [Application Contract](application/APPLICATION_CONTRACT.md)
- [Application Notes](application/README.md)
- [Controller Notes](controller/README.md)
