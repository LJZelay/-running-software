# External Interface

This directory contains frameworks & drivers (outer layer) and concrete implementations
for anything that touches the outside world.

Think: databases, files, APIs, OS, frameworks, and other infrastructure details.

## What belongs here
- Repository implementations (e.g., `JsonTaskRepository`, `MongoTaskRepository`)
- Storage clients and file adapters
- Third-party integrations (email/SMS, external REST APIs)
- Framework setup utilities (config, env loading)
- Logging implementations (optional)

## Notes
- Implement the interfaces (ports) defined in `application` here.
- Keep these implementations replaceable (swap JSON storage → MongoDB without changing use cases).

## Feature 2 Hardware Integration
- `scanner_adapter.py` defines the transport contract (`ScannerAdapter`) used by the app boundary.
- `scanner_event_utils.py` builds validated event envelopes and applies tag normalization by type:
	- RFID tags follow `reader_hardware` canonical behavior (strip leading zeros).
	- NFC tags use strict local normalization (uppercase + separator-free + trim).
- `reader_hardware_adapter.py` provides an optional queue bridge to the local `reader_hardware` repo.

### Optional runtime wiring
- Set `FEATURE2_RFID_REST_URL` to enable the REST RFID adapter in CLI startup.
- If unset, CLI keeps simulation-only behavior.
