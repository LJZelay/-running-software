# Controller

This directory contains interface adapters that connect the outside world to your
application use cases.

Controllers translate external inputs into use case inputs and translate use case outputs
into something the outside world can understand.

## What belongs here
- CLI controllers (menu loops, parsing user input into use case calls)
- Web/API controllers (route handlers that call use cases)
- Presenters / view-model builders (optional)
- Input validation that is specific to the interface

## Flow
External input → Controller → Use Case (application) → Domain → Use Case result → Controller output

## Feature 2 Event Flow
- RFID/NFC events are translated into event envelopes at the controller boundary.
- RFID events are queued to a worker service for single-writer mutation safety.
- The worker invokes application use cases; domain remains the source of business decisions.

### Optional hardware source
- When `FEATURE2_RFID_REST_URL` is set, CLI can start a `reader_hardware` RFID adapter.
- Adapter payloads are normalized/validated before enqueueing to the worker.
- If not set, CLI behavior remains simulation-driven.
