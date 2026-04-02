#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Get conda Python executable path for VS Code debugger
This uses the same logic as check_and_move.ps1
"""
import os
import sys

CONDA_ENV_NAME = "labelme"

# Try common conda installation paths
conda_paths = [
    os.path.join(os.environ.get("USERPROFILE", ""), "anaconda3"),
    os.path.join(os.environ.get("USERPROFILE", ""), "miniconda3"),
    os.path.join(os.environ.get("ProgramData", ""), "anaconda3"),
    os.path.join(os.environ.get("ProgramData", ""), "miniconda3"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "anaconda3"),
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "miniconda3"),
    "C:\\anaconda3",
    "C:\\miniconda3",
]

for conda_path in conda_paths:
    if conda_path and os.path.exists(conda_path):
        python_path = os.path.join(conda_path, "envs", CONDA_ENV_NAME, "python.exe")
        if os.path.exists(python_path):
            print(python_path)
            sys.exit(0)

# Try using conda command
try:
    import subprocess
    result = subprocess.run(
        ["conda", "info", "--base"],
        capture_output=True,
        text=True,
        timeout=5
    )
    if result.returncode == 0:
        conda_base = result.stdout.strip()
        python_path = os.path.join(conda_base, "envs", CONDA_ENV_NAME, "python.exe")
        if os.path.exists(python_path):
            print(python_path)
            sys.exit(0)
except Exception:
    pass

# Fallback to system python
python_exe = sys.executable
if python_exe:
    print(python_exe)
    sys.exit(0)

print("Error: Could not find Python executable", file=sys.stderr)
sys.exit(1)
