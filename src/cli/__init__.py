# src/cli/__init__.py

import subprocess
import sys
from pathlib import Path


def main() -> None:
    review_app = Path(__file__).parent.parent / "review" / "app.py"
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(review_app)],
            check=False,
        )
    except KeyboardInterrupt:
        pass
