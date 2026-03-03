from domain.runner import Runner

def test_runner_creation():
    runner = Runner(
        runner_id=1,
        name="Clifford Wijaya",
        email="cwijaya@example.com",
        nfc_tag="NFC1",
        rfid_tag="RFID1"
    )

    assert runner.id == 1
    assert runner.name == "Clifford Wijaya"
    assert runner.email == "cwijaya@example.com"
    assert runner.nfc_tag == "NFC1"
    assert runner.rfid_tag == "RFID1"