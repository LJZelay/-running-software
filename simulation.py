import csv
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# Command to run:
# python simulation.py .\simulation\interval_training_test_data\group_and_single_start\athletes.csv .\simulation\interval_training_test_data\group_and_single_start\commands.csv

INTERVAL_DISTANCE_METERS = 400
LAPS_PER_INTERVAL = 1
DEFAULT_REST_SECONDS = 60

@dataclass
class Athlete:
    first_name: str
    last_name: str
    rfid_tag: str
    nfc_tag: str
    email: str = ""

@dataclass
class AthleteTimeline:
    athlete: Athlete
    intervals: List[Tuple[int, int]] = field(default_factory=list)
    rests: List[Tuple[int, int]] = field(default_factory=list)

    current_interval_start_ms: Optional[int] = None

    def start_interval(self, start_ms: int) -> None:
        # If the runner is currently running, ignore/raise; for simulation we ignore duplicate starts.
        if self.current_interval_start_ms is not None:
            return
        self.current_interval_start_ms = start_ms

    def finish_interval(self, end_ms: int) -> None:
        # Ignore RFID if no interval is currently running
        if self.current_interval_start_ms is None:
            return

        start_ms = self.current_interval_start_ms
        # Ignore if end is before start
        if end_ms < start_ms:
            return

        self.intervals.append((start_ms, end_ms))
        self.current_interval_start_ms = None
        # Rest start is end_ms; rest end will be filled when next interval starts
        # We'll add rest as "open" using end_ms and fill later.
        self.rests.append((end_ms, end_ms))

    def close_last_rest_if_open(self, next_start_ms: int) -> None:
        if not self.rests:
            return
        rest_start, rest_end = self.rests[-1]
        # if rest_end == rest_start, we treat it as open
        if rest_end == rest_start and next_start_ms >= rest_start:
            self.rests[-1] = (rest_start, next_start_ms)

    def durations_seconds(self) -> List[float]:
        """
        Return [interval1_sec, rest1_sec, interval2_sec, rest2_sec, ...]
        Only include rest_i if it has a real end (i.e., runner started again).
        """
        out: List[float] = []
        for i, (s, e) in enumerate(self.intervals):
            out.append((e - s) / 1000.0)
            if i < len(self.rests):
                rs, re = self.rests[i]
                if re > rs:
                    out.append((re - rs) / 1000.0)
        return out

def _norm(h: str) -> str:
    return h.strip().lower()

def load_athletes(athletes_csv_path: str) -> Dict[str, AthleteTimeline]:
    """
    Returns dict keyed by NFC tag, value = AthleteTimeline.
    Also builds RFID lookup later from timelines.
    """
    with open(athletes_csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("athletes.csv must have a header row")

        # Map expected headers (case-insensitive)
        headers = {_norm(h): h for h in reader.fieldnames}

        def get(row, key):
            col = headers.get(_norm(key))
            return (row.get(col, "") if col else "").strip()

        timelines: Dict[str, AthleteTimeline] = {}
        for row in reader:
            first = get(row, "First Name")
            last = get(row, "Last Name")
            rfid = get(row, "RFID TAG")
            nfc = get(row, "NFC TAG")
            email = get(row, "email")

            if not first or not last or not rfid or not nfc:
                raise ValueError("Each athlete row must include First Name, Last Name, RFID TAG, NFC TAG")

            athlete = Athlete(first, last, rfid, nfc, email)
            timelines[nfc] = AthleteTimeline(athlete=athlete)
    return timelines

def process_commands(commands_csv_path: str, timelines_by_nfc: Dict[str, AthleteTimeline]) -> None:
    # Build RFID lookup
    timelines_by_rfid: Dict[str, AthleteTimeline] = {
        tl.athlete.rfid_tag: tl for tl in timelines_by_nfc.values()
    }

    current_group: List[str] = []

    with open(commands_csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if not row:
                continue

            cmd = row[0].strip().upper()

            if cmd == "GROUP":
                # GROUP, NFC1, NFC2, ...
                current_group = [x.strip() for x in row[1:] if x.strip()]
                # ignore unknown tags silently
                current_group = [nfc for nfc in current_group if nfc in timelines_by_nfc]

            elif cmd == "START":
                # START, TIMESTAMP
                if len(row) < 2:
                    continue
                start_ms = int(row[1].strip())
                # group start: all in current_group begin interval at start_ms
                for nfc in current_group:
                    tl = timelines_by_nfc[nfc]
                    # Starting a new interval also closes prior rest if open
                    tl.close_last_rest_if_open(start_ms)
                    tl.start_interval(start_ms)

            elif cmd == "NFC":
                # NFC, NFC_tag, TIMESTAMP
                if len(row) < 3:
                    continue
                nfc_tag = row[1].strip()
                ts_ms = int(row[2].strip())
                tl = timelines_by_nfc.get(nfc_tag)
                if tl is None:
                    continue
                tl.close_last_rest_if_open(ts_ms)
                tl.start_interval(ts_ms)

            elif cmd == "RFID":
                # RFID, RFID_tag, TIMESTAMP
                if len(row) < 3:
                    continue
                rfid_tag = row[1].strip()
                ts_ms = int(row[2].strip())
                tl = timelines_by_rfid.get(rfid_tag)
                if tl is None:
                    continue
                tl.finish_interval(ts_ms)

            else:
                continue

def fmt_seconds(x: float) -> str:
    # Print cleanly: integer if whole, else 3 decimals
    if abs(x - round(x)) < 1e-9:
        return str(int(round(x)))
    return f"{x:.3f}".rstrip("0").rstrip(".")

def main(argv: List[str]) -> int:
    athletes_csv = argv[1]
    commands_csv = argv[2]

    timelines_by_nfc = load_athletes(athletes_csv)
    process_commands(commands_csv, timelines_by_nfc)

    for tl in timelines_by_nfc.values():
        durs = tl.durations_seconds()
        parts = [tl.athlete.first_name, tl.athlete.last_name] + [fmt_seconds(x) for x in durs]
        print(", ".join(parts))

    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))