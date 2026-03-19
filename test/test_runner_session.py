import pytest
from domain.runner import Runner
from domain.runnerSession import RunnerSession
from domain.runnerState import RunnerState

def test_runner_session_cannot_start_twice_while_running():
    runner = Runner(
        runner_id=1,
        name="Clifford Wijaya",
        email="cwijaya@example.com",
        nfc_tag="NFC001",
        rfid_tag="RFID001",
    )
    session = RunnerSession(runner=runner, restDuration=30)

    session.start_interval()
    assert session.state == RunnerState.RUNNING

    with pytest.raises(ValueError):
        session.start_interval()