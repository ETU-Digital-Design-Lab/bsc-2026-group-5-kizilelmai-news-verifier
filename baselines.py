#!/usr/bin/env python3
"""Root wrapper for scripts/evaluation/baselines.py"""
import sys
from pathlib import Path

# Add scripts/evaluation to sys.path and run main
script_path = Path(__file__).resolve().parent / "scripts" / "evaluation" / "baselines.py"
with open(script_path, "r", encoding="utf-8") as f:
    code = f.read()

exec(code, globals())
