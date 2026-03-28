"""
Tests for RFID Worker Service: Threading, Queue, Lock, and Concurrency Safety.

Validates:
- Single-writer mutation model (worker thread only)
- Non-blocking queue with drop-oldest overflow
- Coarse-grained lock for shared state
- Worker health monitoring and crash recovery
- Concurrent ingest + query safety
"""

import pytest
import threading
import time
from unittest.mock import Mock

from application.services.rfid_worker_service import RFIDWorkerService, WorkerHealthStatus
from application.rfid_contracts import (
    RFIDEventEnvelope,
    HardwareEventType,
    RFIDRuntimeConfig,
)


@pytest.fixture
def runtime_config():
    """RFID runtime config with small queue for testing."""
    return RFIDRuntimeConfig(
        debounce_ms=200,
        max_drift_ms=10_000,
        queue_size=10,  # Small queue to test overflow
        event_id_cache_size=100
    )


@pytest.fixture
def test_event():
    """Sample RFID event for testing."""
    return RFIDEventEnvelope(
        event_id="test-event-001",
        event_type=HardwareEventType.RFID,
        tag_id="12345678",
        timestamp_ms=1000000,
        ingest_time_ms=1000100,
        source="reader-1"
    )


def test_worker_service_initialization(runtime_config):
    """Test service initializes with proper defaults."""
    callback = Mock()
    service = RFIDWorkerService(runtime_config, callback)
    
    assert not service._started
    assert not service._stopped
    assert service._worker_alive is True
    assert service._events_processed == 0
    assert service._events_dropped == 0
    assert service._last_error is None


def test_worker_service_start_and_stop(runtime_config):
    """Test service start and stop lifecycle."""
    callback = Mock()
    service = RFIDWorkerService(runtime_config, callback)
    
    service.start()
    assert service._started
    assert service._worker_thread is not None
    assert service._worker_thread.is_alive()
    
    service.stop()
    assert service._stopped
    # Give thread time to actually stop
    time.sleep(0.1)
    assert not service._worker_thread.is_alive()


def test_worker_service_prevents_double_start(runtime_config):
    """Test service prevents multiple start calls."""
    callback = Mock()
    service = RFIDWorkerService(runtime_config, callback)
    
    service.start()
    first_thread = service._worker_thread
    
    # Second start should not create new thread
    service.start()
    assert service._worker_thread is first_thread
    
    service.stop()


def test_enqueue_event_success(runtime_config, test_event):
    """Test successful event queueing."""
    callback = Mock(return_value={"decision": "accepted"})
    service = RFIDWorkerService(runtime_config, callback)
    service.start()
    
    result = service.enqueue_event(test_event)
    assert result is True
    
    # Worker should process the event quickly without deadlocking
    deadline = time.time() + 1.0
    while time.time() < deadline and service._events_processed < 1:
        time.sleep(0.02)

    assert callback.call_count >= 1
    assert service._events_processed >= 1
    
    service.stop()


def test_enqueue_event_queue_overflow_drops_oldest(runtime_config):
    """Test queue overflow behavior: drop oldest event."""
    call_count = 0
    processed_event_ids = []
    
    def callback(event):
        nonlocal call_count
        call_count += 1
        processed_event_ids.append(event.event_id)
        # Slow processing to accumulate queue
        time.sleep(0.05)
        return {"decision": "accepted"}
    
    dropped_ids = []

    def overflow_callback(event):
        dropped_ids.append(event.event_id)

    service = RFIDWorkerService(runtime_config, callback, overflow_event_callback=overflow_callback)
    service.start()
    
    # Rapidly queue more events than queue size
    event_ids = []
    for i in range(15):
        event = RFIDEventEnvelope(
            event_id=f"event-{i:03d}",
            event_type=HardwareEventType.RFID,
            tag_id=f"tag-{i}",
            timestamp_ms=1000000 + i * 100,
            ingest_time_ms=1000100 + i * 100,
            source="reader-1"
        )
        event_ids.append(event.event_id)
        service.enqueue_event(event)
        # No delay to force overflow pressure
    
    # Wait for worker to process enough events
    time.sleep(0.8)
    
    service.stop()
    
    # Verify: some events were dropped (queue size is 10)
    assert service._events_dropped > 0, "Expected queue overflow to drop events"
    assert len(dropped_ids) > 0, "Expected overflow callback to be called"


