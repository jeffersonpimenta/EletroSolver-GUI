"""Ponto de entrada da GUI — app de **página única** NiceGUI.

A rota ``/`` instancia um :class:`gui.workspace.Workspace` por aba (após a
conexão do cliente, para ter ``app.storage.tab``) e desenha toda a interface. O
``storage_secret`` habilita o estado por aba.
"""
from __future__ import annotations

import os

from nicegui import ui

from gui.workspace import Workspace


@ui.page("/")
async def _raiz() -> None:
    await ui.context.client.connected()
    ws = Workspace()
    await ws.construir()


def main() -> None:
    headless = os.environ.get("ELETROGUI_HEADLESS") == "1"
    ui.run(
        title="EletroSolver — Sistemas de potência",
        port=int(os.environ.get("PORT", "8080")),
        host="0.0.0.0" if headless else "127.0.0.1",
        storage_secret=os.environ.get("STORAGE_SECRET")
        or os.environ.get("ELETROGUI_SECRET", "eletrosolver-dev-secret"),
        reload=False,
        show=not headless,
        favicon="⚡",
        dark=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
