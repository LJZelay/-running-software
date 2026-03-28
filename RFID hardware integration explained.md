
Date: 2026-03-28

Scope Boundary: This report evaluates backend functionality and Feature 2 design functionality only (NFC/RFID event pipeline, state transitions, and backend architecture boundaries).


## 1) What We Changed and Why (Only What Was Necessary)

### Claim
Code changes were necessary to make hardware event handling safe, deterministic, and observable.

### Evidence
Main updated areas:
- controller/cli.py: routes normalized hardware payloads into the worker and dispatches to NFC/RFID use cases.
- externalInterface/scanner_event_utils.py: normalization + timestamp validation + drift guard.
- application/services/rfid_worker_service.py: queueing, single-writer processing, overflow handling, health metrics.
- domain/runnerSession.py: duplicate/out-of-order/invalid timestamp protections at state-transition level.
- domain/workout.py: active-gate and unknown-tag safe handling.
- application/rfid_contracts.py: explicit accepted/ignored decision and reason contracts.

### Reasoning
These changes were not feature creep. They were required to prevent bad scanner data from corrupting workout state and to make behavior measurable under load.

### Analysis
This directly supports the main project goal: reliable, correct interval tracking in realistic noisy conditions.

---

## 2) What Changed by Layer (Domain, Application, External Interface)

### Claim
Feature 2 hardening changes were implemented at the correct architecture boundaries.

### Evidence
Domain layer changes:
- domain/runnerSession.py
	- Added duplicate suppression and out-of-order timestamp guards for NFC/RFID.
	- Added invalid timestamp rejection paths with no state mutation.
	- Preserved interval/rest transition rules inside domain state machine.
- domain/workout.py
	- Enforced active-workout gate before accepting NFC/RFID events.
	- Added safe unknown-tag handling for RFID as ignored decision.

Application use-case changes:
- application/use_cases/group_start.py
	- Group start activates workout and prepares selected runners (READY) without auto-starting intervals.
- application/use_cases/scan_nfc.py
	- Validates request, routes NFC events to domain, maps status to DTO.
- application/use_cases/scan_rfid.py
	- Validates request, routes RFID events to domain, maps accepted/ignored decision and reason into contract DTO.
- application/rfid_contracts.py
	- Defines explicit accepted/ignored decision + reason taxonomy used across worker/use-case boundary.

External interface changes:
- externalInterface/scanner_event_utils.py
	- Normalizes tag payloads and validates timestamps/drift before enqueue.
- controller/cli.py
	- Accepts scanner payloads, builds validated envelopes, and dispatches to worker/use cases.
- application/services/rfid_worker_service.py
	- Single-writer worker model, bounded queue, drop-oldest overflow, and health/latency metrics.

### Reasoning
This keeps business rules in domain, orchestration in use cases, and input normalization at external boundaries.

### Analysis
The implementation aligns with clean architecture while making Feature 2 robust against noisy hardware streams.

---

## 3) How it was Tested (Fast Summary)

### Claim
Testing covered logic correctness, integration correctness, and stress behavior.

### Evidence
Targeted matrix executed in this order:
1. Domain/External/Worker
- tests/test_domain/test_runner_session.py
- tests/test_external/test_scanner_event_utils.py
- tests/test_application/test_rfid_worker_service.py

2. Integration
- tests/test_integration/test_feature2_rfid_pipeline.py
- tests/test_integration/test_workout_flow.py

3. Controller/Adapter
- tests/test_controller/test_hardware_scanner_dispatch.py
- tests/test_external/test_reader_hardware_adapter.py

Then full regression:
- pytest -q

New tests added for this hardening phase and why they were necessary:
- tests/test_integration/test_feature2_rfid_pipeline.py
	- test_unknown_rfid_is_ignored_without_mutating_sessions
	- test_duplicate_rfid_burst_only_records_first_lap_within_debounce_window
	- Why: verify ignored-path safety and burst duplicate resilience in end-to-end flow.
- tests/test_controller/test_hardware_scanner_dispatch.py
	- test_on_hardware_scanner_payload_enqueues_normalized_event
	- test_on_hardware_scanner_payload_invalid_timestamp_raises_and_does_not_enqueue
	- Why: verify controller boundary correctness (good payloads enqueue, bad payloads blocked).
- tests/test_external/test_reader_hardware_adapter.py
	- test_reader_hardware_queue_adapter_burst_preserves_fifo_order
	- Why: verify adapter queue pump preserves ordering under burst load.

### Reasoning
This order validates foundations first, then end-to-end flow, then boundaries, then project-wide safety.

### Analysis
It is both deep enough for confidence and simple enough for repeatable team use.

---

## 4) Runtime and Hardening Metrics (What We Can Measure)

### Claim
Feature 2 behavior is observable under normal and burst conditions.