def test_worker_health_status(runtime_config, test_event):
    """Test worker health status reporting."""
    callback = Mock(return_value={"decision": "accepted"})
    service = RFIDWorkerService(runtime_config, callback)
    service.start()
    
    # Initial status
    status = service.get_health_status()
    assert isinstance(status, WorkerHealthStatus)
    assert status.is_alive is True
    assert status.events_processed == 0
    assert status.events_dropped == 0
    assert status.queue_utilization_percent >= 0.0
    assert status.queue_drops_per_minute >= 0.0
    assert status.processing_latency_ms >= 0.0
    
    # Queue and process event
    service.enqueue_event(test_event)
    time.sleep(0.2)
    
    status = service.get_health_status()
    assert status.is_alive is True
    assert status.events_processed >= 1
    assert status.last_processed_event_id is not None
    
    service.stop()


def test_enqueue_rejected_when_worker_not_alive(runtime_config, test_event):
    """When worker is stopped/unhealthy, enqueue should reject new events."""
    callback = Mock(return_value={"decision": "accepted"})
    service = RFIDWorkerService(runtime_config, callback)
    service.start()
    service.stop()

    result = service.enqueue_event(test_event)
    assert result is False


def test_concurrent_ingest_and_status_queries(runtime_config):
    """Test concurrent ingest and status query safety (no deadlock)."""
    processed_events = []
    
    def callback(event):
        processed_events.append(event.event_id)
        return {"decision": "accepted"}
    
    service = RFIDWorkerService(runtime_config, callback)
    service.start()
    
    ingest_finished = threading.Event()
    query_finished = threading.Event()
    errors = []
    
    def ingest_thread():
        try:
            for i in range(20):
                event = RFIDEventEnvelope(
                    event_id=f"ingest-{i}",
                    event_type=HardwareEventType.RFID,
                    tag_id=f"tag-{i}",
                    timestamp_ms=1000000 + i * 100,
                    ingest_time_ms=1000100 + i * 100,
                    source="reader-1"
                )
                service.enqueue_event(event)
                time.sleep(0.01)
        except Exception as e:
            errors.append(f"Ingest error: {e}")
        finally:
            ingest_finished.set()
    
    def query_thread():
        try:
            for _ in range(30):
                status = service.get_health_status()
                assert status is not None
                depth = service.get_queue_depth()
                assert depth >= 0
                time.sleep(0.002)
        except Exception as e:
            errors.append(f"Query error: {e}")
        finally:
            query_finished.set()
    
    # Run ingest and query threads concurrently
    t_ingest = threading.Thread(target=ingest_thread)
    t_query = threading.Thread(target=query_thread)
    
    t_ingest.start()
    t_query.start()
    
    t_ingest.join(timeout=5.0)
    t_query.join(timeout=5.0)
    
    assert ingest_finished.is_set(), "Ingest thread did not finish"
    assert query_finished.is_set(), "Query thread did not finish"
    assert len(errors) == 0, f"Errors during concurrent access: {errors}"
    
    service.stop()


def test_queue_depth_reporting(runtime_config):
    """Test queue depth status reporting."""
    slow_callback = Mock()
    
    def slow_callback_fn(event):
        time.sleep(0.1)  # Slow processing
        return {"decision": "accepted"}
    
    service = RFIDWorkerService(runtime_config, slow_callback_fn)
    service.start()
    
    # Rapidly queue several events
    for i in range(5):
        event = RFIDEventEnvelope(
            event_id=f"queue-depth-{i}",
            event_type=HardwareEventType.RFID,
            tag_id=f"tag-{i}",
            timestamp_ms=1000000 + i * 100,
            ingest_time_ms=1000100 + i * 100,
            source="reader-1"
        )
        service.enqueue_event(event)
    
    # Check queue has some depth
    depth = service.get_queue_depth()
    assert depth > 0, "Expected some events in queue"
    
    # Wait for processing
    time.sleep(1.0)
    
    # Queue should drain
    final_depth = service.get_queue_depth()
    assert final_depth < depth, "Expected queue to drain over time"
    
    service.stop()


