"""Application entry point - run this to start the app.

OWNER: Ojeaga Jeffrey  (System Integration)

Launches the Tkinter GUI (cv_screener.gui). Run with:

    python main.py
"""

import os
import sys

# Make sure this folder is on the path so `cv_screener` imports cleanly no
# matter where the command is run from.
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from cv_screener.gui import main

if __name__ == "__main__":
    main()
