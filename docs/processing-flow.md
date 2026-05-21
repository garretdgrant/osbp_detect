# FAST5 Processing Flow

This document summarizes how `osbp_detect` turns a raw bulk FAST5 file into the
three tab-separated result files written by the CLI or GUI.

Example input:

```text
test-files/AnastassiasMBP3.attlocal.net_20241229_1229_FBB00577_MN36712_sequencing_run_Dec29_00577_nonew2_A1_probe21_c06cf841_e0a0a5d7.fast5
```

Example GUI output folder:

```text
test-files/processed/11-01-26_08:01:14_osbp_result/
```

Current GUI runs create folders named `dd-mm-yy_HH-MM-SS_osbp_result` using
America/Los_Angeles time. If a folder for the same second already exists, the
GUI appends an incrementing suffix such as `_1`.

Some checked-in sample folders may use older timestamp formatting with colons,
for example `11-01-26_08:01:14_osbp_result`.

## Entry Points

- `gui.py`: desktop UI. Collects the FAST5 path, output parent folder, channel
  range, and detection thresholds. Creates the timestamped output folder and
  writes headers to all output files before calling `start_detection()`.
- `run.py`: CLI. Parses arguments and writes the three TSV outputs directly.
  When no output paths are supplied, files are written beside the input FAST5.
- `run.start_detection()`: shared processing function used by both entry
  points.

## Input Shape

The detector expects a bulk FAST5 layout with raw channel groups:

```text
Raw/
  Channel_1/
    Meta
    Signal
  Channel_2/
    Meta
    Signal
  ...
```

Each channel's `Meta` attributes must include:

- `digitisation`
- `range`
- `offset`
- `sample_rate`

`src.fast5_utils.OsBp_FAST5` opens the FAST5 file. It first attempts ONT's
`ont_fast5_api` reader, then falls back to `h5py`. The `hdf5plugin` import is
kept so HDF5 compression filters used by ONT files are registered.

## Per-Channel Flow

For each selected channel:

1. `OsBp_FAST5.get_channel_raw(channel_id)` reads `Raw/Channel_N/Signal` and
   the calibration metadata into a `ChannelInfo` tuple.
2. `signal_utils.get_signal_pA()` converts raw ADC values to picoamps:

   ```python
   raw_unit = parange / digitisation
   signal_pA = (raw_signal + offset) * raw_unit
   ```

3. `signal_utils.detect_events()` runs the event detector:
   - `trim_start()` replaces the first `350_000` samples with zeros while
     preserving sample indices.
   - `get_baseline()` estimates open-pore current `Io` as the median of samples
     between `150` and `400` pA, after basic mean, standard deviation, and
     density checks.
   - `get_tranloc_idx()` identifies contiguous regions outside the
     `Io +/- 30 pA` open-current band.
   - Candidate regions are kept only when they pass duration and depth filters.

4. `run.start_detection()` rejects the channel unless `Io` is inside the
   expected open-pore current range, currently `150-300` pA.
5. Accepted events are written to the output files.

## Detection Defaults

Default constants live near the top of `run.py`.

| Name | Default | Meaning |
| --- | ---: | --- |
| `CHANNEL_RANGE` | `1-512` | GUI default channel window |
| `TPS_RANGE` | `4-1200` | Event duration bounds in samples/timepoints |
| `IO_RANGE` | `150-300` | Accepted open-pore current range in pA |
| `MIN_IrIo` | `0.55` | Event minimum current must be below this `Io` ratio |
| `STRICT_IrIo` | `0.60` | Every sample in the event must be below this `Io` ratio |
| `MAX_EVENTS_CLEAN` | `100000` | Channels above this event count are excluded from cleaned output |

The detector reports event windows using sample indices, not seconds. The
channel sampling rate is printed in each channel block for downstream
conversion if needed.

## Output Files

Both entry points produce three tab-separated files:

```text
detections.tsv
detections.cleaned.tsv
detections.skipped.tsv
```

The GUI places them in a timestamped output folder. The CLI writes default files
beside the input FAST5 using the input stem:

```text
<input>.detections.tsv
<input>.detections.cleaned.tsv
<input>.detections.skipped.tsv
```

### `detections.tsv`

Contains every accepted channel and event, including channels with very high
event counts.

Each channel block has:

```text
Processing channel 5...
2901 events detected.
# Channel 5, Sampling rate: 3012.0 Hz, Io: 172.5911571085453 pA

1    537382    537392    0.2769874476987448
2    547501    547542    0.2560669456066946
```

Event columns are:

| Column | Meaning |
| --- | --- |
| `event_id` | 1-based event number within the channel |
| `start` | inclusive sample index where the event window begins |
| `end` | exclusive sample index where the event window ends |
| `min_current / Io` | event minimum current divided by channel open current |

### `detections.cleaned.tsv`

Uses the same channel and event format as `detections.tsv`, but excludes any
channel where `event_count > MAX_EVENTS_CLEAN`.

This file is intended for downstream review when extreme event-count channels
are likely to be noisy or otherwise unsuitable.

### `detections.skipped.tsv`

Lists only channels excluded from `detections.cleaned.tsv` because they exceeded
the clean-output threshold:

```text
Skipped channel 4
67265 events detected
```

Those channels are still present in `detections.tsv` if they passed the `Io`
range check.

## Notes And Edge Cases

- The files use TSV formatting even though users may casually refer to them as
  CSVs.
- CLI channel ranges are end-exclusive: `-r 1-64` processes channels `1` through
  `63`.
- GUI channel ranges are end-inclusive: start `1`, end `64` processes channels
  `1` through `64`.
- Channels that fail baseline detection or whose `Io` is outside `150-300` pA
  are not written to any of the three result files.
- `detect_events()` prints event counts to stdout. GUI and CLI result writing is
  controlled by explicit file handles passed into `start_detection()`.
