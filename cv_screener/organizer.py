
"""
cv_organizer.py
---------------
File Organization & Classification module
AI-Powered CV Screening and Ranking System

Author: Abdulshafiu Siyaka

Responsibilities:
    1. Classify CVs into MATCHING and NON-MATCHING groups.
    2. Automatically organize CVs into separate folders.

Integration (how teammates' modules plug in):
    Each processed CV is described by a MatchResult:
        MatchResult(file_path, score, matched, missing, summary)
    - score   : float 0-100 (produced by the regex matching + Gemini ranking modules)
    - matched : list of requirements found in the CV
    - missing : list of requirements not found
    - summary : optional AI-generated comment

Usage:
    classifier = CVClassifier(threshold=60)
    organizer  = CVFileOrganizer(output_dir="Screening_Output", mode="copy")
    report     = organizer.organize(results, classifier)
    print(report.summary_text())
"""

from __future__ import annotations

import csv
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Tuple


# --------------------------------------------------------------------------
# Custom exception
# --------------------------------------------------------------------------
class OrganizationError(Exception):
    """Raised when the output folders cannot be prepared or used."""


# --------------------------------------------------------------------------
# Data classes
# --------------------------------------------------------------------------
# MatchResult is the shared contract - defined once in models.py so the matcher,
# ranker and GUI all agree on it. (Same fields as before: file_path, score,
# matched, missing, summary, plus a .file_name helper.)
from cv_screener.models import MatchResult


@dataclass
class OrganizationReport:
    """Outcome of an organization run (for the GUI / testing module)."""
    matching: List[MatchResult] = field(default_factory=list)   # ranked
    non_matching: List[MatchResult] = field(default_factory=list)
    failed: List[Tuple[str, str]] = field(default_factory=list)  # (file, reason)
    matching_dir: str = ""
    non_matching_dir: str = ""
    report_file: str = ""

    def summary_text(self) -> str:
        lines = [
            f"Matching CVs     : {len(self.matching)}",
            f"Non-matching CVs : {len(self.non_matching)}",
            f"Failed to move   : {len(self.failed)}",
            "",
            "Ranked candidates:",
        ]
        for rank, r in enumerate(self.matching, start=1):
            lines.append(f"  {rank:>2}. {r.file_name}  ({r.score:.1f}%)")
        if self.failed:
            lines.append("")
            lines.append("Errors:")
            for name, reason in self.failed:
                lines.append(f"  - {name}: {reason}")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# Classification
# --------------------------------------------------------------------------
class CVClassifier:
    """Decides whether a CV matches the job requirements."""

    def __init__(self, threshold: float = 60.0, require_all: bool = False):
        """
        threshold   : minimum score (0-100) for a CV to be 'matching'.
        require_all : if True, a CV must also have no missing requirements.
        """
        if not 0 <= threshold <= 100:
            raise ValueError("threshold must be between 0 and 100")
        self.threshold = threshold
        self.require_all = require_all

    def is_match(self, result: MatchResult) -> bool:
        if result.score < self.threshold:
            return False
        if self.require_all and result.missing:
            return False
        return True

    def classify(self, results: List[MatchResult]
                 ) -> Tuple[List[MatchResult], List[MatchResult]]:
        """Return (matching_ranked_best_first, non_matching_best_first)."""
        matching, non_matching = [], []
        for r in results:
            (matching if self.is_match(r) else non_matching).append(r)
        matching.sort(key=lambda r: r.score, reverse=True)
        non_matching.sort(key=lambda r: r.score, reverse=True)
        return matching, non_matching


