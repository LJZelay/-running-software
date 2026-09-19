from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import re


class WorkoutSummaryPdfGenerator:
    """Generate a single PDF summary of a complete workout (config, roster, results)."""

    def __init__(self) -> None:
        pass

    def generate(self, summary_dict: Dict[str, Any], output_path: Path) -> None:
        """
        Create a PDF file from the workout summary dictionary.
        The dict must contain the same structure as built by _build_workout_summary_dict.
        """
        lines = self._build_lines(summary_dict)
        self._write_simple_pdf(lines, output_path)

    def _build_lines(self, summary: Dict[str, Any]) -> List[str]:
        lines = [
            "=" * 70,
            f"WORKOUT SUMMARY: {summary.get('name', 'Unnamed')}",
            "=" * 70,
            f"Date: {summary.get('date', 'Unknown')}",
            "",
            "--- CONFIGURATION ---",
            f"  Interval distance : {summary.get('config', {}).get('interval_distance_m', '?')} m",
            f"  Laps per interval : {summary.get('config', {}).get('laps_per_interval', '?')}",
            f"  Start mode        : {summary.get('config', {}).get('start_mode', '?')}",
            f"  Default rest      : {summary.get('config', {}).get('default_rest_seconds', '?')} s",
            f"  Target intervals  : {summary.get('config', {}).get('target_intervals', '?')}",
            "",
            "--- ROSTER ---",
        ]

        roster = summary.get('roster', [])
        if roster:
            lines.append(f"  {'ID':<5} {'Name':<20} {'RFID Tag':<15} {'NFC Tag':<15}")
            lines.append(f"  {'-'*5} {'-'*20} {'-'*15} {'-'*15}")
            for r in roster:
                lines.append(
                    f"  {r.get('id', '?'):<5} {r.get('name', '?'):<20} "
                    f"{r.get('rfid_tag', 'N/A'):<15} {r.get('nfc_tag', 'N/A'):<15}"
                )
        else:
            lines.append("  No runners in roster.")

        lines.append("")
        lines.append("--- GLOBAL METRICS ---")
        metrics = summary.get('global_metrics', {})
        lines.append(f"  Total runners            : {metrics.get('total_runners', 0)}")
        lines.append(f"  Total completed intervals: {metrics.get('total_completed_intervals', 0)}")
        lines.append("")

        lines.append("--- INDIVIDUAL RESULTS ---")
        results = summary.get('results', {})
        if not results:
            lines.append("  No interval data available.")
        else:
            for runner_id, data in results.items():
                runner_name = self._find_runner_name(roster, runner_id)
                lines.append(f"\n  Runner: {runner_name} (ID {runner_id})")
                lines.append(f"    Overall avg pace : {data.get('overall_avg_pace_s_per_km', 'N/A')} s/km")
                lines.append(f"    Rest efficiency  : {data.get('rest_efficiency', 'N/A')}")
                lines.append("    Intervals:")
                intervals = data.get('intervals', [])
                if intervals:
                    lines.append("      #   Duration(s)   Pace(s/km)   Splits(s)")
                    for iv in intervals:
                        num = iv.get('number', '?')
                        dur = round(iv.get('duration_ms', 0) / 1000, 1) if iv.get('duration_ms') else '?'
                        pace = round(iv.get('pace_per_km', 0), 1) if iv.get('pace_per_km') else '?'
                        splits = ', '.join(str(round(s/1000, 1)) for s in iv.get('splits_ms', [])) if iv.get('splits_ms') else '-'
                        lines.append(f"      {num:<3} {dur:<12} {pace:<12} {splits}")
                else:
                    lines.append("      No intervals recorded.")

        lines.append("")
        lines.append("=" * 70)
        lines.append("End of report")
        return lines

    def _find_runner_name(self, roster: List[Dict], runner_id: str) -> str:
        for r in roster:
            if str(r.get('id')) == str(runner_id):
                return r.get('name', 'Unknown')
        return f"Runner {runner_id}"

    # ------------------------------------------------------------------
    # Low-level PDF writing (identical technique as RunnerPdfReportService)
    # ------------------------------------------------------------------
    @staticmethod
    def _escape_pdf_text(value: str) -> str:
        """Escape special characters for PDF text strings."""
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def _write_simple_pdf(self, lines: List[str], target_path: Path) -> None:
        escaped_lines = [self._escape_pdf_text(line) for line in lines]

        # Prepare content stream: each line starts at a new line (T*)
        content_parts = ["BT", "/F1 10 Tf", "50 780 Td", "12 TL"]
        for i, line in enumerate(escaped_lines):
            if i == 0:
                content_parts.append(f"({line}) Tj")
            else:
                content_parts.append(f"T* ({line}) Tj")
        content_parts.append("ET")
        content_stream = "\n".join(content_parts).encode("latin-1", errors="replace")

        # Standard PDF objects
        objects = [
            b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
            b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>\nendobj\n",
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