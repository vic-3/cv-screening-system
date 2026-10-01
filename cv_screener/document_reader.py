"""Document reading / text extraction.

OWNER: Daniel Orisakwe  (CV File Processing & Text Extraction)

Will read plain text from TXT, PDF and DOC/DOCX files and scan a folder of CVs.
Uses pdfplumber (PDF) and python-docx (DOCX). Returns CVDocument objects from
models.py so the rest of the pipeline can use them.
"""
