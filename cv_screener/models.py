"""Shared data classes used across all modules (the integration "contract").

OWNER: shared - agree as a team before changing anything here.

Will define the objects every module passes around:
  - JobDescription : parsed job description (skills, experience, education).
  - CVDocument     : one CV read from disk (path, name, extracted text).
  - MatchResult    : the screening outcome for one CV (matches, scores, ranking).
"""
