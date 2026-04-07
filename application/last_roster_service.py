from typing import List
from domain.runner import Runner
from externalInterface.last_roster_storage import (
    save_last_roster,
    load_last_roster,
    last_roster_exists,
)


class LastRosterService:
    def save_roster(self, runners: List[Runner]) -> None:
        save_last_roster(runners)
        print("DEBUG: LastRosterService.save_roster called")

    def load_roster(self) -> List[Runner]:
        return load_last_roster()

    def has_saved_roster(self) -> bool:
        return last_roster_exists()