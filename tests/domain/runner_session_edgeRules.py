"""
Domain unit tests for RunnerSession edge-case rules.


These tests cover important guardrails that prevent invalid state transitions.
we avoid relying on time passing (no sleep/mocking).
"""

import pytest
from datetime import datetime

from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.states import (
    RUNNER_NOT_STARTED,
    RUNNER_RUNNING,
    RUNNER_RESTING,
)


def _make_runner() -> Runner:
    """
    creates a basic runner so we don't repeat setup everywhere.
    """
    return Runner(
        runner_id=1,
        name="Test Runner",
        email="",
        nfc_tag="NFC1",
        rfid_tag="RFID1",
    )


def test_runner_session_cannot_start_while_resting():
    """
    If a runner is RESTING, they should NOT be allowed to start a new interval yet.
    This protects the rule: "cannot start if resting."
    """
    runner = _make_runner()
    session = RunnerSession(runner=runner, restDuration=30)

    # Force the session into RESTING with a rest that started "just now".
    # Plain-speak: Using a huge restDuration ensures the session won't become READY.
    session.state = RUNNER_RESTING
    session.rests = [{
        "start": datetime.now().isoformat(),
        "restDuration": 999999,  # huge so check_if_ready won't flip to READY
        "end": None,
    }]

    with pytest.raises(ValueError):
        session.start_interval()


def test_should_finish_interval_false_when_not_running():
    """
    should_finish_interval should return False if the runner isn't RUNNING.
    That prevents accidentally completing intervals while NOT_STARTED/RESTING/READY.
    """
    runner = _make_runner()
    session = RunnerSession(runner=runner, restDuration=30)

    assert session.state == RUNNER_NOT_STARTED
    assert session.should_finish_interval(lapsPerInterval=1) is False


def test_finish_interval_raises_if_not_running():
    """
    finish_interval is only valid when runner is RUNNING.
    If they are NOT_STARTED (or RESTING/READY), it should raise an error.
    """
    runner = _make_runner()
    session = RunnerSession(runner=runner, restDuration=30)

    assert session.state == RUNNER_NOT_STARTED

    with pytest.raises(ValueError):
        session.finish_interval()