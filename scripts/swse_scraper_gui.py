#!/usr/bin/env python3
"""Small desktop GUI for the SWSE wiki exporter.

The GUI writes a temporary target list and delegates downloading to
scrape_swse_wiki.py, so it uses the same extraction, throttling, and cache logic
as the command-line tool without asking users to edit a manifest by hand.
"""

from __future__ import annotations

import os
import queue
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any

try:
    import tkinter as tk
    from tkinter import TclError, filedialog, messagebox, ttk
except ImportError:  # Keep URL parsing testable on headless/minimal Python builds.
    tk = None  # type: ignore[assignment]
    filedialog = None  # type: ignore[assignment]
    messagebox = None  # type: ignore[assignment]
    ttk = None  # type: ignore[assignment]

    class TclError(Exception):
        pass

import scrape_swse_wiki as scraper


ROOT = Path(__file__).resolve().parents[1]
URL_TOKEN = re.compile(r"https?://[^\s<>\[\]]+", re.IGNORECASE)
CURRENT_PAGE = re.compile(r"^\[(\d+)/(\d+)\]\s+(.+)$")


def _trim_url_token(token: str) -> str:
    token = token.strip().rstrip(".,;!\"'`")
    # Markdown links may leave one unmatched ')' after the URL itself, e.g.
    # [https://wiki/page_(name)](https://wiki/page_(name)).
    while token.endswith(")") and token.count(")") > token.count("("):
        token = token[:-1]
    return token


def parse_url_text(text: str) -> tuple[list[str], list[tuple[str, str]]]:
    """Extract and normalize supported wiki URLs from pasted text/Markdown.

    Returns (unique_valid_urls, rejected_candidates_with_reason).
    """
    valid: list[str] = []
    invalid: list[tuple[str, str]] = []
    seen: set[str] = set()
    for match in URL_TOKEN.findall(text):
        candidate = _trim_url_token(match)
        if not candidate:
            continue
        try:
            url = scraper.normalize_url(candidate)
        except ValueError as exc:
            invalid.append((candidate, str(exc)))
            continue
        if url not in seen:
            valid.append(url)
            seen.add(url)
    return valid, invalid


