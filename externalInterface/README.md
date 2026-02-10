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
