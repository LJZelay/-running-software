# CSE 4504 Team Project

## Work Assignments 

Feature 1 implementation:
Cliff - Runner Object - Domain Layer
Lesly - Workout Object - Application Layer
Joel - csvInput within aplication layer

CLI implementation:
Lesly - WorkoutService - Application Layer
Joel - WorkoutController - Controller Layer
cliff - check for any errors -User experience and testing

## Developer's Guide

### Prerequisites

This project requires Python 3.7 or higher. Applications itself uses only Python standard libraries. However, running tests requires pytest.


To check your Python version:
```bash
python --version
```

### Installation

1. **Clone the repository** (if you haven't already):
   ```bash
   git clone <repository-url>
   cd team-project-team4
   ```

2. **No additional dependencies to install** - The project uses only Python standard libraries:
   - `datetime` - For timestamp handling
   - `typing` - For type hints
   - `abc` - For abstract base classes

3. **Install testing framework (pytest):**
   - ```bash 
   python -m pip install pytest
   - If your repo includes `requirements.txt`, install all dependencies with:
   python -m pip install -r requirements.txt
```


### Running the Application

#### Main Command Line Application

To run the main demonstration program with hardcoded use case examples:

```bash
python main.py
```

This will execute all five use cases in sequence and display their outputs:
- Start Workout
- Scan NFC Tag (runner starts interval)
- Scan RFID Tag (lap detection)
- Get Rest Screen (view resting runners)
- End Workout

**Expected Output:** A formatted demonstration showing input parameters and return values for each use case.

#### Running Tests

To run the happy path integration test:

```bash
python -m application.test_happy_path
```

Or use the quick test command:
```bash
python -c "import sys; sys.path.insert(0, '.'); from application.test_happy_path import test_happy_path_interval_workout; test_happy_path_interval_workout(); print('✓ Happy path test PASSED')"
```

**Expected Output:** `✓ Happy path test PASSED`

This project uses **pytest** for unit and integration testing. 

Run all tests:

```bash
python -m pytest -v
```

Run only domain test:
```bash
python -m pytest -m domain -v
```

Run only application layer tests:
```bash
python -m pytest -m application -v
```

**Expected Output:** pytest will display `PASS/FAIL` results for each test

### Project Structure

```
team-project-team4/
├── main.py                     # Main entry point (demonstration)
├── domain/                     # Business logic layer
│   ├── runner.py              # Runner entity
│   ├── runnerSession.py       # Runner session entity
│   └── workout.py             # Workout entity
├── application/               # Application/use case layer
│   ├── use_cases/            # Use case implementations
│   │   ├── start_workout.py
│   │   ├── scan_nfc.py
│   │   ├── scan_rfid.py
│   │   ├── get_rest_screen.py
│   │   └── end_workout.py
│   ├── dto/                  # Data transfer objects
│   ├── repositories/         # Repository interfaces & implementations
│   ├── exceptions.py         # Application-level exceptions
│   ├── input_validation.py   # Input validation utilities
│   └── test_happy_path.py   # Integration tests
├── controller/               # Controller layer (future implementation)
└── externalInterface/        # External interfaces (future implementation)
```

### Troubleshooting

**Import Errors:**
- Make sure you're running commands from the project root directory
- Python must be able to find the project modules (current directory should be in `sys.path`)

**Python Version Issues:**
- Ensure you're using Python 3.7+ (required for type hints and dataclass features)

### Additional Documentation

- [Application Contract](application/APPLICATION_CONTRACT.md) - Application layer responsibilities and guarantees
- [Domain Changes Note](DOMAIN_CHANGES_NOTE.md) - Recent domain implementation details
- Layer-specific READMEs in each directory (`domain/`, `application/`, etc.) and also specific of what was implemented in application.