class ScraperWindow:
    def __init__(self, root: Any):
        if tk is None or ttk is None or messagebox is None or filedialog is None:
            raise RuntimeError("Tkinter is not available in this Python installation")

        self.root = root
        self.root.title("SWSE Wiki Downloader")
        self.root.geometry("860x760")
        self.root.minsize(700, 620)
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)

        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.process: subprocess.Popen[str] | None = None
        self.worker: threading.Thread | None = None
        self.temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self.stop_requested = False
        self.custom_urls: list[str] = []

        self.include_defaults = tk.BooleanVar(value=True)
        self.discover_custom = tk.BooleanVar(value=False)
        self.refresh = tk.BooleanVar(value=False)
        self.workers = tk.StringVar(value="25")
        self.delay = tk.StringVar(value="0.0")
        self.output_dir = tk.StringVar(value=str(scraper.DEFAULT_OUTPUT))
        self.status = tk.StringVar(value="Ready")

        self._build_ui()
        self.root.after(120, self._poll_events)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=14)
        outer.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(3, weight=1)
        outer.rowconfigure(8, weight=2)

        ttk.Label(outer, text="SWSE Wiki Downloader", font=("TkDefaultFont", 18, "bold")).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            outer,
            text="Choose the supplied SWSE page set, paste additional page links, or do both.",
            wraplength=800,
        ).grid(row=1, column=0, sticky="w", pady=(3, 12))

        defaults = ttk.LabelFrame(outer, text="Pages to download", padding=10)
        defaults.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        defaults.columnconfigure(0, weight=1)
        ttk.Checkbutton(
            defaults,
            text="Include the built-in SWSE page set (overview pages, classes, and linked catalog entries)",
            variable=self.include_defaults,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            defaults,
            text="This set also expands links one level from the Feats, Talents, Force Powers, and Species catalogues.",
            wraplength=780,
        ).grid(row=1, column=0, sticky="w", padx=(24, 0), pady=(2, 0))

        custom = ttk.LabelFrame(outer, text="Add page links (optional)", padding=10)
        custom.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        custom.columnconfigure(0, weight=1)
        custom.rowconfigure(1, weight=1)

        ttk.Label(
            custom,
            text="Paste URLs or the Markdown link list you already have; the app extracts the addresses automatically. Supported sites: swse.miraheze.org and swse.fandom.com.",
            wraplength=780,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))

        self.url_entry = tk.Text(custom, height=4, wrap="word", undo=True)
        self.url_entry.grid(row=1, column=0, sticky="nsew")
        self.url_entry.bind("<Control-Return>", lambda _event: self.add_urls())
        try:
            self.url_entry.bind("<Command-Return>", lambda _event: self.add_urls())
        except TclError:
            pass
        entry_scroll = ttk.Scrollbar(custom, orient="vertical", command=self.url_entry.yview)
        entry_scroll.grid(row=1, column=1, sticky="ns")
        self.url_entry.configure(yscrollcommand=entry_scroll.set)

        url_buttons = ttk.Frame(custom)
        url_buttons.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6, 6))
        ttk.Button(url_buttons, text="Add pasted link(s)", command=self.add_urls).pack(side="left")
        ttk.Button(url_buttons, text="Remove selected", command=self.remove_selected).pack(side="left", padx=(6, 0))
        ttk.Button(url_buttons, text="Clear list", command=self.clear_urls).pack(side="left", padx=(6, 0))
        self.url_count = ttk.Label(url_buttons, text="0 additional URLs")
        self.url_count.pack(side="right")

        self.url_list = tk.Listbox(custom, height=5, selectmode="extended", exportselection=False)
        self.url_list.grid(row=3, column=0, sticky="nsew")
        list_scroll = ttk.Scrollbar(custom, orient="vertical", command=self.url_list.yview)
        list_scroll.grid(row=3, column=1, sticky="ns")
        self.url_list.configure(yscrollcommand=list_scroll.set)
        ttk.Checkbutton(
            custom,
            text="Also fetch links from my added URLs (use this for index/list pages only)",
            variable=self.discover_custom,
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(6, 0))

        options = ttk.LabelFrame(outer, text="Export options", padding=10)
        options.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        options.columnconfigure(1, weight=1)
        ttk.Label(options, text="Save Markdown to:").grid(row=0, column=0, sticky="w")
        ttk.Entry(options, textvariable=self.output_dir).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(options, text="Browse…", command=self.choose_output).grid(row=0, column=2, sticky="e")
        worker_options = ttk.Frame(options)
        worker_options.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Label(worker_options, text="Parallel workers (1–50; default 25):").pack(side="left")
        ttk.Spinbox(worker_options, from_=1, to=50, increment=1, textvariable=self.workers, width=6).pack(
            side="left", padx=(6, 16)
        )
        ttk.Label(worker_options, text="Request-start delay (seconds):").pack(side="left")
        ttk.Spinbox(worker_options, from_=0.0, to=30.0, increment=0.1, textvariable=self.delay, width=6).pack(
            side="left", padx=(6, 0)
        )
        ttk.Checkbutton(
            options,
            text="Refresh all pages instead of using the HTTP cache",
            variable=self.refresh,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(7, 0))

        actions = ttk.Frame(outer)
        actions.grid(row=5, column=0, sticky="ew", pady=(0, 5))
        self.start_button = ttk.Button(actions, text="Start download", command=self.start_download)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(actions, text="Stop", command=self.stop_download, state="disabled")
        self.stop_button.pack(side="left", padx=(6, 0))
        ttk.Button(actions, text="Open export folder", command=self.open_output).pack(side="right")

        self.progress = ttk.Progressbar(outer, mode="indeterminate")
        self.progress.grid(row=6, column=0, sticky="ew", pady=(2, 4))
        ttk.Label(outer, textvariable=self.status).grid(row=7, column=0, sticky="nw", pady=(0, 4))

        log_frame = ttk.LabelFrame(outer, text="Activity", padding=6)
        log_frame.grid(row=8, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_text = tk.Text(log_frame, height=9, wrap="word", state="disabled")
        self.log_text.grid(row=0, column=0, sticky="nsew")
        log_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=log_scroll.set)

        ttk.Label(
            outer,
            text="Pages are saved as Markdown with source links. Check each wiki's current license before publishing the export.",
            wraplength=800,
        ).grid(row=9, column=0, sticky="w", pady=(8, 0))

    def add_urls(self) -> None:
        pasted = self.url_entry.get("1.0", "end-1c")
        urls, invalid = parse_url_text(pasted)
        self.url_entry.delete("1.0", "end")

        added = 0
        for url in urls:
            if url not in self.custom_urls:
                self.custom_urls.append(url)
                self.url_list.insert("end", url)
                added += 1
        self.url_count.configure(text=f"{len(self.custom_urls)} additional URL(s)")

        if not urls and not invalid:
            messagebox.showinfo("No links found", "Paste one or more http:// or https:// wiki page addresses first.", parent=self.root)
        if invalid:
            shown = "\n".join(f"• {url}\n  {reason}" for url, reason in invalid[:4])
            if len(invalid) > 4:
                shown += f"\n…and {len(invalid) - 4} more rejected address(es)."
            messagebox.showwarning(
                "Some links were not added",
                f"Added {added} supported URL(s). These addresses were skipped:\n\n{shown}",
                parent=self.root,
            )
        elif added:
            self.status.set(f"Added {added} URL(s).")

    def remove_selected(self) -> None:
        indices = list(self.url_list.curselection())
        for index in reversed(indices):
            self.url_list.delete(index)
            del self.custom_urls[index]
        self.url_count.configure(text=f"{len(self.custom_urls)} additional URL(s)")

    def clear_urls(self) -> None:
        self.custom_urls.clear()
        self.url_list.delete(0, "end")
        self.url_count.configure(text="0 additional URLs")

    def choose_output(self) -> None:
        initial = Path(self.output_dir.get()).expanduser()
        if not initial.is_dir():
            initial = ROOT
        selected = filedialog.askdirectory(initialdir=str(initial), title="Choose export folder", parent=self.root)
        if selected:
            self.output_dir.set(selected)

    def _make_manifest(self) -> Path:
        lines: list[str] = ["# Temporary target list generated by the SWSE Downloader GUI"]
        if self.include_defaults.get():
            if not scraper.DEFAULT_TARGETS.is_file():
                raise FileNotFoundError(f"Built-in target list not found: {scraper.DEFAULT_TARGETS}")
            lines.extend(scraper.DEFAULT_TARGETS.read_text(encoding="utf-8").splitlines())
        for url in self.custom_urls:
            prefix = "@discover " if self.discover_custom.get() else ""
            lines.append(prefix + url)
        self.temp_dir = tempfile.TemporaryDirectory(prefix="swse-scraper-")
        manifest_path = Path(self.temp_dir.name) / "targets.txt"
        manifest_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return manifest_path

    def start_download(self) -> None:
        if self.process is not None:
            return
        if self.url_entry.get("1.0", "end-1c").strip():
            self.add_urls()
        if not self.include_defaults.get() and not self.custom_urls:
            messagebox.showwarning("No pages selected", "Select the built-in page set or add at least one URL.", parent=self.root)
            return
        try:
            delay = float(self.delay.get())
            workers = int(self.workers.get())
            if delay < 0 or not 1 <= workers <= 50:
                raise ValueError("Workers must be 1–50 and delay must be non-negative.")
            output_text = self.output_dir.get().strip()
            if not output_text:
                raise ValueError("Choose an export folder.")
            output_path = Path(output_text).expanduser()
            output_path.mkdir(parents=True, exist_ok=True)
            manifest_path = self._make_manifest()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Check the export settings", f"Could not start the download:\n{exc}", parent=self.root)
            self._cleanup_temp()
            return

        python_executable = Path(sys.executable)
        if os.name == "nt" and python_executable.name.casefold() == "pythonw.exe":
            console_python = python_executable.with_name("python.exe")
            if console_python.is_file():
                python_executable = console_python
        command = [
            str(python_executable),
            "-u",
            str(ROOT / "scripts" / "scrape_swse_wiki.py"),
            "--targets",
            str(manifest_path),
            "--output",
            str(output_path.resolve()),
            "--workers",
            str(workers),
            "--delay",
            str(delay),
        ]
        if self.refresh.get():
            command.append("--refresh")

        self.stop_requested = False
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.progress.start(12)
        self.status.set("Starting download…")
        self._append_log("Starting the downloader. This may take a while for a large page set.")
        self.worker = threading.Thread(target=self._run_process, args=(command,), daemon=True)
        self.worker.start()

    def _run_process(self, command: list[str]) -> None:
        try:
            environment = os.environ.copy()
            environment["PYTHONUNBUFFERED"] = "1"
            process = subprocess.Popen(
                command,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=environment,
                creationflags=(getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0),
            )
            self.process = process
            if self.stop_requested:
                process.terminate()
            assert process.stdout is not None
            for line in process.stdout:
                self.events.put(("line", line.rstrip("\r\n")))
            return_code = process.wait()
            self.events.put(("done", return_code))
        except Exception as exc:
            self.events.put(("worker-error", str(exc)))

    def stop_download(self) -> None:
        self.stop_requested = True
        process = self.process
        if process is not None and process.poll() is None:
            self.status.set("Stopping the downloader…")
            self._append_log("Stop requested.")
            try:
                process.terminate()
            except OSError as exc:
                self._append_log(f"Could not stop process cleanly: {exc}")
        else:
            self.status.set("Stopping after startup…")

    def _poll_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "line":
                    line = payload
                    self._append_log(line)
                    match = CURRENT_PAGE.match(line)
                    if match:
                        self.status.set(f"Completed page {match.group(1)} of {match.group(2)} in current batch")
                elif event == "done":
                    self._finish(int(payload))
                elif event == "worker-error":
                    self._append_log(f"Downloader could not start: {payload}")
                    self._finish(-999)
        except queue.Empty:
            pass
        try:
            self.root.after(120, self._poll_events)
        except TclError:
            pass

    def _finish(self, return_code: int) -> None:
        self.process = None
        self.progress.stop()
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self._cleanup_temp()

        output_path = Path(self.output_dir.get()).expanduser()
        if self.stop_requested:
            self.status.set("Download stopped.")
            self._append_log("Download stopped. Any pages saved before stopping remain in the export folder.")
            return
        if return_code == 0:
            self.status.set("Download complete.")
            self._append_log("Download complete. Open the export folder to review the Markdown and index.")
            messagebox.showinfo("Download complete", f"The export is ready here:\n{output_path}", parent=self.root)
        elif return_code == 1:
            self.status.set("Finished with some page errors.")
            self._append_log(f"Some pages could not be downloaded. Review: {output_path / 'report.json'}")
            messagebox.showwarning(
                "Finished with page errors",
                f"The export was created, but one or more pages failed.\n\nReview report.json in:\n{output_path}",
                parent=self.root,
            )
        else:
            self.status.set("Downloader exited with an error.")
            messagebox.showerror("Downloader error", "See the Activity log for details.", parent=self.root)

    def _append_log(self, text: str) -> None:
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text + "\n")
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > 800:
            self.log_text.delete("1.0", f"{line_count - 800}.0")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _cleanup_temp(self) -> None:
        if self.temp_dir is not None:
            try:
                self.temp_dir.cleanup()
            except OSError:
                pass
            self.temp_dir = None

    def open_output(self) -> None:
        path = Path(self.output_dir.get()).expanduser()
        if not path.exists():
            messagebox.showinfo("Export folder not created yet", "Run a download first, or choose an existing folder.", parent=self.root)
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except (OSError, TclError) as exc:
            messagebox.showerror("Could not open folder", str(exc), parent=self.root)

    def close_window(self) -> None:
        process = self.process
        worker_running = self.worker is not None and self.worker.is_alive()
        if worker_running or (process is not None and process.poll() is None):
            should_close = messagebox.askyesno(
                "Download in progress",
                "Stop the active download and close the window?",
                parent=self.root,
            )
            if not should_close:
                return
            self.stop_requested = True
            if process is not None and process.poll() is None:
                try:
                    process.terminate()
                except OSError:
                    pass
        self._cleanup_temp()
        self.root.destroy()


def main() -> int:
    if tk is None:
        print(
            "Tkinter is missing from this Python installation. On Windows, reinstall Python with Tcl/Tk support; "
            "on Linux, install the python3-tk package.",
            file=sys.stderr,
        )
        return 2
    try:
        root = tk.Tk()
        ScraperWindow(root)
        root.mainloop()
    except (TclError, RuntimeError) as exc:
        print(f"Could not open the SWSE Downloader window: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
