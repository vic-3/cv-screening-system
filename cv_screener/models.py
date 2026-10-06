"""Shared data classes used across all modules (the integration "contract").

OWNER: shared - agree as a team before changing anything here.

These are the three objects every module passes around:
  - JobDescription : parsed job description (skills, experience, education).
  - CVDocument     : one CV read from disk (path, name, extracted text).
  - MatchResult    : the screening outcome for one CV (matches, scores, ranking).

Why this file matters
---------------------
Different teammates named the same data differently while working in parallel:

    matched skills -> organizer.py uses `matched`
                      matcher.py   uses `found_skills`
                      gui.py       reads `matched_skills`

Rather than force everyone to rename their code, `MatchResult` below stores ONE
canonical set of fields and exposes the other names as aliases (properties).
So all of these do the same thing and stay in sync:

    result.matched = ["Python"]        # organizer's name  (the real field)
    result.found_skills = ["Python"]   # matcher's name    (alias -> matched)
    result.matched_skills              # gui's name        (alias -> matched)

That means teammates can keep their existing code, and later switch their local
`class` definitions to `from cv_screener.models import JobDescription, MatchResult`
without changing anything else.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, List, Optional


# --------------------------------------------------------------------------
# JobDescription  (mirrors the one in job_description.py - Toluwalase)
# --------------------------------------------------------------------------
@dataclass
class JobDescription:
    """What the job asks for, parsed from the description text."""

    title: str = ""
    skills: List[str] = field(default_factory=list)          # must-have skills
    preferred_skills: List[str] = field(default_factory=list)  # nice-to-have
    years_experience: int = 0                                # minimum years
    education: List[str] = field(default_factory=list)       # required degrees
    raw_text: str = ""                                       # original text

    # matcher.py also looks for `.experience`; keep it as an alias so its
    # adapter finds the number no matter which name is used.
    @property
    def experience(self) -> int:
        return self.years_experience


# --------------------------------------------------------------------------
# CVDocument  (consumed by matcher.py, which needs a `.text` attribute)
# --------------------------------------------------------------------------
@dataclass
class CVDocument:
    """One candidate's CV: where it came from and the text pulled out of it."""

    file_path: str
    text: str = ""

    @property
    def file_name(self) -> str:
        """Just the file name, e.g. 'jane_doe.pdf'."""
        return os.path.basename(self.file_path)

    @property
    def name(self) -> str:
        """Friendly alias some modules use."""
        return self.file_name


# --------------------------------------------------------------------------
# MatchResult  (superset of the one in organizer.py - Abdulshafiu)
# --------------------------------------------------------------------------
@dataclass
class MatchResult:
    """The screening outcome for a single CV.

    Canonical fields (the real storage):
        file_path, score, matched, missing, summary
    Everything else below is an alias so each teammate's code keeps working.
    """

    file_path: str
    score: float = 0.0
    matched: List[str] = field(default_factory=list)   # requirements found
    missing: List[str] = field(default_factory=list)   # requirements not found
    summary: str = ""                                  # AI comment (optional)

    # Optional extras the matcher / AI / ranker may fill in along the way.
    regex_score: Optional[float] = None
    ai_score: Optional[float] = None
    years_experience: Optional[float] = None
    regex_results: List[Any] = field(default_factory=list)

    # ---- display helpers --------------------------------------------------
    @property
    def file_name(self) -> str:
        return os.path.basename(self.file_path)

    @property
    def name(self) -> str:            # gui.py reads `.name`
        return self.file_name

    @property
    def final_score(self) -> float:  # gui.py falls back to `.final_score`
        return self.score

    @final_score.setter
    def final_score(self, value) -> None:
        self.score = float(value)

    # ---- matched-skills aliases (matcher: found_skills, gui: matched_skills)
    @property
    def matched_skills(self) -> List[str]:
        return self.matched

    @matched_skills.setter
    def matched_skills(self, value) -> None:
        self.matched = list(value)

    @property
    def found_skills(self) -> List[str]:
        return self.matched

    @found_skills.setter
    def found_skills(self, value) -> None:
        self.matched = list(value)

    # ---- missing-skills alias (matcher & gui both use missing_skills) -----
    @property
    def missing_skills(self) -> List[str]:
        return self.missing

    @missing_skills.setter
    def missing_skills(self, value) -> None:
        self.missing = list(value)
