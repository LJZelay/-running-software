from typing import Optional

class Runner:
    """
    Domain Entity: Runner

    Stores static information about a runner:
    - id, name, email, NFC tag, RFID tag
    """

    def __init__(
        self,
        runner_id: int,
        name: str,
        email: str,
        nfc_tag: str,
        rfid_tag: str,
    ):
        self.id = runner_id
        self.name = name
        self.email = email
        self.nfc_tag = nfc_tag
        self.rfid_tag = rfid_tag

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "nfc_tag": self.nfc_tag,
            "rfid_tag": self.rfid_tag,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            runner_id=data["id"],
            name=data["name"],
            email=data["email"],
            nfc_tag=data["nfc_tag"],
            rfid_tag=data["rfid_tag"],
        )
