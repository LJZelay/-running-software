# Application

This directory contains the application use cases that coordinate domain entities to accomplish a function or a goal.

## What belongs here
- Use case / service classes
- Application-level policies and workflows
- Input/output models (DTOs) used by controllers/adapters
- Interfaces (ports) that the use cases depend on

## NOTE
Controllers call use cases. Use cases return plain data (DTOs/results) that controllers
can present however they want (CLI, web API, etc.).

APPLICATION LAYER (Orchestration & use cases)


What belongs in Application
1. Use Case Services

These coordinate domain objects.

Examples:

StartWorkoutUseCase

Accepts config + roster

Calls domain to start workout

Persists initial state

ProcessNfcScanUseCase

Receives NFC tag ID + timestamp

Finds matching runner

Asks domain: “Can this runner start now?”

Saves result

ProcessRfidDetectionUseCase

Receives RFID tag ID + timestamp

Determines lap vs finish

Tells domain to update runner

Triggers rest start if needed

EndWorkoutUseCase

Validates workout can end

Locks data

Persists final state

2. Application Interfaces (Ports)

These are abstractions, not implementations.

Examples:

RunnerRepository

WorkoutRepository

Clock

HardwareEventSource

The application depends on these — not the concrete implementations.

3. Mapping & Coordination

Application layer:

Translates raw input → domain intent

Calls domain methods

Handles errors

Logs events

Saves state

It does not enforce business rules itself.
