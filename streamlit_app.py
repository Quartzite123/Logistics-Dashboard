"""Top-level Streamlit entry point.

Run from the project root:
    streamlit run streamlit_app.py
"""
import sys
from pathlib import Path

# Ensure repo root is on sys.path so `app.*` imports work when Streamlit
# launches this file directly.
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import main

main()
