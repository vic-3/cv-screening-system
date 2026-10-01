# AI-Powered CV Screening and Ranking System

A Python desktop app (Tkinter) that reads a job description, scans a folder of
CVs, matches each CV against the requirements using **regular expressions** and
the **Gemini API**, then classifies, organizes and **ranks** the candidates.

## Project structure

Each team member owns one file. Work only in your file so we don't get merge
conflicts; talk to the team before changing `models.py` or `config.py`.

| File | Owner | Responsibility |
|------|-------|----------------|
| `cv_screener/gui.py` | **Victory Okeke** | Tkinter GUI & user interaction |
| `cv_screener/job_description.py` | **Toluwalase Ayeoyenikan** | Parse job descriptions into requirements |
| `cv_screener/document_reader.py` | **Daniel Orisakwe** | Read text from TXT / PDF / DOCX CVs |
| `cv_screener/matcher.py` | **Aiwansoba Eric** | Regex keyword & requirement matching |
| `cv_screener/ai_analysis.py` | **Muhammad Bala** | Gemini AI analysis |
| `cv_screener/ranker.py` | **Muhammad Bala** | Score & rank candidates |
| `cv_screener/organizer.py` | **Abdulshafiu Siyaka** | Classify & move CVs into folders |
| `cv_screener/screener.py` | **Ojeaga Jeffrey** | Wire the pipeline together + error handling |
| `cv_screener/models.py` | shared | Data classes everyone passes around |
| `cv_screener/config.py` | shared | Settings & API key |
| `main.py` | Jeffrey | App entry point (`python main.py`) |

All files are currently empty except for a description at the top explaining
what each one will do. Fill in your own part.

## How the pieces connect

```
GUI (Victory)
  -> screener.screen_folder()              (Jeffrey)
       -> document_reader.load_cv_folder()  (Daniel)   reads the CVs
       -> matcher.match()                   (Eric)     regex matching
       -> ai_analysis.analyse()             (Muhammad) Gemini scoring
       -> ranker.rank()                     (Muhammad) final score + sort
       -> organizer.organize()              (Abdulshafiu) sort into folders
  <- ranked list of results shown in the GUI
```

The glue between everyone is `models.py` (JobDescription, CVDocument,
MatchResult). As long as each function takes and returns those objects, the
parts will plug together at integration.

## Setup

```bash
# 1. (optional but recommended) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. install the external modules
pip install -r requirements.txt

# 3. add your Gemini key (for the AI part)
cp .env.example .env             # then edit .env and paste your key

# 4. run the app
python main.py
```

Get a free Gemini key at https://aistudio.google.com/app/apikey.
The app should still run without a key (regex-only mode).
