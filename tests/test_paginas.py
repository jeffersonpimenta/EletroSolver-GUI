"""Fumaça da camada de UI: os módulos importam e a rota única é registrada.

Não levanta o servidor — apenas confirma que ``@ui.page('/')`` registrou o
caminho e que layout/componentes/workspace importam de forma limpa.
"""


def test_importar_main_registra_rota_unica():
    from nicegui import app

    import gui.main  # noqa: F401  (registra a página '/')

    caminhos = {getattr(r, "path", None) for r in app.routes}
    assert "/" in caminhos


def test_layout_e_componentes_importam():
    from gui import componentes, layout

    assert layout.ACCENT.startswith("#")
    assert callable(layout.tema)
    assert callable(layout.montar_drawer)
    assert callable(componentes.cartao)
    assert callable(componentes.chip)


def test_workspace_importa():
    from gui.workspace import Workspace

    assert callable(Workspace.construir)


def test_main_define_entrypoint():
    from gui import main

    assert callable(main.main)
