"""Tkinter graphical user interface.

OWNER: Victory Okeke  (GUI & User Interaction)

The desktop window: a job-description text box (+ "Load from file"), a CV folder
picker, a "Start Screening" button, and a results table showing ranked
candidates with their scores. Calls screener.screen_folder() to do the work.

Integration contract (what this GUI expects from the team):
    screener.screen_folder(job_text: str, cv_folder: str) -> list[result]
where each result has (read defensively, so exact names can still change):
    .name            candidate name or CV file name
    .score           final score 0-100 (also accepts .final_score)
    .matched_skills  list[str]  (optional)
    .missing_skills  list[str]  (optional)
    .summary         str        (optional)

Until teammates finish screener.py / models.py, the GUI falls back to a small
demo so you can build and test the window on your own.

Run it on its own with:   python main.py
"""

import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# Make sure the project root is importable so `cv_screener.*` resolves, whether
# the app is launched as `python main.py` or `python cv_screener/gui.py`.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Import the real pipeline. If it (or one of its dependencies) can't load yet,
# the GUI falls back to demo mode instead of crashing.
try:
    from cv_screener import screener
except Exception:  # noqa: BLE001 - we genuinely want to catch anything here
    screener = None


class CVScreenerApp:
    """The main application window."""

    def __init__(self, root):
        self.root = root
        self.root.title("AI-Powered CV Screening and Ranking System")
        self.root.geometry("820x640")
        self.root.minsize(680, 540)

        # Folder the user picked, and a queue to pass results back from the
        # background screening thread to the GUI thread safely.
        self.cv_folder = tk.StringVar()
        self.result_queue = queue.Queue()

        self._build_widgets()

    # ------------------------------------------------------------------ UI --
    def _build_widgets(self):
        padding = {"padx": 12, "pady": 6}

        # Title
        title = ttk.Label(
            self.root,
            text="CV Screening and Ranking",
            font=("Helvetica", 18, "bold"),
        )
        title.pack(anchor="w", **padding)

        # --- Job description -------------------------------------------------
        jd_frame = ttk.LabelFrame(self.root, text="1. Job description")
        jd_frame.pack(fill="x", **padding)

        self.job_text = tk.Text(jd_frame, height=8, wrap="word")
        self.job_text.pack(fill="x", padx=8, pady=(8, 4))
        self.job_text.insert(
            "1.0",
            "Paste the job description here, or click 'Load from file'...",
        )

        ttk.Button(
            jd_frame, text="Load from file", command=self._load_job_file
        ).pack(anchor="e", padx=8, pady=(0, 8))

        # --- CV folder -------------------------------------------------------
        folder_frame = ttk.LabelFrame(self.root, text="2. Folder of CVs")
        folder_frame.pack(fill="x", **padding)

        row = ttk.Frame(folder_frame)
        row.pack(fill="x", padx=8, pady=8)
        ttk.Entry(row, textvariable=self.cv_folder).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(row, text="Browse...", command=self._pick_folder).pack(
            side="left", padx=(8, 0)
        )

        # --- Start button ----------------------------------------------------
        self.start_btn = ttk.Button(
            self.root, text="Start Screening", command=self._start_screening
        )
        self.start_btn.pack(**padding)

        # --- Results table ---------------------------------------------------
        results_frame = ttk.LabelFrame(self.root, text="3. Ranked candidates")
        results_frame.pack(fill="both", expand=True, **padding)

        columns = ("rank", "name", "score", "skills")
        self.tree = ttk.Treeview(
            results_frame, columns=columns, show="headings", height=10
        )
        self.tree.heading("rank", text="#")
        self.tree.heading("name", text="Candidate")
        self.tree.heading("score", text="Score")
        self.tree.heading("skills", text="Matched skills")
        self.tree.column("rank", width=40, anchor="center")
        self.tree.column("name", width=220)
        self.tree.column("score", width=70, anchor="center")
        self.tree.column("skills", width=380)

        scrollbar = ttk.Scrollbar(
            results_frame, orient="vertical", command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        scrollbar.pack(side="right", fill="y", pady=8)

        # Double-click a row to see the full detail of that candidate.
        self.tree.bind("<Double-1>", self._show_detail)
        self._results = []  # keep the raw result objects for the detail view

        # --- Status bar ------------------------------------------------------
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(
            self.root, textvariable=self.status, relief="sunken", anchor="w"
        ).pack(fill="x", side="bottom")

    # ------------------------------------------------------------- actions --
    def _load_job_file(self):
        """Let the user load the job description from a .txt file."""
        path = filedialog.askopenfilename(
            title="Choose a job-description file",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            messagebox.showerror("Could not read file", str(exc))
            return
        self.job_text.delete("1.0", "end")
        self.job_text.insert("1.0", text)

    def _pick_folder(self):
        """Let the user choose the folder that holds the CVs."""
        folder = filedialog.askdirectory(title="Choose the folder of CVs")
        if folder:
            self.cv_folder.set(folder)

    def _start_screening(self):
        """Validate input, then run screening in the background."""
        job_text = self.job_text.get("1.0", "end").strip()
        folder = self.cv_folder.get().strip()

        if not job_text:
            messagebox.showwarning(
                "Missing job description", "Please enter a job description first."
            )
            return
        if not folder or not Path(folder).is_dir():
            messagebox.showwarning(
                "Missing CV folder", "Please choose a valid folder of CVs."
            )
            return

        # Disable the button and clear old results while we work.
        self.start_btn.config(state="disabled")
        self.tree.delete(*self.tree.get_children())
        self._results = []
        self.status.set("Screening... please wait.")

        # Run the slow work off the GUI thread so the window stays responsive.
        worker = threading.Thread(
            target=self._run_pipeline, args=(job_text, folder), daemon=True
        )
        worker.start()
        self.root.after(100, self._poll_results)

    # ---------------------------------------------------------- background --
    def _run_pipeline(self, job_text, folder):
        """Runs in a background thread. Puts (results, error) on the queue."""
        try:
            if screener is not None and hasattr(screener, "screen_folder"):
                results = screener.screen_folder(job_text, folder)
            else:
                results = self._demo_results(folder)
            self.result_queue.put((results, None))
        except NotImplementedError:
            # Teammate's part exists but isn't finished - show the demo instead.
            self.result_queue.put((self._demo_results(folder), None))
        except Exception as exc:  # noqa: BLE001 - report any pipeline error
            self.result_queue.put((None, exc))

    def _poll_results(self):
        """Runs on the GUI thread; checks if the worker has finished."""
        try:
            results, error = self.result_queue.get_nowait()
        except queue.Empty:
            self.root.after(100, self._poll_results)  # not done yet, keep waiting
            return

        self.start_btn.config(state="normal")
        if error is not None:
            self.status.set("Screening failed.")
            messagebox.showerror("Screening failed", str(error))
            return

        self._display_results(results or [])

    # ------------------------------------------------------------- display --
    def _display_results(self, results):
        self._results = list(results)
        for position, result in enumerate(self._results, start=1):
            name = getattr(result, "name", None) or getattr(
                result, "filename", "Unknown"
            )
            score = getattr(result, "score", getattr(result, "final_score", 0))
            matched = getattr(result, "matched_skills", []) or []
            skills = ", ".join(matched) if matched else "-"
            self.tree.insert(
                "",
                "end",
                values=(position, name, f"{round(float(score))}", skills),
            )
        self.status.set(f"Done. {len(self._results)} candidate(s) ranked.")
        if not self._results:
            messagebox.showinfo("No results", "No CVs were found in that folder.")

    def _show_detail(self, _event):
        """Show the full detail of the double-clicked candidate."""
        selected = self.tree.selection()
        if not selected:
            return
        index = self.tree.index(selected[0])
        if index >= len(self._results):
            return
        result = self._results[index]

        name = getattr(result, "name", None) or getattr(
            result, "filename", "Unknown"
        )
        score = getattr(result, "score", getattr(result, "final_score", 0))
        matched = getattr(result, "matched_skills", []) or []
        missing = getattr(result, "missing_skills", []) or []
        summary = getattr(result, "summary", "") or ""

        lines = [f"Candidate: {name}", f"Score: {round(float(score))}/100", ""]
        if matched:
            lines.append("Matched skills: " + ", ".join(matched))
        if missing:
            lines.append("Missing skills: " + ", ".join(missing))
        if summary:
            lines += ["", summary]
        messagebox.showinfo(f"Candidate - {name}", "\n".join(lines))

    # ---------------------------------------------------------------- demo --
    @staticmethod
    def _demo_results(folder):
        """Fake results so the GUI is testable before the pipeline is ready.

        Lists the CV-like files in the folder and gives each a placeholder
        score. Replaced automatically once screener.screen_folder() works.
        """
        extensions = {".txt", ".pdf", ".docx"}
        files = [
            p
            for p in sorted(Path(folder).iterdir())
            if p.is_file() and p.suffix.lower() in extensions
        ]

        class _DemoResult:
            def __init__(self, name, score):
                self.name = name
                self.score = score
                self.matched_skills = ["(demo)"]
                self.missing_skills = []
                self.summary = "Demo result - real screening not wired up yet."

        # Simple descending placeholder scores so the table looks ranked.
        results = []
        for position, path in enumerate(files):
            score = max(10, 95 - position * 7)
            results.append(_DemoResult(path.name, score))
        return results


def main():
    """Create the window and start the app. Called by main.py."""
    root = tk.Tk()
    CVScreenerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
