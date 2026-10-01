"""Gemini-assisted CV analysis.

OWNER: Muhammad Bala  (Gemini AI Integration & Ranking)  -- part 1 of 2

Will send the CV text + job description to the Gemini API and get back a score
(0-100) and a short summary, writing them onto the MatchResult. Must still work
with no API key (regex-only mode) by checking config.ai_enabled() first.
"""
