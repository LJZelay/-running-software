# Agent Contract: Project-Wide Rules

This file defines non-negotiable rules I must follow when working in this repository.
When instructions conflict, this contract takes precedence for project decisions.

## 1) Architecture Boundaries (Must Not Break)

1. Keep dependency direction as controller -> application -> domain.
2. Treat domain as pure business logic. No UI, I/O, CSV parsing, hardware calls, or framework glue in domain code.
3. Keep orchestration in application/use_cases. New features should be added through use cases, not ad-hoc controller logic.
4. Keep integration and adapters in externalInterface, including hardware/scanner adapters and CSV-side integration.
5. Preserve repository abstraction boundaries. Use cases depend on repository interfaces, not concrete classes.
6. Do not bypass contracts in application/APPLICATION_CONTRACT.md.

## 2) Coding Style and Design Standards

1. Target Python 3.11+ behavior.
2. Use type hints for public functions, use cases, DTOs, and service boundaries.
3. Keep naming consistent: snake_case for functions/variables, CamelCase for classes.
4. Prefer dataclasses and enums where already established by current patterns.
5. Use explicit custom exceptions for application/domain failures instead of generic exceptions.
6. Keep constructor-based dependency injection for use cases and services.
7. Preserve existing module responsibilities. Do not move logic across layers without clear reason.

## 3) Reliability and Crash-Prevention Rules

1. Validate external input at boundaries (CLI, CSV, scanner events, adapter input).
2. Fail explicitly with meaningful errors. Never hide invalid state with silent fallback behavior.
3. Guard null/empty data and invalid state transitions before mutating workout or runner state.
4. Make minimal, safe changes when touching concurrency-sensitive code.
5. Do not introduce shared mutable state across threads without clear ownership and locking strategy.
6. For RFID worker flows, preserve queue/worker ordering and existing thread-safety assumptions.

## 4) Testing and Change Validation

1. Any behavior-changing edit requires tests or updates to existing tests.
2. Run targeted pytest files for focused changes.
3. Run full pytest for cross-layer, workflow, or integration-impacting changes.
4. Do not claim success without reporting what was validated and what was not run.

## 5) Documentation and Source of Truth

I must align edits with these files:

1. README.md
2. DEVELOPER_GUIDE.md
3. HARDWARE_INTEGRATION.md
4. application/APPLICATION_CONTRACT.md
5. application/README.md
6. controller/README.md
7. externalInterface/README.md

If code and docs disagree, I should call it out and choose the safer interpretation until clarified.

## 6) Agent Behavior Promise

1. I will prioritize correctness and safety over speed.
2. I will not introduce shortcuts that violate layer boundaries.
3. I will not skip validation logic for convenience.
4. I will not silently ignore errors that can cause misinterpretation.
5. I will communicate assumptions when requirements are ambiguous.
6. I will prefer small, reversible changes and avoid unrelated refactors.
7. I will never change or add code that has not been approved yet.
8. I will never overcomplicate or overengineer solutions that are not needed.
9. I will use approaches that are efficient, simple, and easy to debug.

## 7) Scope Note

These rules apply to the full repository, including gui, controller, application, domain, and externalInterface paths.