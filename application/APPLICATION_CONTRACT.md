#This is a brief explaination of what the application contract is and what it should contain. It should be a high level document that outlines the responsibilities and guarantees of the application layer, without going into implementation details. It should also include any important design decisions or constraints that the application layer must follow.

# Application Layer Contract

This document formalizes the guarantees, boundaries, and responsibilities of the Application Layer.

## Core Responsibilities

The application layer orchestrates domain entities and translates between external requests and domain behavior. It does NOT implement business logic.

### What the Application Layer DOES

- Accept inputs from controllers (primitives only)
- Validate application-level requests (positive IDs, non-empty strings)
- Load domain objects via repositories
- Call domain methods in the correct sequence
- Translate domain objects into DTOs
- Handle application-level errors (not found, invalid request)
- Save domain state back to persistence via repositories

### What the Application Layer DOES NOT Do

- Enforce business rules (domain's job)
- Calculate timings or state transitions (domain's job)
- Inspect domain internals (state, collections, object properties)
- Return domain objects directly to callers
- Decide persistence strategies (repository's job)
- Handle hardware events directly
- Provide UI logic or rendering

## Time Ownership (CRITICAL)

**The Domain owns time.**

- The application passes timestamps received from controllers/sensors to domain methods
- The domain decides when and how to use timestamps
- The domain internally may call `datetime.now()` for rest calculations
- Controllers/hardware must provide timestamps; application passes them through
- This ensures testability and replay capability

## State Representation

**State is opaque to the application layer.**

- The domain exposes state as strings (`workout.status`)
- The application does NOT interpret or compare state values
- Domain query methods (e.g., `workout.get_runner_counts()`) abstract away state details
- If state changes, only domain and DTOs change—application code stays stable

## Repository Contract

**Repositories are swappable interfaces.**

```python
class WorkoutRepository(ABC):
    def get_by_id(self, workout_id: int) -> Optional[object]
    def save(self, workout: object) -> None
```

- Repository implementations are NOT in this layer
- Repositories live in externalInterface (example: JsonWorkoutRepository, SqlWorkoutRepository)
- The application never knows how data is stored
- Multiple implementations can coexist without changing application code

## DTO Guarantees

DTOs are immutable, read-only views:

- `RunnerRestView` → Runner resting status
- `WorkoutStatusView` → Workout state + runner counts
- `RunnerSummaryView` → Runner session summary

**DTOs never leak domain objects.** Controllers and UI receive only DTOs.

## Input Validation

Application-level validation guards against clearly invalid inputs:

- `validate_positive_int(value, field_name)` — Rejects negative/zero IDs
- `validate_non_empty_string(value, field_name)` — Rejects empty strings/whitespace

**This is NOT business rule validation.** Domain rules (e.g., "cannot start if already running") are checked inside the domain, not here.

## Use Case Responsibilities

Each use case is a single orchestration flow:

```
Input → Validate → Load → Call Domain → Save → DTO → Return
```

- `StartWorkoutUseCase` — Activate workout
- `EndWorkoutUseCase` — Complete workout
- `ScanNFCUseCase` — Record NFC event, return status
- `ScanRFIDUseCase` — Record RFID event, return status
- `GetRestScreenUseCase` → Retrieve resting runners, return DTOs

No business decisions are made in use cases. They coordinate.

## Error Handling

Application layer raises two error types:

- `WorkoutNotFoundError` — Requested workout does not exist
- `InvalidApplicationRequestError` — Invalid input (negative ID, empty string, wrong type)

Domain errors bubble up unchanged. Controllers handle all exceptions.

## Stability & Maintenance

**After initial implementation, the application layer should rarely change.**

Changes happen only when:

1. New domain methods are added → New use cases can call them
2. New DTOs are needed → New use cases can return them
3. New workflow patterns emerge → New use cases can orchestrate them

**Never change:**

- Use case class names or method signatures
- DTO field names
- Repository interfaces
- The boundaries between layers

If you feel pressure to modify the application layer for business logic, stop. That logic belongs in the domain.

## Testing

The `test_happy_path.py` demonstrates a complete flow:

1. Create domain objects
2. Populate repository
3. Execute use cases
4. Verify DTOs are correct
5. Verify domain state changed

This test does not mock anything. It runs the real code.

## Backward Compatibility Notes

Future extensions:

- New runners can be added
- New sensors can feed events
- New UI views can consume DTOs
- Storage can move from JSON to SQL to cloud

**All of these are possible without touching this layer** because repositories are abstract and use cases depend on domain interfaces, not implementations.
