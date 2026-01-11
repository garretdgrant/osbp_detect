from __future__ import annotations

import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import os
import subprocess
from pathlib import Path
from typing import Optional

from tkinter import NSEW, StringVar, Tk, filedialog, messagebox
from tkinter import ttk

from run import MIN_IrIo, STRICT_IrIo, TPS_RANGE, start_detection, CHANNEL_RANGE

API_NAME = "OsBp Detect v3.0"
WINDOW_SIZE = (400, 550)


class DetectionGUI:
    """Thin Tkinter wrapper around the CLI pipeline so non-terminal users can run detections."""

    def __init__(self) -> None:
        self.root = Tk()
        self.root.title(API_NAME)
        self.root.geometry(f"{WINDOW_SIZE[0]}x{WINDOW_SIZE[1]}")
        # Configure basic layout
        self.root.columnconfigure(0, weight=1)
        self.root.columnconfigure(1, weight=1)

        # Style/theme setup
        style = ttk.Style(self.root)
        style.theme_use("clam")  # cleaner, cross-platform look

        # Dark-window + light-entry styling for macOS
        self.root.configure(bg="#202020")

        style.configure("TLabel", background="#202020", foreground="white")
        style.configure("TFrame", background="#202020")

        style.configure(
            "TEntry",
            foreground="#000000",
            fieldbackground="#FFFFFF",
            background="#FFFFFF",
            insertcolor="#000000",
        )
        style.configure("TButton", padding=4)

        self.in_fast5: Optional[Path] = None
        self.out_fast5: Optional[Path] = None

        self.start_var = StringVar(value=str(CHANNEL_RANGE[0]))
        self.end_var = StringVar(value=str(CHANNEL_RANGE[1]))
        self.min_time_var = StringVar(value=str(TPS_RANGE[0]))
        self.max_time_var = StringVar(value=str(TPS_RANGE[1]))
        self.all_irio_var = StringVar(value=str(STRICT_IrIo))
        self.min_irio_var = StringVar(value=str(MIN_IrIo))

        self._build_layout()

    def _build_layout(self) -> None:
        """Lay out the 3 input blocks: file I/O, channel range, detection thresholds."""
        ttk.Frame(self.root, height=10).grid(row=0, column=0)
        ttk.Label(
            self.root, text="1. File I/O:", font=("Helvetica", 10, "bold")
        ).grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 4), sticky="w")
        ttk.Button(
            self.root, text="Open FAST5 File", command=self.open_file
        ).grid(row=2, column=0, columnspan=2, padx=20, pady=4, sticky="ew")
        ttk.Frame(self.root, height=5).grid(row=3, column=0)
        ttk.Button(
            self.root, text="Select Output Folder", command=self.save_file
        ).grid(row=4, column=0, columnspan=2, padx=20, pady=4, sticky="ew")

        ttk.Frame(self.root, height=15).grid(row=5, column=0)
        ttk.Frame(self.root, height=2).grid(row=6, column=0, columnspan=2, sticky="ew")
        ttk.Frame(self.root, height=10).grid(row=7, column=0)

        ttk.Label(
            self.root, text="2. Channels:", font=("Helvetica", 10, "bold")
        ).grid(row=8, column=0, columnspan=2, padx=20, pady=(0, 4), sticky="w")
        ttk.Label(self.root, text="Start").grid(row=9, column=0, padx=10, sticky="e")
        ttk.Entry(self.root, textvariable=self.start_var).grid(
            row=9, column=1, padx=10, pady=3, sticky="ew"
        )
        ttk.Label(self.root, text="End").grid(row=10, column=0, padx=10, sticky="e")
        ttk.Entry(self.root, textvariable=self.end_var).grid(
            row=10, column=1, padx=10, pady=3, sticky="ew"
        )

        ttk.Frame(self.root, height=15).grid(row=11, column=0)
        ttk.Frame(self.root, height=2).grid(row=12, column=0, columnspan=2, sticky="ew")
        ttk.Frame(self.root, height=10).grid(row=13, column=0)

        ttk.Label(
            self.root, text="3. Thresholds:", font=("Helvetica", 10, "bold")
        ).grid(row=14, column=0, columnspan=2, padx=20, pady=(0, 4), sticky="w")
        ttk.Label(self.root, text="min(time)").grid(row=15, column=0, padx=10, sticky="e")
        ttk.Entry(self.root, textvariable=self.min_time_var).grid(
            row=15, column=1, padx=10, pady=3, sticky="ew"
        )
        ttk.Label(self.root, text="max(time)").grid(row=16, column=0, padx=10, sticky="e")
        ttk.Entry(self.root, textvariable=self.max_time_var).grid(
            row=16, column=1, padx=10, pady=3, sticky="ew"
        )
        ttk.Label(self.root, text="all(Ir/Io)").grid(row=17, column=0, padx=10, sticky="e")
        ttk.Entry(self.root, textvariable=self.all_irio_var).grid(
            row=17, column=1, padx=10, pady=3, sticky="ew"
        )
        ttk.Label(self.root, text="min(Ir/Io)").grid(row=18, column=0, padx=10, sticky="e")
        ttk.Entry(self.root, textvariable=self.min_irio_var).grid(
            row=18, column=1, padx=10, pady=3, sticky="ew"
        )

        ttk.Frame(self.root, height=15).grid(row=19, column=0)
        ttk.Frame(self.root, height=2).grid(row=20, column=0, columnspan=2, sticky="ew")
        ttk.Frame(self.root, height=10).grid(row=21, column=0)

        ttk.Button(self.root, text="Run", command=self.execute).grid(
            row=22, column=0, columnspan=2, padx=20, pady=8, sticky="ew"
        )

    def open_file(self) -> None:
        """Prompt the user for a FAST5 file and remember the selection."""
        selected = filedialog.askopenfilename(
            initialdir=str(Path.home()),
            title="Load file",
            filetypes=[("Bulk FAST5 files", ".fast5")],
        )
        if selected:
            self.in_fast5 = Path(selected).expanduser()

    def save_file(self) -> None:
        """Prompt for a parent directory that will receive detection results."""
        selected = filedialog.askdirectory(
            initialdir=str(Path.home()), title="Select output folder"
        )
        if selected:
            self.out_fast5 = Path(selected).expanduser()

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