### Evidence
Worker runtime metrics available:
- events_processed
- events_dropped
- queue_utilization_percent
- queue_drops_per_minute
- processing_latency_ms

How runtime/hardening metrics were collected:
- Test-run metrics (pass/fail/runtime) came from targeted pytest blocks and full regression summary output.
- Worker metrics came from the worker health status contract after deterministic probe replay.
- Decision-quality metrics came from accepted/ignored outcomes and reason distribution during probe replay.
- State-integrity metrics came from final runner snapshots (state, interval count, lap count, rest count).

Probe snapshot from this pass:
- events_processed: 5
- events_dropped: 9
- queue_utilization_percent: 0.0
- queue_drops_per_minute: 674.16
- processing_latency_ms: 51.2

Decision-quality snapshot:
- accepted_total: 2
- ignored_total: 4
- ignored reasons: duplicate, out-of-order, unknown-tag, invalid timestamp

### Reasoning
If we can measure drops, latency, and decision reasons, we can monitor real-world quality and react quickly.

### Analysis
This is operationally mature compared to black-box behavior.

---

## 5) How To Test With Real Hardware

### Claim
If NFC and RFID hardware are available, we can run true end-to-end validation for Feature 2.

### Evidence
Suggested hardware test flow:
1. Start app and worker:
- python controller/cli.py

2. Connect hardware adapters (as configured):
- RFID REST reader endpoint via env var FEATURE2_RFID_REST_URL
- NFC adapter via FEATURE2_ENABLE_NFC=1 (or FEATURE2_NFC_ENABLED=1)

3. Execute real scan sequence:
- Add athletes / group.
- Group start.
- NFC scan to start interval.
- RFID scans for laps and interval finish.
- Include duplicate and out-of-order scan attempts intentionally.

4. Verify outcomes:
- Valid events update state.
- Invalid/noisy events are ignored safely.
- Rest/running counts update correctly.
- Worker health metrics show process/drop/latency values.
- Payloads that are out-of-contract are rejected at boundary validation and do not mutate state.

### Reasoning
This proves complete signal path: hardware -> adapter -> normalized envelope -> worker -> use case -> domain state.

### Analysis
If this path passes and regression remains green, Feature 2 is real-world ready.

---

## 7) How To Test Without Hardware (Still High Confidence)

### Claim
We can confidently validate Feature 2 even without physical readers.

### Evidence
Run automated suite:
- python -m pytest -q tests/test_domain/test_runner_session.py tests/test_external/test_scanner_event_utils.py tests/test_application/test_rfid_worker_service.py
- python -m pytest -q tests/test_integration/test_feature2_rfid_pipeline.py tests/test_integration/test_workout_flow.py
- python -m pytest -q tests/test_controller/test_hardware_scanner_dispatch.py tests/test_external/test_reader_hardware_adapter.py
- python -m pytest -q

If no hardware is available at all:
- Drive event flow through CLI simulation and test adapters.
- Use integration tests as the main source of truth for end-to-end behavior.
- For a new sensor type, add/extend adapter contract tests and dispatch tests before hardware arrives.

Why this is enough:
- Integration tests simulate complete event streams.
- Controller tests validate dispatch and envelope handling.
- Worker tests validate queue pressure, FIFO behavior, and metrics.
- External tests validate normalization and drift protection.

### Reasoning
This gives deterministic, repeatable proof without requiring physical devices on every developer machine.

### Analysis
Team velocity stays high while release confidence remains strong.

---

## 8) Did We Break Existing Code?

### Claim
No, we did not break existing behavior.

### Evidence
- Full regression suite: 91/91 passed.
- No failing nodes in final run.

### Reasoning
Regression green is the objective project-wide safety gate.

### Analysis
Feature 2 improvements are additive hardening, not destructive changes.

---

## 9) Libraries and Tools Used

### Claim
Implementation stayed lean and maintainable.

### Evidence
- Testing: pytest
- Core runtime internals: threading, queue, logging, dataclasses
- Reader workspace dependencies available: requests, flask, sllurp, pyscard

### Reasoning
Mostly standard library for core logic reduces dependency risk.

### Analysis
This improves long-term maintainability and onboarding.

---

## 10) Residual Risks (Bounded)

### Claim
Remaining risks are known, bounded, and do not invalidate backend scope readiness.

### Evidence
- Probe metrics are short-run diagnostics from one pass, not long-run throughput guarantees.
- Determinism evidence is strongest for ordered replay streams; broader concurrent interleaving coverage can be expanded.
- Drift rejection is enforced at scanner-envelope boundary validation; direct internal call paths are validated primarily by use-case and integration tests.

### Reasoning
Documenting what is validated and what is not prevents over-claiming and makes sign-off credible.

### Analysis
Current residual risks are hardening opportunities, not blockers for Feature 2 backend functionality.

