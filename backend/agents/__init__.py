"""Agent package exports."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

_module_path = Path(__file__).with_name("notebooklm-agent.py")
_spec = importlib.util.spec_from_file_location("agents.notebooklm_agent", _module_path)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Unable to load RAG agent module from {_module_path}")

_module = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _module
_spec.loader.exec_module(_module)

ask_rag = _module.ask_rag

