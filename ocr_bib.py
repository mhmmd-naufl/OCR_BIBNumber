"""ocr_bib.py — Legacy compatibility launcher.

The main pipeline has been moved to run.py (modular architecture).
This file exists only for backward compatibility so that
`python ocr_bib.py` still works.

Do NOT add new logic here. Edit run.py and the ocr/ package instead.
"""

from run import main

if __name__ == '__main__':
    main()
