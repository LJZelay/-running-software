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