# --------------------------------------------------------------------------
# File organization
# --------------------------------------------------------------------------
class CVFileOrganizer:
    """Copies or moves CVs into Matching / Non_Matching folders."""

    MATCHING_FOLDER = "Matching_CVs"
    NON_MATCHING_FOLDER = "Non_Matching_CVs"

    def __init__(self, output_dir: str, mode: str = "copy"):
        """
        output_dir : folder where the two result folders will be created.
        mode       : 'copy' (keeps originals, safer) or 'move'.
        """
        if mode not in ("copy", "move"):
            raise ValueError("mode must be 'copy' or 'move'")
        self.output_dir = output_dir
        self.mode = mode
        self.matching_dir = os.path.join(output_dir, self.MATCHING_FOLDER)
        self.non_matching_dir = os.path.join(output_dir, self.NON_MATCHING_FOLDER)

    # ---- public API ------------------------------------------------------
    def organize(self, results: List[MatchResult],
                 classifier: CVClassifier) -> OrganizationReport:
        self._prepare_folders()
        report = OrganizationReport(
            matching_dir=self.matching_dir,
            non_matching_dir=self.non_matching_dir,
        )

        # Skip missing files first so ranks stay consecutive.
        valid = []
        for r in results:
            if os.path.isfile(r.file_path):
                valid.append(r)
            else:
                report.failed.append((r.file_name, "file not found"))
        matching, non_matching = classifier.classify(valid)

        # Matching CVs: prefix with rank so the folder lists best-first.
        for rank, r in enumerate(matching, start=1):
            if self._transfer(r, self.matching_dir, prefix=f"{rank:02d}_", report=report):
                report.matching.append(r)

        for r in non_matching:
            if self._transfer(r, self.non_matching_dir, prefix="", report=report):
                report.non_matching.append(r)

        report.report_file = self._write_csv_report(report)
        return report

    # ---- internals -------------------------------------------------------
    def _prepare_folders(self) -> None:
        try:
            os.makedirs(self.matching_dir, exist_ok=True)
            os.makedirs(self.non_matching_dir, exist_ok=True)
        except OSError as e:
            raise OrganizationError(f"Cannot create output folders: {e}") from e

    def _unique_path(self, folder: str, name: str) -> str:
        """Avoid overwriting files that share the same name."""
        base, ext = os.path.splitext(name)
        path = os.path.join(folder, name)
        counter = 1
        while os.path.exists(path):
            path = os.path.join(folder, f"{base}_{counter}{ext}")
            counter += 1
        return path

    def _transfer(self, result: MatchResult, dest_folder: str,
                  prefix: str, report: OrganizationReport) -> bool:
        src = result.file_path
        try:
            if not os.path.isfile(src):
                raise FileNotFoundError("file not found")
            dest = self._unique_path(dest_folder, prefix + result.file_name)
            if self.mode == "copy":
                shutil.copy2(src, dest)
            else:
                shutil.move(src, dest)
            return True
        except (OSError, shutil.Error) as e:
            report.failed.append((result.file_name, str(e)))
            return False

    def _write_csv_report(self, report: OrganizationReport) -> str:
        path = os.path.join(self.output_dir, "screening_report.csv")
        try:
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["Rank", "File", "Status", "Score (%)",
                            "Matched requirements", "Missing requirements", "AI summary"])
                for i, r in enumerate(report.matching, start=1):
                    w.writerow([i, r.file_name, "Matching", f"{r.score:.1f}",
                                "; ".join(r.matched), "; ".join(r.missing), r.summary])
                for r in report.non_matching:
                    w.writerow(["-", r.file_name, "Non-matching", f"{r.score:.1f}",
                                "; ".join(r.matched), "; ".join(r.missing), r.summary])
            return path
        except OSError as e:
            report.failed.append(("screening_report.csv", str(e)))
            return ""


# --------------------------------------------------------------------------
# Demo / self-test (run: python cv_organizer.py)
# --------------------------------------------------------------------------
if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        src_dir = os.path.join(tmp, "cvs")
        os.makedirs(src_dir)
        samples = {"ada.pdf": 88, "bola.docx": 45, "chidi.pdf": 72, "dayo.pdf": 30}
        results = []
        for name, score in samples.items():
            p = os.path.join(src_dir, name)
            with open(p, "w") as f:
                f.write("dummy cv")
            results.append(MatchResult(p, score, ["Python"], ["SQL"], "demo"))
        results.append(MatchResult(os.path.join(src_dir, "ghost.pdf"), 90))  # missing file

        organizer = CVFileOrganizer(os.path.join(tmp, "output"), mode="copy")
        report = organizer.organize(results, CVClassifier(threshold=60))
        print(report.summary_text())
        print("\nMatching folder:", sorted(os.listdir(report.matching_dir)))
        print("Non-matching folder:", sorted(os.listdir(report.non_matching_dir)))
