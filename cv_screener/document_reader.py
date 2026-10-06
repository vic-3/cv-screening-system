"""Document reading - TXT / PDF / DOCX.

OWNER: Daniel Orisakwe  (Document Processing)

The real implementation lives in the project-root `document_reader.py`. This
module is a thin wrapper so that `import document_reader` works whether the code
is run from the project root OR from inside the cv_screener package (where this
file would otherwise shadow the root one). It re-exports the same functions, so
callers use it exactly the same way:

    from document_reader import read_document, clean_text
"""

from __future__ import annotations

import importlib.util
import os

# Load the real reader from the project root and re-export its functions.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_READER_PATH = os.path.join(_ROOT, "document_reader.py")

_spec = importlib.util.spec_from_file_location("_root_document_reader", _READER_PATH)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

read_txt = _module.read_txt
read_pdf = _module.read_pdf
read_docx = _module.read_docx
read_document = _module.read_document
clean_text = _module.clean_text
