import argparse
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

from src.fast5_utils import OsBp_FAST5
from src.signal_utils import detect_events, get_signal_pA


TPS_RANGE: Tuple[int, int] = (4, 1000)
IO_RANGE: Tuple[int, int] = (150, 300)
MIN_IrIo: float = 0.30
STRICT_IrIo: float = 0.60


def start_detection(
    file_in: Union[Path, str],
    channel_query: Sequence[int],
    duration: Tuple[int, int] = TPS_RANGE,
    min_thresh_i: float = MIN_IrIo,
    strict_thresh_i: float = STRICT_IrIo,
    io_range: Tuple[int, int] = IO_RANGE,
) -> None:
    """Run detection for the requested FAST5 and channels."""
    if not channel_query:
        print("No channels supplied; exiting.")
        return

    fast5_path = Path(file_in)
    with OsBp_FAST5(str(fast5_path)) as g:
        for channel_no in channel_query:
            print(f"Processing channel {channel_no}...")
            info_obj = g.get_channel_raw(channel_no)
            # Convert the raw ADC trace into absolute picoamp measurements.
            signal_ary = get_signal_pA(info_obj)
            detect_out = detect_events(
                signal_ary,
                t_range=duration,
                min_depth_range=(0.0, min_thresh_i),
                strict_depth=strict_thresh_i,
            )
            open_pA = detect_out["open_current"]
            # Skip channels whose inferred baseline current lies outside the expected pore window.
            if io_range[0] <= open_pA <= io_range[1]:
                print(
                    f"# Channel {channel_no}, Sampling rate: {info_obj.sampling_rate} Hz, "
                    f"Io: {open_pA} pA\n"
                )
                for event_id, event_idx in enumerate(detect_out["event_idx"], start=1):
                    start, end = event_idx
                    this_event = signal_ary[start:end]
                    min_pA = float(this_event.min())
                    # Report event start/end indices plus the depth ratio to open current.
                    print(f"{event_id}\t{start}\t{end}\t{min_pA / open_pA}")
            print("")


def _parse_channel_range(raw_value: str) -> List[int]:
    """Turn a start-end string into a list of channel ids (end exclusive)."""
    try:
        start_raw, end_raw = raw_value.split("-", 1)
        start, end = int(start_raw), int(end_raw)
    except ValueError as exc:
        raise ValueError("Invalid range format (expected start-end).") from exc
    if start >= end:
        raise ValueError("Channel range start must be less than end.")
    return [i for i in range(start, end)]


def _parse_channel_list(raw_value: str) -> List[int]:
    """Parse comma-separated integers into a list of unique channel ids."""
    try:
        split_vals = [token.strip() for token in raw_value.split(",") if token.strip()]
        if not split_vals:
            raise ValueError
        return [int(token) for token in split_vals]
    except ValueError as exc:
        raise ValueError("Channel list must be comma-separated integers.") from exc


def _resolve_channel_selection(args: argparse.Namespace, parser: argparse.ArgumentParser) -> List[int]:
    """Validate the caller's channel selection and remove any blacklisted ids."""
    if args.channel_range and args.channel_specific:
        parser.error("Specify only one of -r/--range or -s/--channels.")

    channels: List[int] = []
    if args.channel_range:
        try:
            channels = _parse_channel_range(args.channel_range)
        except ValueError as exc:
            parser.error(str(exc))
    elif args.channel_specific:
        try:
            channels = sorted(set(_parse_channel_list(args.channel_specific)))
        except ValueError as exc:
            parser.error(str(exc))
    else:
        parser.error("You must provide channel indices via -r/--range or -s/--channels.")

    blacklist: Iterable[int] = []
    if args.blacklist:
        try:
            blacklist = set(_parse_channel_list(args.blacklist))
        except ValueError as exc:
            parser.error(f"Invalid blacklist: {exc}")

    filtered_channels = [channel for channel in channels if channel not in blacklist]
    if not filtered_channels:
        parser.error("No channels remain after applying the blacklist.")
    return filtered_channels


def cli(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Configure and parse the CLI, returning validated arguments."""
    parser = argparse.ArgumentParser(
        description="Detect events corresponding to short, single miRNA translocations"
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        metavar="FAST5",
        help="Path to input FAST5 file",
    )
    parser.add_argument(
        "-r",
        "--range",
        dest="channel_range",
        help="Channel range to analyse, start-end (end exclusive)",
    )
    parser.add_argument(
        "-s",
        "--channels",
        dest="channel_specific",
        help="Specific channels, comma-separated (e.g. 1,4,8)",
    )
    parser.add_argument(
        "-b",
        "--blacklist",
        help="Channels to skip, comma-separated (applied after range/selection)",
    )
    parser.add_argument(
        "--duration",
        nargs=2,
        type=int,
        metavar=("MIN", "MAX"),
        default=TPS_RANGE,
        help="Event duration window in timepoints (default: %(default)s)",
    )
    parser.add_argument(
        "--min-irio",
        type=float,
        default=MIN_IrIo,
        help="Minimum Ir/Io threshold (default: %(default)s)",
    )
    parser.add_argument(
        "--strict-irio",
        type=float,
        default=STRICT_IrIo,
        help="Strict Ir/Io threshold applied to all samples (default: %(default)s)",
    )
    args = parser.parse_args(args=argv)

    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        parser.error(f"Input FAST5 does not exist: {input_path}")

    args.input_path = input_path
    args.channels = _resolve_channel_selection(args, parser)
    return args


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = cli(argv)
    start_detection(
        file_in=args.input_path,
        channel_query=args.channels,
        duration=tuple(args.duration),
        min_thresh_i=args.min_irio,
        strict_thresh_i=args.strict_irio,
    )


if __name__ == "__main__":
    main()
