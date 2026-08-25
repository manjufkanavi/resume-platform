"""Pytest config: put the api/ package on sys.path so intra-package
imports (from routes import ..., from services.ats import ...) resolve."""
import os
import sys

_API_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _API_DIR not in sys.path:
    sys.path.insert(0, _API_DIR)
