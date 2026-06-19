"""Fumaça da camada de UI: importar as páginas registra as rotas sem quebrar.

Não levanta o servidor — apenas confirma que ``@ui.page`` registrou os caminhos
esperados e que os módulos importam de forma limpa.
"""


def test_importar_paginas_registra_rotas():
    import gui.paginas  # noqa: F401
    from nicegui import app

    caminhos = {getattr(r, "path", None) for r in app.routes}
    for rota in ("/", "/sistema", "/fluxo", "/visualizador"):
        assert rota in caminhos, f"rota ausente: {rota}"


def test_layout_e_componentes_importam():
    from gui import componentes, layout  # noqa: F401

    assert layout.ACCENT.startswith("#")
    assert callable(componentes.cartao)
    assert callable(layout.casca)


def test_main_define_entrypoint():
    from gui import main

    assert callable(main.main)
