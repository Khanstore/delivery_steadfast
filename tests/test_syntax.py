# Lightweight source-package test; full Odoo tests require an Odoo 18 runtime.
import ast
from pathlib import Path


def test_python_sources_parse():
    root = Path(__file__).resolve().parents[1]
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