def test_worker_processes_events_in_order(runtime_config):
    """Test worker processes events in FIFO queue order."""
    processed_order = []
    
    def callback(event):
        processed_order.append(event.event_id)
        return {"decision": "accepted"}
    
    service = RFIDWorkerService(runtime_config, callback)
    service.start()
    
    # Queue 5 events with identifiable IDs
    event_ids = ["first", "second", "third", "fourth", "fifth"]
    for event_id in event_ids:
        event = RFIDEventEnvelope(
            event_id=event_id,
            event_type=HardwareEventType.RFID,
            tag_id="same-tag",
            timestamp_ms=1000000,
            ingest_time_ms=1000100,
            source="reader-1"
        )
        service.enqueue_event(event)
    
    # Wait for processing
    time.sleep(0.5)
    
    service.stop()
    
    # Verify FIFO order
    assert processed_order == event_ids, f"Expected {event_ids}, got {processed_order}"


def test_lock_protects_shared_state(runtime_config):
    """Test coarse-grained lock protects mutations and queries."""
    service = RFIDWorkerService(runtime_config, Mock())
    service.start()
    
    # Access lock-protected state from multiple threads
    errors = []
    
    def mutate_stats():
        try:
            for _ in range(100):
                # Simulate holding lock during status query (which acquires lock)
                status = service.get_health_status()
                # Access internal state should not race
                assert status.events_processed >= 0
        except Exception as e:
            errors.append(f"Mutation error: {e}")
    
    threads = [threading.Thread(target=mutate_stats) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)
    
    assert len(errors) == 0, f"Errors during concurrent state access: {errors}"
    
    service.stop()


def test_graceful_shutdown_with_pending_events(runtime_config):
    """Test graceful shutdown processes pending events."""
    processed_events = []
    
    def callback(event):
        processed_events.append(event.event_id)
        time.sleep(0.05)  # Slow processing
        return {"decision": "accepted"}
    
    service = RFIDWorkerService(runtime_config, callback)
    service.start()
    
    # Queue several events
    for i in range(5):
        event = RFIDEventEnvelope(
            event_id=f"shutdown-test-{i}",
            event_type=HardwareEventType.RFID,
            tag_id=f"tag-{i}",
            timestamp_ms=1000000 + i * 100,
            ingest_time_ms=1000100 + i * 100,
            source="reader-1"
        )
        service.enqueue_event(event)
    
    # Stop service
    service.stop()
    
    # Verify events were processed before shutdown
    assert len(processed_events) > 0, "Expected at least some events to be processed before shutdown"


def test_callback_exception_isolation(runtime_config):
    """Test callback exceptions don't crash worker, logged and tracked."""
    callback_calls = []
    
    def faulty_callback(event):
        callback_calls.append(event.event_id)
        if len(callback_calls) == 2:
            raise ValueError(f"Simulated error on event {event.event_id}")
        return {"decision": "accepted"}
    
    service = RFIDWorkerService(runtime_config, faulty_callback)
    service.start()
    
    # Queue 5 events, 2nd will raise error
    for i in range(5):
        event = RFIDEventEnvelope(
            event_id=f"fault-test-{i}",
            event_type=HardwareEventType.RFID,
            tag_id=f"tag-{i}",
            timestamp_ms=1000000 + i * 100,
            ingest_time_ms=1000100 + i * 100,
            source="reader-1"
        )
        service.enqueue_event(event)
    
    time.sleep(0.5)
    
    status = service.get_health_status()
    assert status.is_alive is True, "Worker should still be alive after callback exception"
    assert "ValueError" in (status.last_error or ""), "Error should be logged"
    
    service.stop()
