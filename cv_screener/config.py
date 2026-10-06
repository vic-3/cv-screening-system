"""Application configuration and shared constants.

OWNER: shared.

Everything that might need tweaking lives here in one place: which file types
count as CVs, the score needed to be considered a "match", the output folder
names, and the Gemini API key / model (loaded from a .env file).

Get a free Gemini key at https://aistudio.google.com/app/apikey and put it in a
.env file next to main.py:

    GEMINI_API_KEY=your-key-here

The app still runs without a key - the AI step is simply skipped (regex-only
mode). Use ai_enabled() to check.
"""

from __future__ import annotations

import os

# Load variables from a .env file if python-dotenv is installed. Guarded so the
# app still imports cleanly when the package (or the .env file) is missing.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


# --------------------------------------------------------------------------
# Document handling
# --------------------------------------------------------------------------
# File types the document reader knows how to open. Keep lower-case, with dots.
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


# --------------------------------------------------------------------------
# Scoring & classification
# --------------------------------------------------------------------------
# A CV scoring at or above this (0-100) is treated as a MATCH. Matches the
# default already used in organizer.py (CVClassifier threshold).
MATCH_THRESHOLD = 60.0


# --------------------------------------------------------------------------
# Output folders  (used by organizer.py)
# --------------------------------------------------------------------------
OUTPUT_DIR = "Screening_Output"      # top-level folder for results
MATCHING_DIR_NAME = "Matching"       # sub-folder for CVs that passed
NON_MATCHING_DIR_NAME = "Non_Matching"  # sub-folder for CVs that didn't


# --------------------------------------------------------------------------
# Gemini AI  (used by ai_analysis.py)
# --------------------------------------------------------------------------
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()


def ai_enabled() -> bool:
    """True if a Gemini key is configured, so the AI step can run."""
    return bool(GEMINI_API_KEY)
