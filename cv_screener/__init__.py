"""AI-Powered CV Screening and Ranking System.

A Tkinter desktop application that reads a job description, scans a folder of
CVs, matches each CV against the requirements using regular expressions and the
Gemini API, then classifies, organizes and ranks the candidates.

Package layout (one module per team member):
    models.py           Shared data classes used by everyone (the "contract").
    config.py           App settings and API-key loading.
    document_reader.py  Daniel     - read text from TXT / PDF / DOCX files.
    job_description.py  Toluwalase - parse a job description into requirements.
    matcher.py          Eric       - regex keyword / requirement matching.
    ai_analysis.py      Muhammad   - Gemini-assisted analysis.
    ranker.py           Muhammad   - score and rank candidates.
    organizer.py        Abdulshafiu- classify and move CVs into folders.
    screener.py         (shared)   - orchestrates the whole pipeline.
    gui.py              Victory    - Tkinter user interface.
"""

__version__ = "0.1.0"
