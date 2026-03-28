"""
RFID Worker Service: Manages deterministic, thread-safe event processing.

Provides:
- Ingest thread for receiving RFID/NFC events from hardware adapters
- Worker thread for processing events with single-writer mutation semantics
- Bounded queue with drop-oldest overflow behavior
- Coarse-grained lock for shared state (workout, runner sessions)
- Worker health monitoring and failure handling
"""

import threading
import queue
import logging
import traceback
from datetime import datetime
from typing import Optional, Callable
from dataclasses import dataclass

from application.rfid_contracts import RFIDEventEnvelope, RFIDRuntimeConfig


logger = logging.getLogger(__name__)


@dataclass
class WorkerHealthStatus:
    """Current health and statistics of the worker thread."""
    is_alive: bool
    events_processed: int
    events_dropped: int
    last_error: Optional[str] = None
    last_error_time: Optional[str] = None
    worker_thread_id: Optional[int] = None


class RFIDWorkerService:
    """
    Thread-safe RFID event processing service.
    
    - Single ingest thread queues events (non-blocking, drop-oldest on overflow)
    - Single worker thread processes events serially (mutations only)
    - Coarse-grained lock protects all shared state during mutation
    - Worker crash stops ingest and halts processing
    
    Design:
    - Lock guards: workout, runner sessions, all mutable state
    - Worker calls execute() on each queued event (via callback function)
    - Ingest thread calls enqueue_event() (lock-free, queue operation only)
    - Coach/display reads lock briefly for status queries
    """
    
    def __init__(self, config: RFIDRuntimeConfig, process_event_callback: Callable):
        """
        Initialize RFID worker service.
        
        Args:
            config: RFIDRuntimeConfig with queue_size, debounce_ms, max_drift_ms, cache_size
            process_event_callback: Callable that processes a single RFIDEventEnvelope
                                    and returns decision result (dict or object)
                                    Signature: (event: RFIDEventEnvelope) -> decision_result
        """
        self.config = config
        self.process_event_callback = process_event_callback
        
        # Shared state protected by single coarse-grained lock
        self._lock = threading.Lock()
        self._worker_alive = True
        self._events_processed = 0
        self._events_dropped = 0
        self._last_error: Optional[str] = None
        self._last_error_time: Optional[str] = None
        
        # Event queue with bounded size and drop-oldest overflow
        self._event_queue: queue.Queue = queue.Queue(maxsize=config.queue_size)
        
        # Thread management
        self._ingest_thread: Optional[threading.Thread] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        
        # Lifecycle
        self._started = False
        self._stopped = False
        
    def start(self) -> None:
        """
        Start ingest and worker threads.
        
        Thread Model:
        - Ingest thread: Wait for external events, queue them (non-blocking)
        - Worker thread: Process queued events serially (lock-guarded mutations)
        - Main: Can safely read status (queries will block briefly on lock)
        """
        with self._lock:
            if self._started:
                logger.warning("RFIDWorkerService already started")
                return
            
            self._started = True
            self._stop_event.clear()
            self._worker_alive = True
            
        # Start worker thread (processes events from queue)
        self._worker_thread = threading.Thread(
            target=self._worker_run,
            name="RFIDWorker",
            daemon=False
        )
        self._worker_thread.start()
        logger.info("RFIDWorkerService started (worker thread running)")
        
    def stop(self) -> None:
        """
        Stop worker and ingest threads gracefully.
        
        Signals threads to stop, waits for them to finish.
        """
        with self._lock:
            if self._stopped:
                logger.warning("RFIDWorkerService already stopped")
                return
            
            self._stopped = True
            self._stop_event.set()
        
        # Wait for worker thread to finish
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5.0)
            if self._worker_thread.is_alive():
                logger.warning("Worker thread did not stop within timeout")
        
        logger.info("RFIDWorkerService stopped")
    
    def enqueue_event(self, event: RFIDEventEnvelope) -> bool:
        """
        Enqueue an RFID event for processing.
        
        Non-blocking operation. If queue is full, drops oldest event.
        
        Args:
            event: RFIDEventEnvelope to process
            
        Returns:
            True if event was queued, False if dropped (queue overflow)
        """
        # Check if worker is alive (fail-safe: stop intake if worker crashed)
        with self._lock:
            if not self._worker_alive:
                logger.warning(f"Worker not alive, rejecting event {event.event_id}")
                return False
        
        # Try to queue event (non-blocking, drop oldest if full)
        try:
            # Use non-blocking put with drop-oldest on overflow
            try:
                self._event_queue.put_nowait(event)
                return True
            except queue.Full:
                # Queue is full, drop oldest and add new
                try:
                    self._event_queue.get_nowait()  # Drop oldest
                    self._event_queue.put_nowait(event)
                    with self._lock:
                        self._events_dropped += 1
                    logger.debug(f"Queue full, dropped oldest event (dropped: {self._events_dropped})")
                    return True
                except queue.Empty:
                    # Race condition: queue emptied between check and drop
                    self._event_queue.put_nowait(event)
                    return True
        except Exception as e:
            logger.error(f"Error queueing event: {e}")
            return False
    
    def get_health_status(self) -> WorkerHealthStatus:
        """
        Get current health status (lock-guarded snapshot).
        
        Returns:
            WorkerHealthStatus with worker state, stats, errors
        """
        with self._lock:
            return WorkerHealthStatus(
                is_alive=self._worker_alive,
                events_processed=self._events_processed,
                events_dropped=self._events_dropped,
                last_error=self._last_error,
                last_error_time=self._last_error_time,
                worker_thread_id=self._worker_thread.ident if self._worker_thread else None
            )
    
    def get_queue_depth(self) -> int:
        """Get current number of events waiting in queue."""
        return self._event_queue.qsize()
    
    def _worker_run(self) -> None:
        """
        Worker thread main loop.
        
        - Poll queue for events
        - Process each event via callback (under lock for mutations)
        - On crash: mark worker_alive=False, stop accepting new events, log error
        """
        worker_thread_id = threading.get_ident()
        logger.info(f"Worker thread started (tid={worker_thread_id})")
        
        try:
            while not self._stop_event.is_set():
                try:
                    # Poll queue with timeout to allow graceful shutdown
                    try:
                        event: RFIDEventEnvelope = self._event_queue.get(timeout=0.5)
                    except queue.Empty:
                        # No events, continue polling
                        continue
                    
                    # Process event under lock (mutations only)
                    with self._lock:
                        try:
                            # Call the event processing callback
                            # Callback is responsible for updating workout/runner sessions
                            decision_result = self.process_event_callback(event)
                            self._events_processed += 1
                            
                            logger.debug(
                                f"Event {event.event_id} processed: decision={decision_result}"
                            )
                        
                        except Exception as callback_error:
                            logger.error(
                                f"Error processing event {event.event_id}: {callback_error}\n"
                                f"{traceback.format_exc()}"
                            )
                            # Log error but continue processing
                            self._last_error = (
                                f"{type(callback_error).__name__}: {callback_error}"
                            )
                            self._last_error_time = datetime.now().isoformat()
                
                except Exception as queue_error:
                    # Error getting from queue (rare)
                    logger.error(f"Error polling queue: {queue_error}")
                    with self._lock:
                        self._last_error = f"Queue error: {queue_error}"
                        self._last_error_time = datetime.now().isoformat()
        
        except Exception as thread_error:
            # Critical thread error - mark as unhealthy and stop accepting events
            logger.critical(
                f"Worker thread crashed: {thread_error}\n"
                f"{traceback.format_exc()}"
            )
            with self._lock:
                self._worker_alive = False
                self._last_error = f"WORKER CRASH: {thread_error}"
                self._last_error_time = datetime.now().isoformat()
        
        finally:
            with self._lock:
                self._worker_alive = False
            logger.info(f"Worker thread stopped (tid={worker_thread_id})")
