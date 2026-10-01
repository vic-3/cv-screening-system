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

## Team workflow (step by step, for beginners)

This is the exact routine every team member follows. Think of it like this: the
code lives online on GitHub (the "original"), you make your **own copy** on your
computer, you work in **your own lane** (a branch named after you), then you ask
for your changes to be added back to the original. Nobody edits the original
directly — that keeps everyone's work from crashing into each other.

> You only do **Steps 1–2 (install + clone)** once. After that you start at
> **Step 3** every time you sit down to work.

### Step 1 — Install the tools you need (one time only)

Before you can do anything, your computer needs two programs: **Git** (the tool
that shares the code) and **Python** (the language the project is written in).

- **Git** — download from https://git-scm.com/downloads and install it. On
  Windows, choose "Git Bash" when asked; just click Next on the defaults.
- **Python** — download from https://www.python.org/downloads and install it.
  On Windows, **tick the box that says "Add Python to PATH"** on the first screen.

> You do this only once per computer. If a teammate already helped you set these
> up, skip to the next step.

### Step 2 — Open your terminal

- **Windows:** press the Start button, type `cmd` (or `Git Bash` if you
  installed Git for Windows), and open it.
- **Mac:** press `Cmd + Space`, type `Terminal`, press Enter.
- **VS Code (any computer):** open the menu `Terminal -> New Terminal`.

The terminal is just a place where you type commands instead of clicking buttons.
You type a line, press **Enter**, and wait for it to finish before typing the next.

First, check that Git and Python actually installed. Type each line and press
Enter — you should see a version number, not an error:

```bash
git --version         # e.g. "git version 2.43.0"
python --version      # e.g. "Python 3.12.0"  (try "python3 --version" on Mac)
```

If you get an error like "command not found", the program isn't installed yet —
go back to Step 1.

Then tell Git who you are (do this once per computer):

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

### Step 3 — Clone the repo (copy it to your computer) — do this ONCE

Go to the folder where you keep your projects, then download the code:

```bash
# go somewhere you want the project to live, e.g. your Desktop
cd Desktop

# download ("clone") the project from GitHub
git clone https://github.com/vic-3/cv-screening-system.git

# move into the project folder you just downloaded
cd cv-screening-system
```

You now have the whole project on your computer. (Follow the **Setup** section
above once to install the modules and create your virtual environment.)

### Step 4 — Get the latest code before you start working

Other people may have added changes since last time. Always grab them first so
you're not working on old code:

```bash
git checkout main          # make sure you're on the main lane
git pull origin main       # download everyone's latest changes
```

### Step 5 — Create your own branch (your personal lane)

A **branch** is your own private copy of the code where you can experiment
without affecting anyone else. Name it after yourself so the team knows whose
work it is:

```bash
# create a new branch AND switch to it, in one command
git checkout -b victory

# other examples:
#   git checkout -b daniel
#   git checkout -b muhammad-ranker   (name + what you're doing is even better)
```

Check which branch you're on at any time with:

```bash
git branch        # the one with a * next to it is where you are
```

### Step 6 — Write your code

Open **only your own file** (see the table at the top of this README) and write
your part. For example, if you're Victory you work in
`cv_screener/gui.py`.

Here is a tiny example of adding sample code. Say you open your file and type a
simple function so there's something to test:

```python
# cv_screener/gui.py  (just an example to practice the workflow)

def say_hello(name):
    return f"Hello, {name}! The GUI module is alive."


if __name__ == "__main__":
    print(say_hello("team"))
```

Save the file. You can run a single Python file from the terminal to check it
works:

```bash
python cv_screener/gui.py
```

### Step 7 — Save your work with Git (stage + commit)

Git doesn't save your changes automatically. You "commit" them, which is like
taking a snapshot with a note describing what you did:

```bash
# see what you changed (optional, but good habit)
git status

# stage your changes (prepare them to be saved).
git add .                 # the "." means "all my changed files"

# commit them with a short message describing what you did
git commit -m "Add say_hello function to GUI module"
```

> **Tip:** commit small and often. Each commit should be one clear step with a
> short message like `"Add PDF reader"` or `"Fix ranking bug"`.

### Step 8 — Push your branch to GitHub

So far your work only exists on your computer. "Pushing" uploads your branch to
GitHub so the team can see it:

```bash
git push origin victory      # use YOUR branch name here
```

The first time you push a new branch, Git may print a longer command to copy —
just paste and run whatever it suggests, e.g.
`git push --set-upstream origin victory`.

### Step 9 — Open a Pull Request (ask for your code to be added)

A **Pull Request (PR)** is you politely asking: "Please review my work and add it
to the main project." You do this on the GitHub website:

1. Go to **https://github.com/vic-3/cv-screening-system** in your browser.
2. GitHub usually shows a yellow banner: **"Compare & pull request"** — click it.
   (If you don't see it, click the **Pull requests** tab -> **New pull request**,
   then pick your branch.)
3. Make sure it says: base `main`  <-  compare `your-branch`.
4. Write a title and a short description of what you did.
5. Click **Create pull request**.
6. Tell the team (or the person merging) that it's ready. Once it's reviewed and
   approved, it gets **merged** into `main`.

### Step 10 — Start fresh for your next task

After your PR is merged, go back and get the updated code before doing more work:

```bash
git checkout main
git pull origin main
git checkout -b victory-next-task    # a fresh branch for the next thing
```

That's the whole loop. **Install and clone once (Steps 1–3), then repeat
Steps 4 -> 9 every time.**

### Quick reference (the whole routine in order)

```bash
git checkout main                      # 1. go to main
git pull origin main                   # 2. get latest
git checkout -b yourname               # 3. make your branch
# ... write your code in YOUR file ...
git add .                              # 4. stage changes
git commit -m "describe what you did"  # 5. save a snapshot
git push origin yourname               # 6. upload your branch
# 7. open a Pull Request on github.com
```

### If something goes wrong

- **"I'm on the wrong branch!"** -> `git checkout yourname` to switch back.
- **"What did I change?"** -> `git status` and `git diff`.
- **"I edited the wrong file / want to undo unsaved changes"** ->
  `git checkout -- filename` (careful: this throws away unsaved edits to that file).
- **Push rejected / "updates were rejected"** -> someone pushed before you.
  Run `git pull origin main` to merge their changes, fix any conflicts, then push again.
- When in doubt, **ask the team before forcing anything** — never run commands
  with `--force` unless someone experienced tells you to.
