"""Signal processing helpers used by the CLI and GUI pipelines."""

from __future__ import annotations

from itertools import groupby
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from src.fast5_utils import ChannelInfo


def sec_to_tp(sec: float, sampl_rate: float) -> int:
    """
    Convert seconds into timepoints using the instrument sampling rate.

    Parameters
    ----------
    sec:
        Duration in seconds.
    sampl_rate:
        Digitizer sampling rate reported in Hz.
    """
    return int(sec * sampl_rate)


def trim_start(raw_signal: np.ndarray, trim_tps: int = 350_000) -> np.ndarray:
    """
    Zero out the initial region to stabilize indices during downstream filtering.

    Nanopore bulk acquisitions often have an initial drift or warm-up period. The
    detector discards it by replacing the head of the trace with zeros while
    preserving the downstream indices expected by the heuristics.
    """
    prefix = np.zeros(trim_tps, dtype=float)
    return np.concatenate((prefix, raw_signal[trim_tps:]))


def get_baseline(
    filtered_ary: np.ndarray, lower: int = 150, upper: int = 400
) -> Optional[float]:
    """
    Estimate the open-pore current Io using a robust median inside [lower, upper].

    Signals whose mean, standard deviation, or in-range density fall below the
    empirically tuned thresholds are rejected and reported as bad channels.
    """
    consts = {"min_ary_mean": 50.0, "min_ary_std": 10.0, "min_subset_n_prop": 0.01}
    baseline_out: Optional[float] = None

    if (
        filtered_ary.mean() > consts["min_ary_mean"]
        and filtered_ary.std() > consts["min_ary_std"]
    ):
        signal_subset = filtered_ary[(filtered_ary > lower) & (filtered_ary < upper)]
        if len(signal_subset) > len(filtered_ary) * consts["min_subset_n_prop"]:
            baseline_out = float(np.median(signal_subset))

    if baseline_out is None:
        print("Failed to identify baseline Io - bad channel")

    return baseline_out


def merge_consecutive_bool(
    mask: Sequence[bool],
) -> List[Tuple[bool, Tuple[int, int]]]:
    """
    Compress boolean runs into contiguous spans.

    Example:
        [True, True, False, False, False, True] => [(True, (0, 2)), (False, (2, 5)), (True, (5, 6))]
    """
    run_sum = 0
    out_lst: List[Tuple[bool, Tuple[int, int]]] = []
    count_bool = [(key, sum(1 for _ in group)) for key, group in groupby(mask)]
    for value, count in count_bool:
        start = run_sum
        run_sum += count
        out_lst.append((value, (start, run_sum)))

    if not out_lst:
        return []

    if not out_lst[0][0]:
        out_lst = out_lst[1:]
    if out_lst and not out_lst[-1][0]:
        out_lst = out_lst[:-1]
    return out_lst


def get_tranloc_idx(
    ex_filt_sig: np.ndarray,
    baseline_pA: float,
    baseline_dev: float = 30,
    t_range: Tuple[int, int] = (4, 150),
    min_depth_range: Tuple[float, float] = (0.0, 0.4),
    strict_depth: float = 0.6,
) -> List[Tuple[int, int]]:
    """
    Locate translocation windows by filtering contiguous drops in the signal.

    The baseline window (baseline_pA ± baseline_dev) defines the open channel.
    Events are kept when (1) they fall within the t_range duration bounds,
    (2) their minima stay between the min_depth_range proportions of Io, and
    (3) they never exceed the stricter Ir/Io ceiling.
    """
    assert len(t_range) == 2
    assert len(min_depth_range) == 2
    min_duration, max_duration = t_range
    lower_depth_thresh = min_depth_range[0] * baseline_pA
    upper_depth_thresh = min_depth_range[1] * baseline_pA
    upper_strict_depth = strict_depth * baseline_pA

    median_band = np.array(
        (ex_filt_sig < baseline_pA + baseline_dev)
        & (ex_filt_sig > baseline_pA - baseline_dev)
    )
    merged_idx = merge_consecutive_bool(median_band)

    filtered_idx: List[Tuple[int, int]] = []
    for key, idx in merged_idx:
        if not key:
            duration = idx[1] - idx[0]
            if min_duration <= duration <= max_duration:
                drop_current = ex_filt_sig[idx[0] : idx[1]]
                min_current = drop_current.min()
                if upper_depth_thresh > min_current > lower_depth_thresh:
                    if np.all(drop_current < upper_strict_depth):
                        filtered_idx.append(idx)
    print(f"{len(filtered_idx)} events detected.")
    return filtered_idx


def get_signal_pA(chann_info: ChannelInfo) -> np.ndarray:
    """
    Convert ADC units to picoamps using channel calibration metadata.

    Parameters
    ----------
    chann_info:
        ChannelInfo structure returned by ``OsBp_FAST5.get_channel_raw``; the sampling
        rate is carried forward and consumed by downstream heuristics.
    """
    raw_unit = chann_info.parange / chann_info.digitisation
    return (chann_info.raw_signal + chann_info.offset) * raw_unit


def detect_events(sig_ary: np.ndarray, **kwargs) -> Dict[str, object]:
    """
    Execute the baseline estimation + translocation detection pipeline.

    Parameters
    ----------
    sig_ary:
        Pore signal in picoamps for a single channel.
    kwargs:
        Forwarded to ``get_tranloc_idx`` to customize durations and depth limits.
    """
    out_dict: Dict[str, object] = {"open_current": -1.0, "event_idx": []}

    trim_sig = trim_start(sig_ary)
    open_pA = get_baseline(trim_sig)

    if open_pA is not None:
        transloc_idx = get_tranloc_idx(trim_sig, open_pA, **kwargs)
        out_dict["open_current"] = open_pA
        out_dict["event_idx"] = transloc_idx
    return out_dict
