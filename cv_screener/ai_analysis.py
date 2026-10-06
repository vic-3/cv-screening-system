"""Gemini AI analysis.

OWNER: Muhammad Bala  (Gemini AI Integration & Ranking)  -- part 1 of 2

Asks the Gemini model to judge how well a CV fits the job, returning a score
(0-100) and a short summary, and writes them onto the MatchResult.

Must still work when AI is NOT available (no API key, or the google-generativeai
package isn't installed): in that case it simply skips, leaves ai_score = None,
and the ranker falls back to the regex-only score.
"""

from __future__ import annotations

import json
import re
from typing import Optional, Tuple

# Shared settings (Gemini key / model, ai_enabled()).
try:
    from cv_screener import config
except ImportError:
    import config

# The Gemini SDK is optional - guard it so the app runs without it installed.
try:
    import google.generativeai as genai
except ImportError:
    genai = None


def _get_model():
    """Return a configured Gemini model, or None if AI isn't available."""
    if genai is None or not config.ai_enabled():
        return None
    try:
        genai.configure(api_key=config.GEMINI_API_KEY)
        return genai.GenerativeModel(config.GEMINI_MODEL)
    except Exception:
        return None


def _build_prompt(cv_text: str, job) -> str:
    """Build the instruction we send to Gemini."""
    skills = ", ".join(getattr(job, "skills", []) or []) or "not specified"
    education = ", ".join(getattr(job, "education", []) or []) or "not specified"
    years = getattr(job, "years_experience", 0)
    title = getattr(job, "title", "") or "the role"

    # Keep the CV text to a sane size for the request.
    cv_excerpt = cv_text[:6000]

    return (
        "You are a recruitment assistant screening a CV against a job.\n"
        f"Job title: {title}\n"
        f"Required skills: {skills}\n"
        f"Minimum years of experience: {years}\n"
        f"Required education: {education}\n\n"
        "CV text:\n"
        f"{cv_excerpt}\n\n"
        "Rate how well this candidate fits the job from 0 to 100 and give a "
        "one-sentence reason. Reply with ONLY JSON in this exact form:\n"
        '{"score": <number 0-100>, "summary": "<one sentence>"}'
    )


def _parse_response(text: str) -> dict:
    """Pull the {score, summary} JSON out of Gemini's reply."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in AI response.")
    return json.loads(match.group(0))


def analyse(cv_text: str, job, result=None) -> Tuple[Optional[float], str]:
    """Analyse one CV. Returns (ai_score, summary) and writes them onto result.

    ai_score is None when AI is unavailable or the call fails.
    """
    model = _get_model()

    if model is None:
        summary = "AI analysis skipped (no Gemini API key)."
        if result is not None:
            result.ai_score = None
            if not result.summary:
                result.summary = summary
        return None, summary

    try:
        response = model.generate_content(_build_prompt(cv_text, job))
        data = _parse_response(response.text)
        score = max(0.0, min(100.0, float(data.get("score", 0))))
        summary = str(data.get("summary", "")).strip()
    except Exception as error:
        score, summary = None, f"AI analysis failed: {error}"

    if result is not None:
        result.ai_score = score
        if summary:
            result.summary = summary
    return score, summary
