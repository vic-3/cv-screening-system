"""Candidate scoring and ranking.

OWNER: Muhammad Bala  (Gemini AI Integration & Ranking)  -- part 2 of 2

Turns each MatchResult into a final score (0-100) and sorts candidates
best-first. The final score combines:
  - the regex match (how many requirements were found), and
  - the Gemini AI score when it is available.
If there is no AI score (no API key / AI module off), the final score is just
the regex score, so ranking still works in regex-only mode.
"""

from __future__ import annotations

from typing import List

# How much each part counts toward the final score when BOTH are present.
REGEX_WEIGHT = 0.5
AI_WEIGHT = 0.5


def regex_score(result) -> float:
    """Percentage of the job's requirements that were found in the CV (0-100)."""
    found = len(result.matched)
    total = found + len(result.missing)
    if total == 0:
        return 0.0
    return 100.0 * found / total


def final_score(result) -> float:
    """Combine the regex score with the AI score (if any) into one 0-100 number."""
    regex = regex_score(result)

    ai = getattr(result, "ai_score", None)
    if ai is None:
        return round(regex, 1)

    combined = REGEX_WEIGHT * regex + AI_WEIGHT * float(ai)
    return round(combined, 1)


def rank(results: List) -> List:
    """Score every result and return them sorted best-first."""
    for result in results:
        result.regex_score = round(regex_score(result), 1)
        result.score = final_score(result)
    return sorted(results, key=lambda r: r.score, reverse=True)

#Ranking contribution by Muhammad:
scores are kept within the expected 0-100 range.
