"""Pipeline orchestration - ties every module together.

OWNER: Ojeaga Jeffrey  (System Integration, Exception Handling & Testing)

The "spine" of the app. The GUI calls screen_folder(), which runs the full
pipeline for every CV in a folder:

    read the CV text      (document_reader - Daniel)
    parse the job         (job_description - Toluwalase)
    regex match           (matcher         - Eric)
    AI analyse (optional) (ai_analysis     - Muhammad)
    score + rank          (ranker          - Muhammad)

and returns a list of MatchResult sorted best-first for the GUI to display.
Optionally it can also sort the CV files into folders (organizer - Abdulshafiu).

Every CV is processed inside a try/except so one unreadable file never crashes
the whole run - it just comes back with a 0 score and an error note.
"""

from __future__ import annotations

import os
import sys
from typing import List

# Make sure the project root is importable so `cv_screener.*` always resolves,
# even when the app is launched as `python cv_screener/gui.py`.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cv_screener import ai_analysis, config, job_description, matcher, ranker
from cv_screener.models import CVDocument, MatchResult

# document_reader resolves to the root reader (the package copy re-exports it).
import document_reader


def _cv_files(cv_folder: str) -> List[str]:
    """Return the full paths of the supported CV files in a folder."""
    files = []
    for name in sorted(os.listdir(cv_folder)):
        path = os.path.join(cv_folder, name)
        ext = os.path.splitext(name)[1].lower()
        if os.path.isfile(path) and ext in config.SUPPORTED_EXTENSIONS:
            files.append(path)
    return files


def screen_one(path: str, job) -> MatchResult:
    """Run the pipeline for a single CV file and return its MatchResult."""
    result = MatchResult(file_path=path)
    try:
        text = document_reader.clean_text(document_reader.read_document(path))
    except Exception as error:
        result.summary = f"Could not read file: {error}"
        return result

    cv = CVDocument(file_path=path, text=text)

    # Regex matching fills matched / missing / years_experience on the result.
    matcher.match_cv(cv, job, result=result)

    # AI analysis is optional - safely skipped when there is no API key.
    ai_analysis.analyse(text, job, result=result)
    return result


def screen_folder(job_text: str, cv_folder: str) -> List[MatchResult]:
    """Screen every CV in cv_folder against the job description text.

    Args:
        job_text:  the job description (raw text typed/loaded in the GUI).
        cv_folder: path to the folder containing the CV files.

    Returns:
        A list of MatchResult, ranked best-first.
    """
    if not os.path.isdir(cv_folder):
        raise NotADirectoryError(f"Not a folder: {cv_folder}")

    job = job_description.extract_requirements(job_text)

    results = [screen_one(path, job) for path in _cv_files(cv_folder)]
    return ranker.rank(results)
