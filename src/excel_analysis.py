"""Excel workbook generation for OsBp detection outputs."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

import xlsxwriter


BIN_START = 0.05
BIN_STEP = 0.05
BIN_COUNT = 11
EXCEL_MAX_ROWS = 1_048_576
EVENT_HEADERS = ("Channel", "Event", "Start", "End", "Ir/Io")


@dataclass
class ChannelSummary:
    """Summary metadata parsed from detection TSV text."""

    channel: int
    event_count: Optional[int] = None
    sampling_rate: Optional[float] = None
    open_current: Optional[float] = None
    skipped: bool = False
    reason: str = ""


@dataclass
class ParsedDetectionOutput:
    """Parsed detection output needed for workbook creation."""

    input_fast5: str = ""
    thresholds: List[str] = field(default_factory=list)
    channels: Dict[int, ChannelSummary] = field(default_factory=dict)
    events: List[Tuple[int, int, int, int, float]] = field(default_factory=list)


def _parse_channel_header(line: str) -> Optional[Tuple[int, Optional[float], Optional[float]]]:
    match = re.match(
        r"# Channel (\d+), Sampling rate: ([^ ]+) Hz, Io: ([^ ]+) pA",
        line,
    )
    if not match:
        return None
    channel = int(match.group(1))
    sampling_rate = _safe_float(match.group(2))
    open_current = _safe_float(match.group(3))
    return channel, sampling_rate, open_current


def _parse_processing_channel(line: str) -> Optional[int]:
    match = re.match(r"Processing channel (\d+)\.\.\.", line)
    return int(match.group(1)) if match else None


def _parse_label_value(line: str) -> Optional[Tuple[str, str]]:
    match = re.match(r"([^:]+?)\s*:\s*(.+)", line)
    if not match:
        return None
    return match.group(1).strip(), match.group(2).strip()


def _safe_float(raw_value: str) -> Optional[float]:
    try:
        return float(raw_value)
    except ValueError:
        return None


def _bins() -> List[float]:
    return [round(BIN_START + (BIN_STEP * idx), 10) for idx in range(BIN_COUNT)]


def _excel_like_bins() -> List[float]:
    bins = [BIN_START]
    for _ in range(1, BIN_COUNT):
        bins.append(bins[-1] + BIN_STEP)
    return bins


def parse_detection_output(cleaned_tsv: Path, skipped_tsv: Optional[Path] = None) -> ParsedDetectionOutput:
    """Parse cleaned and skipped TSV outputs for Excel analysis."""
    parsed = ParsedDetectionOutput()
    current_channel: Optional[int] = None
    pending_event_count: Optional[int] = None

    with cleaned_tsv.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            label_value = _parse_label_value(line)
            if label_value is not None and label_value[0] == "Input FAST5":
                parsed.input_fast5 = label_value[1]
                continue
            if label_value is not None and label_value[0] in {
                "Duration",
                "Event duration (in tps)",
                "Lowest Ir/Io",
                "All Ir/Io",
                "Max events",
            }:
                parsed.thresholds.append(line)
                continue

            channel = _parse_processing_channel(line)
            if channel is not None:
                current_channel = channel
                parsed.channels.setdefault(channel, ChannelSummary(channel=channel))
                pending_event_count = None
                continue

            if line.endswith("events detected.") or line.endswith("events detected"):
                count_match = re.match(r"(\d+) events detected\.?", line)
                if count_match and current_channel is not None:
                    pending_event_count = int(count_match.group(1))
                    parsed.channels[current_channel].event_count = pending_event_count
                continue

            channel_header = _parse_channel_header(line)
            if channel_header is not None:
                channel, sampling_rate, open_current = channel_header
                current_channel = channel
                summary = parsed.channels.setdefault(channel, ChannelSummary(channel=channel))
                summary.event_count = pending_event_count
                summary.sampling_rate = sampling_rate
                summary.open_current = open_current
                continue

            fields = line.split("\t")
            if len(fields) == 4 and current_channel is not None and fields[0].isdigit():
                try:
                    parsed.events.append(
                        (
                            current_channel,
                            int(fields[0]),
                            int(fields[1]),
                            int(fields[2]),
                            float(fields[3]),
                        )
                    )
                except ValueError:
                    continue

    if skipped_tsv is not None and skipped_tsv.exists():
        _parse_skipped_output(skipped_tsv, parsed)

    for summary in parsed.channels.values():
        if summary.event_count is None and not summary.skipped:
            summary.event_count = 0
    return parsed


def _parse_skipped_output(skipped_tsv: Path, parsed: ParsedDetectionOutput) -> None:
    current_channel: Optional[int] = None
    with skipped_tsv.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            skip_match = re.match(r"Skipped channel (\d+)", line)
            if skip_match:
                current_channel = int(skip_match.group(1))
                summary = parsed.channels.setdefault(
                    current_channel,
                    ChannelSummary(channel=current_channel),
                )
                summary.skipped = True
                summary.reason = "Too many events for cleaned output"
                continue
            count_match = re.match(r"(\d+) events detected\.?", line)
            if count_match and current_channel is not None:
                parsed.channels[current_channel].event_count = int(count_match.group(1))


def histogram_counts(values: Iterable[float]) -> Tuple[List[float], List[int], int]:
    """Count values into Excel-style upper-bound bins plus a More bucket."""
    bins = _excel_like_bins()
    counts = [0 for _ in bins]
    more = 0
    for value in values:
        lower_bound = float("-inf")
        placed = False
        for index, upper_bound in enumerate(bins):
            if lower_bound < value <= upper_bound:
                counts[index] += 1
                placed = True
                break
            lower_bound = upper_bound
        if not placed:
            more += 1
    return _bins(), counts, more


def create_analysis_workbook(
    cleaned_tsv: Path,
    skipped_tsv: Optional[Path],
    workbook_path: Path,
) -> None:
    """Create an Excel workbook with cleaned events, skipped channels, and histogram."""
    parsed = parse_detection_output(cleaned_tsv, skipped_tsv)
    workbook_path.parent.mkdir(parents=True, exist_ok=True)

    workbook = xlsxwriter.Workbook(str(workbook_path), {"constant_memory": True})
    formats = _create_formats(workbook)
    try:
        summary_sheet = workbook.add_worksheet("Summary")
        _write_summary_sheet(workbook, summary_sheet, parsed, formats)
        _write_event_sheets(workbook, parsed.events, formats)
    finally:
        workbook.close()


def _create_formats(workbook: xlsxwriter.Workbook) -> Dict[str, xlsxwriter.format.Format]:
    return {
        "title": workbook.add_format({"bold": True, "font_size": 16}),
        "section": workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1}),
        "header": workbook.add_format({"bold": True, "bg_color": "#EDEDED", "border": 1}),
        "text": workbook.add_format({"border": 1}),
        "integer": workbook.add_format({"border": 1, "num_format": "0"}),
        "decimal": workbook.add_format({"border": 1, "num_format": "0.000000"}),
    }


def _write_summary_sheet(
    workbook: xlsxwriter.Workbook,
    sheet: xlsxwriter.worksheet.Worksheet,
    parsed: ParsedDetectionOutput,
    formats: Dict[str, xlsxwriter.format.Format],
) -> None:
    sheet.write("A1", "OsBp Detect Analysis", formats["title"])
    sheet.write("A3", "Input FAST5", formats["header"])
    sheet.write("B3", parsed.input_fast5, formats["text"])

    sheet.write("A5", "Thresholds", formats["section"])
    for row_offset, threshold in enumerate(parsed.thresholds, start=6):
        sheet.write(row_offset - 1, 0, threshold, formats["text"])

    histogram_start = max(8, 7 + len(parsed.thresholds))
    _write_histogram(workbook, sheet, parsed, histogram_start, formats)

    summary_row = histogram_start + BIN_COUNT + 6
    sheet.write(summary_row - 1, 0, "Run Summary", formats["section"])
    run_summary = (
        ("Channels parsed", len(parsed.channels)),
        ("Channels in cleaned output", sum(1 for item in parsed.channels.values() if not item.skipped)),
        ("Skipped channels", sum(1 for item in parsed.channels.values() if item.skipped)),
        ("Cleaned events", len(parsed.events)),
    )
    for index, (label, value) in enumerate(run_summary, start=summary_row):
        sheet.write(index, 0, label, formats["text"])
        sheet.write(index, 1, value, formats["integer"])

    channel_start = summary_row + len(run_summary) + 3
    _write_channel_table(sheet, parsed, channel_start, formats)

    sheet.set_column("A:A", 28)
    sheet.set_column("B:B", 95)
    sheet.set_column("D:D", 16)
    sheet.set_column("E:G", 14)
    sheet.set_column("I:J", 14)
    sheet.freeze_panes(1, 0)


def _write_channel_table(
    sheet: xlsxwriter.worksheet.Worksheet,
    parsed: ParsedDetectionOutput,
    start_row: int,
    formats: Dict[str, xlsxwriter.format.Format],
) -> None:
    headers = ("Channel", "Events", "Included in cleaned", "Sampling rate", "Io", "Reason")
    for col, header in enumerate(headers):
        sheet.write(start_row, col, header, formats["header"])

    for row_index, summary in enumerate(sorted(parsed.channels.values(), key=lambda item: item.channel), start=start_row + 1):
        sheet.write(row_index, 0, summary.channel, formats["integer"])
        sheet.write(row_index, 1, summary.event_count or 0, formats["integer"])
        sheet.write(row_index, 2, "No" if summary.skipped else "Yes", formats["text"])
        if summary.sampling_rate is not None:
            sheet.write(row_index, 3, summary.sampling_rate, formats["decimal"])
        if summary.open_current is not None:
            sheet.write(row_index, 4, summary.open_current, formats["decimal"])
        sheet.write(row_index, 5, summary.reason, formats["text"])


def _write_histogram(
    workbook: xlsxwriter.Workbook,
    sheet: xlsxwriter.worksheet.Worksheet,
    parsed: ParsedDetectionOutput,
    start_row: int,
    formats: Dict[str, xlsxwriter.format.Format],
) -> None:
    bins, counts, more = histogram_counts(event[-1] for event in parsed.events)
    sheet.write(start_row - 2, 8, "Histogram", formats["section"])
    sheet.write(start_row - 1, 8, "Bin", formats["header"])
    sheet.write(start_row - 1, 9, "Frequency", formats["header"])
    for offset, (bin_value, count) in enumerate(zip(bins, counts)):
        sheet.write_number(start_row + offset, 8, bin_value, formats["decimal"])
        sheet.write_number(start_row + offset, 9, count, formats["integer"])
    more_row = start_row + len(bins)
    sheet.write(more_row, 8, "More", formats["text"])
    sheet.write_number(more_row, 9, more, formats["integer"])
    total_row = more_row + 2
    sheet.write(total_row, 8, "Total", formats["header"])
    total = sum(counts) + more
    sheet.write_formula(
        total_row,
        9,
        f"=SUM(J{start_row + 1}:J{more_row + 1})",
        formats["integer"],
        total,
    )

    chart = workbook.add_chart({"type": "column"})
    chart.add_series(
        {
            "name": "Frequency",
            "categories": ["Summary", start_row, 8, more_row, 8],
            "values": ["Summary", start_row, 9, more_row, 9],
        }
    )
    chart.set_title({"name": "Histogram"})
    chart.set_x_axis({"name": "Bin"})
    chart.set_y_axis({"name": "Frequency"})
    chart.set_legend({"position": "right"})
    sheet.insert_chart("L8", chart, {"x_scale": 1.35, "y_scale": 1.2})


def _write_event_sheets(
    workbook: xlsxwriter.Workbook,
    events: List[Tuple[int, int, int, int, float]],
    formats: Dict[str, xlsxwriter.format.Format],
) -> None:
    rows_per_sheet = EXCEL_MAX_ROWS - 1
    if not events:
        sheet = workbook.add_worksheet("Events")
        _write_event_header(sheet, formats)
        return

    for sheet_index, event_chunk in enumerate(_chunks(events, rows_per_sheet), start=1):
        sheet_name = "Events" if sheet_index == 1 else f"Events {sheet_index}"
        sheet = workbook.add_worksheet(sheet_name)
        _write_event_header(sheet, formats)
        for row_offset, event in enumerate(event_chunk, start=1):
            channel, event_id, start, end, ir_io = event
            sheet.write_number(row_offset, 0, channel, formats["integer"])
            sheet.write_number(row_offset, 1, event_id, formats["integer"])
            sheet.write_number(row_offset, 2, start, formats["integer"])
            sheet.write_number(row_offset, 3, end, formats["integer"])
            sheet.write_number(row_offset, 4, ir_io, formats["decimal"])
        sheet.set_column("A:E", 14)
        sheet.freeze_panes(1, 0)


def _write_event_header(
    sheet: xlsxwriter.worksheet.Worksheet,
    formats: Dict[str, xlsxwriter.format.Format],
) -> None:
    for col, header in enumerate(EVENT_HEADERS):
        sheet.write(0, col, header, formats["header"])


def _chunks(
    values: List[Tuple[int, int, int, int, float]],
    size: int,
) -> Iterator[List[Tuple[int, int, int, int, float]]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]
