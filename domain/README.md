# Domain

This directory contains the core business objects and rules of the system.

## What belongs here
- Entities / domain models (e.g., `Interval`, `Runner`, `Workout`)
- Business invariants and rule-checking methods (e.g., validation that must always hold)
- Value objects (immutable types like `Duration`, `Email`, etc.)
- Domain-specific exceptions


What belongs in Domain
1. Entities (core objects with behavior)

These are stateful and rule-enforcing.

Runner

id

name

NFC tag ID

RFID tag ID

current state

interval history

rest history

Domain behavior

Can transition states

Cannot be in two states at once

Cannot start if already running

Workout

workoutId

runners

workout configuration

start mode (GROUP / INDIVIDUAL)

workout status (ACTIVE / COMPLETED)

Domain behavior

Can start

Can end

Cannot end twice

Cannot accept events after completion

Interval

interval number

start timestamp

end timestamp

lap timestamps

RestPeriod

start timestamp

end timestamp

configured rest duration

WorkoutConfiguration

interval distance

rest duration

laps per interval

total intervals

Domain behavior

Validates constraints (positive distance, etc.)

2. Value Objects (small, immutable concepts)

Examples:

Timestamp

Duration

RunnerId

WorkoutId

StartMode

These have no identity, just meaning.

3. Domain Rules & Invariants

This is huge.

Examples:

A runner cannot start an interval unless READY or NOT_STARTED

Rest starts immediately after an interval finishes

NFC scans are ignored unless runner is eligible

RFID finishes only count after lap threshold is met

Start mode is immutable after workout starts

These rules live in domain methods, not application code.

4. Domain Events (optional but powerful)

Examples:

RunnerStartedInterval

RunnerFinishedInterval

RunnerStartedRest

RunnerBecameReady


