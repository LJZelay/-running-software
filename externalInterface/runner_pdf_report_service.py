from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional
import re


class RunnerPdfReportService:
    """Generate one PDF summary per runner for a completed workout."""

    def __init__(self, output_dir: Optional[Path] = None) -> None:
        self.output_dir = Path(output_dir) if output_dir is not None else Path("reports")

    def generate_reports_for_workout(self, workout: object, output_dir: Optional[Path] = None) -> list[Path]:
        target_dir = output_dir if output_dir is not None else self.output_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        generated: list[Path] = []

        for session in workout.runnerSessions:
            report_lines = self._build_report_lines(workout, session)
            safe_name = self._sanitize_filename(session.runner.name)
            file_name = f"workout_{workout.workout_id}_runner_{session.runner.id}_{safe_name}.pdf"
            output_path = target_dir / file_name
            self._write_simple_pdf(report_lines, output_path)
            generated.append(output_path)

        return generated

    def _build_report_lines(self, workout: object, session: object) -> list[str]:
        lines = [
            "Runner Workout Report",
            f"Runner: {session.runner.name}",
            f"Workout ID: {workout.workout_id}",
            f"Workout Date: {workout.endTime or workout.startTime or 'N/A'}",
            f"Configured Interval Distance: {workout.intervalDistance} m",
            f"Configured Rest Duration: {session.restDuration} s",
            "",
        ]

        if not session.intervals:
            lines.append("No intervals were completed in this workout.")
            return lines

        lines.append("Intervals")
        for idx, interval in enumerate(session.intervals, start=1):
            duration_ms = self._duration_ms(interval.get("start"), interval.get("end"))
            duration_label = f"{duration_ms} ms" if duration_ms is not None else "N/A"
            lines.append(
                f"Interval {idx}: start={interval.get('start') or 'N/A'}, "
                f"end={interval.get('end') or 'N/A'}, duration={duration_label}"
            )

            split_lines = self._build_split_lines(interval)
            if split_lines:
                lines.extend(split_lines)

            if idx <= len(session.rests):
                rest = session.rests[idx - 1]
                actual_rest_ms = self._duration_ms(rest.get("start"), rest.get("end"))
                rest_label = f"{actual_rest_ms} ms" if actual_rest_ms is not None else "N/A"
                lines.append(
                    f"Rest {idx}: configured={rest.get('restDuration', session.restDuration)} s, "
                    f"actual={rest_label}"
                )

            lines.append("")

        return lines

    def _build_split_lines(self, interval: dict) -> list[str]:
        laps: list[str] = interval.get("laps", [])
        if len(laps) < 1:
            return []

        start = interval.get("start")
        if not start:
            return []

        split_lines = ["Split timings (ms):"]
        previous_marker = start
        for lap_index, lap in enumerate(laps, start=1):
            cumulative_ms = self._duration_ms(start, lap)
            split_ms = self._duration_ms(previous_marker, lap)
            cumulative_label = str(cumulative_ms) if cumulative_ms is not None else "N/A"
            split_label = str(split_ms) if split_ms is not None else "N/A"
            split_lines.append(
                f"  Lap {lap_index}: split={split_label}, cumulative={cumulative_label}"
            )
            previous_marker = lap

        return split_lines

    @staticmethod
    def _duration_ms(start_iso: Optional[str], end_iso: Optional[str]) -> Optional[int]:
        if not start_iso or not end_iso:
            return None
        try:
            start = datetime.fromisoformat(start_iso)
            end = datetime.fromisoformat(end_iso)
        except ValueError:
            return None
        duration_ms = int((end - start).total_seconds() * 1000)
        if duration_ms < 0:
            return None
        return duration_ms

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        sanitized = re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_")
        return sanitized or "runner"

    @staticmethod
    def _escape_pdf_text(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _write_simple_pdf(self, lines: Iterable[str], target_path: Path) -> None:
        escaped_lines = [self._escape_pdf_text(line) for line in lines]

        content_parts = ["BT", "/F1 12 Tf", "50 780 Td", "14 TL"]
        for i, line in enumerate(escaped_lines):
            if i == 0:
                content_parts.append(f"({line}) Tj")
            else:
                content_parts.append(f"T* ({line}) Tj")
        content_parts.append("ET")
        content_stream = "\n".join(content_parts).encode("latin-1", errors="replace")

        objects = [
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
            b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
            (
                f"5 0 obj\n<< /Length {len(content_stream)} >>\nstream\n".encode("ascii")
                + content_stream
                + b"\nendstream\nendobj\n"
            ),
        ]

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for obj in objects:
            offsets.append(len(pdf))
            pdf.extend(obj)

        xref_offset = len(pdf)
        pdf.extend(f"xref\n0 {len(offsets)}\n".encode("ascii"))
        pdf.extend(b"0000000000 65535 f \n")
        for off in offsets[1:]:
            pdf.extend(f"{off:010d} 00000 n \n".encode("ascii"))
        pdf.extend(
            (
                "trailer\n"
                f"<< /Size {len(offsets)} /Root 1 0 R >>\n"
                "startxref\n"
                f"{xref_offset}\n"
                "%%EOF\n"
            ).encode("ascii")
        )

        target_path.write_bytes(pdf)
