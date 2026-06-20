"""Fixtures e ajustes de path para os testes headless."""
import sys
from pathlib import Path

pytest_plugins = ["nicegui.testing.plugin"]

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
