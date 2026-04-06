# Hardware Integration Guide

This document explains how to integrate real RFID/NFC hardware into the system.

## Current Architecture

The system currently uses **simulated hardware input** via the runner dashboard UI. Athletes click a "Simulate Lap" button to simulate RFID tag scans, which triggers the domain recording logic.

### Current Flow (Simulation)
```
RunnerView Button Click (_simulate_lap) 
    → ScanRFIDUseCase.execute(workout_id, runner.rfid_tag, timestamp)
    → Workout.record_rfid_event()
    → Repository saves
    → Coach polling fetches updated data
    → Tables/Charts update
```

## Hardware Integration Points

### Option 1: Direct Hardware Reader Integration (Recommended)

Replace the simulation button with a hardware listener:

#### Step 1: Create a Hardware Reader Service
File: `externalInterface/hardware_reader.py`

```python
class RFIDHardwareReader:
    """Listens to real RFID hardware and reports scan events."""
    
    def __init__(self, port: str, scan_callback):
        """
        Args:
            port: Serial port (e.g., 'COM3', '/dev/ttyUSB0')
            scan_callback: Function to call with (tag_id, timestamp)
        """
        self.port = port
        self.scan_callback = scan_callback
        self.reader = None  # Initialize your hardware library here
    
    def start(self):
        """Start listening for RFID scans."""
        # Your hardware library initialization
        pass
    
    def stop(self):
        """Stop listening."""
        pass
```

#### Step 2: Update Runner View to Use Hardware

In `GUI/runner_view.py`, modify initialization:

```python
def __init__(self, ..., hardware_reader=None, ...):
    ...
    self.hardware_reader = hardware_reader
    if self.hardware_reader:
        self.hardware_reader.scan_callback = self._on_rfid_scanned
        self.hardware_reader.start()
    ...

def _on_rfid_scanned(self, tag_id: str, timestamp: str):
    """Called by hardware reader when tag is scanned."""
    try:
        if self.scan_rfid_uc:
            self.scan_rfid_uc.execute(
                self.workout_id,
                tag_id,
                timestamp
            )
        self.lap_count += 1
        self.lap_label.config(text=f"Laps: {self.lap_count}")
        self.feedback.config(text=f"RFID: {tag_id} recorded")
    except Exception as e:
        self.feedback.config(text=f"Error: {str(e)[:40]}")
```

#### Step 3: Update Main to Create Hardware Reader

In `GUI/main.py`:

```python
# Option: Create hardware reader if real hardware is available
hardware_reader = None
try:
    hardware_reader = RFIDHardwareReader(port="COM3", scan_callback=None)
except:
    # Fall back to simulation if hardware unavailable
    pass

# Pass to RunnerView
RunnerView(
    ...,
    hardware_reader=hardware_reader,
    ...
)
```

### Option 2: Central Event Bus (For Multiple Readers)

If you have multiple RFID readers or complex hardware:

```python
# Create event bus
class HardwareEventBus:
    def __init__(self, scan_use_case, nfc_use_case):
        self.scan_rfid_uc = scan_use_case
        self.scan_nfc_uc = nfc_use_case
        self.listeners = []
    
    def on_rfid_scan(self, workout_id: int, tag_id: str, timestamp: str):
        """Called by hardware reader."""
        self.scan_rfid_uc.execute(workout_id, tag_id, timestamp)
    
    def on_nfc_scan(self, workout_id: int, tag_id: str, timestamp: str):
        """Called by NFC hardware reader."""
        self.scan_nfc_uc.execute(workout_id, tag_id, timestamp)
```

## Use Cases Already Ready for Hardware

These use cases are designed to accept direct hardware input:

1. **ScanRFIDUseCase** (`application/use_cases/scan_rfid.py`)
   - Signature: `execute(workout_id, rfid_tag_id, timestamp, use_event_time=False)`
   - Used when runner's RFID tag passes reader

2. **ScanNFCUseCase** (`application/use_cases/scan_nfc.py`)
   - Signature: `execute(workout_id, nfc_tag_id, timestamp, use_event_time=False)`
   - Used when runner's NFC tag is detected

## Key Points for Integration

### Tag Matching
- Runners are loaded from CSV with unique `rfid_id` and `nfc_id`
- When hardware scans a tag, the scanned ID must match exactly
- Example CSV format:
  ```csv
  name,nfc_tag,rfid_tag
  Alice Johnson,NFC001,RFID001
  Bob Smith,NFC002,RFID002
  ```

### Timestamp Handling
- Pass ISO format timestamps: `datetime.now().isoformat()`
- Or `set use_event_time=True` if hardware provides timestamp

### Error Handling
- Invalid tag IDs → Use case will raise exception (handled gracefully)
- Network/port errors → Wrap in try/catch, fall back to simulation

## Testing Without Real Hardware

Keep the simulation button active during development:

```python
# In runner_view.py
def _setup_ui(self):
    # Always show simulate button for testing
    ttk.Button(..., text="Simulate Lap", command=self._simulate_lap).pack()
    
    # Also: If real hardware connected, disable this button
    if self.hardware_reader:
        self.simulate_lap_btn.config(state=tk.DISABLED)
```

## Coach-Side Hardware

For coach-side hardware (e.g., start/stop button):

```python
# In coach_view.py, add method
def on_hardware_start_signal(self):
    self._on_start_workout()

def on_hardware_stop_signal(self):
    self._on_end_workout()

# Connect hardware listener
hardware_button_listener.on_start_callback = self.on_hardware_start_signal
```

## Flow Diagram with Real Hardware

```
RFID Reader (Hardware)
    ↓ [scans tag RFID001]
HardwareReader.on_scan(tag_id="RFID001", timestamp="2025-04-06T14:30:00")
    ↓
RunnerView._on_rfid_scanned()
    ↓
ScanRFIDUseCase.execute(1, "RFID001", "2025-04-06T14:30:00")
    ↓
Workout.record_rfid_event() [Domain Logic]
    ↓
InMemoryWorkoutRepository.save()
    ↓
CoachView._poll() [periodic, every 1000ms]
    ↓
GetRunningScreenUseCase.execute() → Updated runner list
    ↓
Coach Dashboard Tables/Charts Update
```

## CSV Athlete Roster Loading

Athletes are loaded via the Coach Dashboard:

1. Click "📂 Load Roster" button
2. Select CSV file with columns: `name`, `nfc_tag`, `rfid_tag`, (optional) `email`
3. File is parsed and athletes are added to workout
4. Tags must be unique

This must be done **before** starting the workout, so hardware can match tags correctly.

## Support for Multiple Runners

Currently a single runner window opens for the first athlete. For multiple runner windows:

```python
# In main.py
for runner_session in workout.runnerSessions:
    runner_window = tk.Toplevel(root)
    RunnerView(
        runner_window,
        ...,
        runner=runner_session.runner,
        hardware_reader=hardware_reader,  # Can be shared
        ...
    )
```

## Troubleshooting

- **Tags not matching**: Verify CSV tag IDs exactly match hardware output
- **Hardware not recognized**: Check serial port, driver installation
- **Laps not recording**: Ensure `use_event_time=False` if using local timestamps
- **Polling not updating**: Check `GetRunningScreenUseCase.execute()` works independently

## Questions?

See domain/ and application/use_cases/ for the actual business logic.
Use cases have execute() methods that expect hardware input.
