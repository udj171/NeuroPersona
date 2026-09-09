# ============================================================================
# conftest.py - Pytest configuration
# ============================================================================
# Only puts the backend package on sys.path. There is no app factory in this
# project (app.py builds a module-level `app`), so importing one here used to
# break collection for every test in the directory.
# ============================================================================

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
