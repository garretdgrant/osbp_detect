from __future__ import annotations

import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import subprocess
from pathlib import Path
from typing import Optional

from tkinter import NSEW, StringVar, Tk, filedialog, messagebox, Canvas, Frame, Label, Entry, Button
from tkinter import ttk
from tkinter import font as tkfont

from run import (
    CHANNEL_RANGE,
    MAX_EVENTS_CLEAN,
    MIN_IrIo,
    STRICT_IrIo,
    TPS_RANGE,
    start_detection,
)

API_NAME = "OsBp Detect v3.0"
WINDOW_SIZE = (520, 820)


class DetectionGUI:
    """Refined Tkinter interface for nanopore event detection with professional aesthetics."""

    # Color Palette - Refined Scientific Instrument Theme
    BG_PRIMARY = "#0a0e14"      # Deep space black
    BG_SECONDARY = "#151b24"    # Elevated surface
    BG_TERTIARY = "#1e2936"     # Card background
    ACCENT_BLUE = "#00d4ff"     # Electric cyan
    ACCENT_GLOW = "#0099cc"     # Dimmer glow
    TEXT_PRIMARY = "#e8eef5"    # Soft white
    TEXT_SECONDARY = "#8a99a8"  # Muted gray
    TEXT_TERTIARY = "#5a6a7a"   # Subtle gray
    BORDER_COLOR = "#2a3544"    # Subtle borders
    INPUT_BG = "#1a2230"        # Input field background
    INPUT_FOCUS = "#223344"     # Input focused state

    def __init__(self) -> None:
        self.root = Tk()
        self.root.title(API_NAME)
        self.root.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        self.root.configure(bg=self.BG_PRIMARY)
        self.root.resizable(False, False)

        # Configure grid
        self.root.columnconfigure(0, weight=1)

        # Custom fonts
        try:
            self.font_title = tkfont.Font(family="SF Pro Display", size=24, weight="bold")
            self.font_heading = tkfont.Font(family="SF Pro Text", size=11, weight="bold")
            self.font_label = tkfont.Font(family="SF Pro Text", size=10)
            self.font_mono = tkfont.Font(family="SF Mono", size=10)
        except:
            # Fallback fonts
            self.font_title = tkfont.Font(family="Helvetica", size=24, weight="bold")
            self.font_heading = tkfont.Font(family="Helvetica", size=11, weight="bold")
            self.font_label = tkfont.Font(family="Helvetica", size=10)
            self.font_mono = tkfont.Font(family="Courier", size=10)

        # State
        self.in_fast5: Optional[Path] = None
        self.out_fast5: Optional[Path] = None
        self.in_fast5_label_text = StringVar(value="No file selected")
        self.out_fast5_label_text = StringVar(value="No folder selected")

        # Parameters
        self.start_var = StringVar(value=str(CHANNEL_RANGE[0]))
        self.end_var = StringVar(value=str(CHANNEL_RANGE[1]))
        self.min_time_var = StringVar(value=str(TPS_RANGE[0]))
        self.max_time_var = StringVar(value=str(TPS_RANGE[1]))
        self.all_irio_var = StringVar(value=str(STRICT_IrIo))
        self.min_irio_var = StringVar(value=str(MIN_IrIo))
        self.max_events_clean_var = StringVar(value=str(MAX_EVENTS_CLEAN))

        # Build interface
        self._apply_styles()
        self._build_layout()

    def _apply_styles(self) -> None:
        """Configure ttk styles for custom themed widgets."""
        style = ttk.Style(self.root)
        style.theme_use("clam")

        # Card/Section frames
        style.configure(
            "Card.TFrame",
            background=self.BG_TERTIARY,
            relief="flat",
        )

        # Labels
        style.configure(
            "Heading.TLabel",
            background=self.BG_TERTIARY,
            foreground=self.ACCENT_BLUE,
            font=self.font_heading,
        )
        style.configure(
            "Label.TLabel",
            background=self.BG_TERTIARY,
            foreground=self.TEXT_SECONDARY,
            font=self.font_label,
        )
        style.configure(
            "Value.TLabel",
            background=self.BG_TERTIARY,
            foreground=self.TEXT_TERTIARY,
            font=self.font_mono,
        )

        # Entry fields
        style.configure(
            "Custom.TEntry",
            fieldbackground=self.INPUT_BG,
            background=self.INPUT_BG,
            foreground=self.TEXT_PRIMARY,
            bordercolor=self.BORDER_COLOR,
            lightcolor=self.INPUT_FOCUS,
            darkcolor=self.INPUT_FOCUS,
            insertcolor=self.ACCENT_BLUE,
            relief="flat",
        )
        style.map(
            "Custom.TEntry",
            fieldbackground=[("focus", self.INPUT_FOCUS)],
            bordercolor=[("focus", self.ACCENT_BLUE)],
        )

        # Buttons
        style.configure(
            "File.TButton",
            background=self.BG_SECONDARY,
            foreground=self.TEXT_PRIMARY,
            bordercolor=self.BORDER_COLOR,
            borderwidth=1,
            relief="flat",
            padding=(12, 8),
            font=self.font_label,
        )
        style.map(
            "File.TButton",
            background=[("active", self.BG_TERTIARY)],
            foreground=[("active", self.ACCENT_BLUE)],
        )

        style.configure(
            "Run.TButton",
            background=self.ACCENT_BLUE,
            foreground=self.BG_PRIMARY,
            borderwidth=0,
            relief="flat",
            padding=(16, 12),
            font=self.font_heading,
        )
        style.map(
            "Run.TButton",
            background=[("active", self.ACCENT_GLOW)],
        )

    def _create_card(self, parent, row: int) -> ttk.Frame:
        """Create a styled card container."""
        card = ttk.Frame(parent, style="Card.TFrame", padding=16)
        card.grid(row=row, column=0, padx=24, pady=10, sticky="ew")
        return card

    def _create_section_heading(self, parent, text: str, row: int) -> None:
        """Create a section heading with accent styling."""
        label = ttk.Label(parent, text=text, style="Heading.TLabel")
        label.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))

    def _create_input_row(
        self, parent, row: int, label_text: str, textvariable: StringVar
    ) -> None:
        """Create a labeled input field row."""
        label = ttk.Label(parent, text=label_text, style="Label.TLabel")
        label.grid(row=row, column=0, sticky="w", pady=4)

        entry = ttk.Entry(
            parent, textvariable=textvariable, style="Custom.TEntry", font=self.font_mono
        )
        entry.grid(row=row, column=1, sticky="ew", pady=4, padx=(16, 0))
        parent.columnconfigure(1, weight=1)

    def _build_layout(self) -> None:
        """Build the refined interface with card-based sections."""
        # Header
        header_frame = Frame(self.root, bg=self.BG_PRIMARY, height=70)
        header_frame.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 8))
        header_frame.grid_propagate(False)

        title = Label(
            header_frame,
            text="OsBp Detect",
            font=self.font_title,
            fg=self.TEXT_PRIMARY,
            bg=self.BG_PRIMARY,
        )
        title.pack(anchor="w", pady=(8, 0))

        subtitle = Label(
            header_frame,
            text="Nanopore Event Detection System",
            font=self.font_label,
            fg=self.TEXT_TERTIARY,
            bg=self.BG_PRIMARY,
        )
        subtitle.pack(anchor="w", pady=(2, 0))

        # Section 1: File I/O
        card1 = self._create_card(self.root, row=1)
        self._create_section_heading(card1, "01 — FILE I/O", row=0)

        btn_open = ttk.Button(
            card1,
            text="Select FAST5 File",
            command=self.open_file,
            style="File.TButton",
        )
        btn_open.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        file_status = ttk.Label(
            card1,
            textvariable=self.in_fast5_label_text,
            style="Value.TLabel",
        )
        file_status.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 16))

        btn_output = ttk.Button(
            card1,
            text="Select Output Folder",
            command=self.save_file,
            style="File.TButton",
        )
        btn_output.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(0, 8))

        output_status = ttk.Label(
            card1,
            textvariable=self.out_fast5_label_text,
            style="Value.TLabel",
        )
        output_status.grid(row=4, column=0, columnspan=2, sticky="w")

        # Section 2: Channels
        card2 = self._create_card(self.root, row=2)
        self._create_section_heading(card2, "02 — CHANNEL RANGE", row=0)
        self._create_input_row(card2, row=1, label_text="Start Channel", textvariable=self.start_var)
        self._create_input_row(card2, row=2, label_text="End Channel", textvariable=self.end_var)

        # Section 3: Detection Parameters
        card3 = self._create_card(self.root, row=3)
        self._create_section_heading(card3, "03 — DETECTION PARAMETERS", row=0)
        self._create_input_row(card3, row=1, label_text="Min Time (tps)", textvariable=self.min_time_var)
        self._create_input_row(card3, row=2, label_text="Max Time (tps)", textvariable=self.max_time_var)
        self._create_input_row(card3, row=3, label_text="Strict Ir/Io", textvariable=self.all_irio_var)
        self._create_input_row(card3, row=4, label_text="Min Ir/Io", textvariable=self.min_irio_var)
        self._create_input_row(card3, row=5, label_text="Max Events (clean)", textvariable=self.max_events_clean_var)

        # Run Button
        btn_run = ttk.Button(
            self.root,
            text="RUN DETECTION",
            command=self.execute,
            style="Run.TButton",
        )
        btn_run.grid(row=4, column=0, padx=24, pady=(10, 20), sticky="ew")

    def open_file(self) -> None:
        """Prompt the user for a FAST5 file and remember the selection."""
        selected = filedialog.askopenfilename(
            initialdir=str(Path.home()),
            title="Load file",
            filetypes=[("Bulk FAST5 files", ".fast5")],
        )
        if selected:
            self.in_fast5 = Path(selected).expanduser()
            self.in_fast5_label_text.set(f"✓ {self.in_fast5.name}")

    def save_file(self) -> None:
        """Prompt for a parent directory that will receive detection results."""
        selected = filedialog.askdirectory(
            initialdir=str(Path.home()), title="Select output folder"
        )
        if selected:
            self.out_fast5 = Path(selected).expanduser()
            # Truncate long paths for display
            display_path = str(self.out_fast5)
            if len(display_path) > 40:
                display_path = "..." + display_path[-37:]
            self.out_fast5_label_text.set(f"✓ {display_path}")

    def execute(self) -> None:
        """Validate inputs, then redirect stdout to the TSV file while running start_detection."""
        if not self.in_fast5:
            messagebox.showerror("Error", "Please specify the input file")
            return
        if not self.out_fast5:
            messagebox.showerror("Error", "Please specify the output folder")
            return

        try:
            start_int = int(self.start_var.get().strip())
            end_int = int(self.end_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Channel indices must be integers")
            return
        if start_int > end_int:
            messagebox.showerror("Error", "Start channel must be <= end channel")
            return

        try:
            t_min = int(self.min_time_var.get().strip())
            t_max = int(self.max_time_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Time thresholds must be integers")
            return
        if t_min >= t_max:
            messagebox.showerror("Error", "min(time) must be less than max(time)")
            return

        try:
            all_irio = float(self.all_irio_var.get().strip())
            min_irio = float(self.min_irio_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Ir/Io thresholds must be numeric")
            return
        try:
            max_events_clean = int(self.max_events_clean_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Max events (clean) must be an integer")
            return
        if max_events_clean <= 0:
            messagebox.showerror("Error", "Max events (clean) must be > 0")
            return

        channel_ids = list(range(start_int, end_int + 1))
        pst_now = datetime.now(ZoneInfo("America/Los_Angeles"))
        timestamp = pst_now.strftime("%d-%m-%y_%H-%M-%S")
        base_dir = self.out_fast5.resolve()
        run_dir = base_dir / f"{timestamp}_osbp_result"
        if run_dir.exists():
            suffix = 1
            while (base_dir / f"{timestamp}_osbp_result_{suffix}").exists():
                suffix += 1
            run_dir = base_dir / f"{timestamp}_osbp_result_{suffix}"
        run_dir.mkdir(parents=True, exist_ok=False)

        out_file = run_dir / "detections.tsv"

        suffix = out_file.suffix or ".tsv"
        clean_file = out_file.with_name(f"{out_file.stem}.cleaned{suffix}")
        skipped_file = out_file.with_name(f"{out_file.stem}.skipped{suffix}")

        def _write_header(handle: object) -> None:
            label_width = 12
            print("OSBP Detect v3.0", file=handle)
            print("-" * 40, file=handle)
            print(f"{'Input FAST5':<{label_width}}: {self.in_fast5.name}", file=handle)
            print(f"{'Duration':<{label_width}}: {t_min} - {t_max} tps", file=handle)
            print(f"{'Lowest Ir/Io':<{label_width}}: < {min_irio}", file=handle)
            print(f"{'All Ir/Io':<{label_width}}: < {all_irio}", file=handle)
            print(f"{'Max events':<{label_width}}: {max_events_clean}", file=handle)
            print("-" * 40, file=handle)
            print("", file=handle)

        with out_file.open("w", encoding="utf-8") as raw_handle, clean_file.open(
            "w", encoding="utf-8"
        ) as clean_handle, skipped_file.open("w", encoding="utf-8") as skipped_handle:
            _write_header(raw_handle)
            _write_header(clean_handle)
            _write_header(skipped_handle)
            start_detection(
                self.in_fast5,
                channel_ids,
                output_raw=raw_handle,
                output_clean=clean_handle,
                output_skipped=skipped_handle,
                duration=(t_min, t_max),
                min_thresh_i=min_irio,
                strict_thresh_i=all_irio,
                max_events_clean=max_events_clean,
            )

        print(
            f"FAST5 file processed successfully.\nOutput directory: {run_dir}",
            file=sys.stderr,
        )
        self._open_output_dir(run_dir)

        messagebox.showinfo(
            API_NAME,
            f"Analysis complete!\nOutput folder: {run_dir}",
        )
        self.root.quit()
        self.root.destroy()
        sys.exit(0)

    def run(self) -> None:
        """Start the Tkinter event loop."""
        self.root.mainloop()

    @staticmethod
    def _open_output_dir(path: Path) -> None:
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            elif sys.platform.startswith("win"):
                os.startfile(path)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception:
            print(f"Unable to open output directory: {path}", file=sys.stderr)


def main() -> None:
    """Entry point for `python3 gui.py`."""
    DetectionGUI().run()


if __name__ == "__main__":
    main()
