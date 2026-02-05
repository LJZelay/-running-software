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
