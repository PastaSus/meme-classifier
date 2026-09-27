"""Entry point for the Meme & Reaction Image Organizer.

Usage:
    python main.py [input_dir] [-o OUTPUT] [-b {mobilenet,custom-cnn}] [--dry-run]
"""
from __future__ import annotations

import sys

from cli import main

if __name__ == "__main__":
    sys.exit(main())
