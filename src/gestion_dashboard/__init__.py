"""Budget Personnel — Streamlit dashboard application."""
from __future__ import annotations

import os
import subprocess
import sys


def main() -> None:
    """Launch the Streamlit application."""
    app_path = os.path.join(os.path.dirname(__file__), "app.py")
    cmd = [sys.executable, "-m", "streamlit", "run", app_path, "--server.headless", "false"]
    subprocess.run(cmd, check=False)
