"""FAST5 utilities for OsBp detection pipelines."""

from __future__ import annotations

import sys
from typing import NamedTuple, Optional

import h5py
import hdf5plugin  # noqa: F401  (ensures HDF5 compression filters are registered)
import numpy as np

try:
    from ont_fast5_api.fast5_interface import get_fast5_file
except ImportError:  # pragma: no cover - optional dependency
    get_fast5_file = None


class ChannelInfo(NamedTuple):
    """Aggregated FAST5 metadata needed to convert raw ADC samples to picoamps."""

    digitisation: float
    parange: float
    offset: float
    sampling_rate: float
    raw_signal: np.ndarray


class OsBp_FAST5:
    """Context manager that yields FAST5 handles with ONT plugin support when available."""

    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.handle: Optional[h5py.File] = None
        self._ont_ctx = None

    def __enter__(self) -> "OsBp_FAST5":
        self._open_handle()
        return self

    def __exit__(self, exception_type, exception_value, traceback) -> None:
        if self._ont_ctx is not None:
            self._ont_ctx.__exit__(exception_type, exception_value, traceback)
            self._ont_ctx = None
            self.handle = None
        elif self.handle:
            self.handle.close()
            self.handle = None
        self.filename = None

    def _open_handle(self) -> None:
        """
        Prefer ONT's reader (bundles FAST5 plugins); fall back to raw h5py if unavailable.
        Bulk FAST5 files are expected to raise in ont-fast5-api (unsupported), so we
        treat that as a normal path and log on stderr without polluting TSV output.
        """
        if get_fast5_file is not None:
            try:
                self._ont_ctx = get_fast5_file(self.filename, mode="r")
                ont_handle = self._ont_ctx.__enter__()
                # The ONT wrapper exposes the underlying h5py file via different attributes
                # depending on multi/single FAST5 implementations.
                candidate = getattr(ont_handle, "handle", None)
                if candidate is None:
                    candidate = getattr(ont_handle, "h5py_file", None)
                if candidate is None and isinstance(ont_handle, h5py.File):
                    candidate = ont_handle
                if candidate is not None:
                    self.handle = candidate
                    return
            except Exception as exc:
                sys.stderr.write(
                    "Warning: ont-fast5-api open failed ({}). Falling back to h5py. "
                    "This is expected for bulk FAST5 files because the ONT API only supports multi/reads.\n".format(
                        exc
                    )
                )
                if self._ont_ctx is not None:
                    self._ont_ctx.__exit__(None, None, None)
                    self._ont_ctx = None
        # Fallback path uses vanilla h5py; `hdf5plugin` import above registers ONT filters.
        if self.handle is None:
            self.handle = h5py.File(self.filename, mode="r")

    def get_channel_raw(self, channel_id: int) -> ChannelInfo:
        """
        Extract raw channel samples plus the metadata required for picoamp conversion.

        Parameters
        ----------
        channel_id:
            1-based bulk FAST5 channel identifier.
        """
        if self.handle is None:
            raise RuntimeError("FAST5 handle not opened; use OsBp_FAST5 as a context.")

        raw_obj = self.handle["Raw"]
        channel_name = f"Channel_{channel_id}"
        if channel_name not in raw_obj:
            raise KeyError(f'Channel "{channel_name}" not in: {self.filename}')
        channel_obj = raw_obj[channel_name]

        meta = channel_obj["Meta"].attrs
        raw_signal: np.ndarray = channel_obj["Signal"][()]

        # Bundle the waveform with the metadata needed for downstream pA conversion.
        return ChannelInfo(
            raw_signal=raw_signal,
            digitisation=float(meta["digitisation"]),
            parange=float(meta["range"]),
            offset=float(meta["offset"]),
            sampling_rate=float(meta["sample_rate"]),
        )
