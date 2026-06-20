"""Integração: trocar a ligação de um ramo pelo ``Workspace`` reflete no canvas.

Cobre o caminho real do bug reportado (linha↔trafo "não entrava" e o desenho não
mudava): combina o commit do dropdown (ver test_componentes_select) com o
redesenho do diagrama. O storage por aba é monkeypatchado para rodar headless.
"""
from gui import casos, estado
from gui.workspace import Workspace


def _ws(monkeypatch) -> Workspace:
    monkeypatch.setattr(estado, "projeto_da_aba", estado.Projeto.vazio)
    monkeypatch.setattr(estado, "salvar_na_aba", lambda proj: None)
    ws = Workspace()
    barras, ramos, params = casos.carregar("d3")  # ramo 2 (1→3) é 'linha'
    ws.proj.definir_sistema(barras, ramos, params)
    ws.sel_kind, ws.sel_id = "ramo", ramos[1]["id"]
    return ws


def test_set_ligacao_reflete_no_canvas(monkeypatch) -> None:
    ws = _ws(monkeypatch)

    # linha → transformador: dado comita e o símbolo/rótulo entram no desenho
    assert ws.ramo(ws.sel_id)["ligacao"] == "linha"
    ws.set_ligacao("YNyn")
    assert ws.ramo(ws.sel_id)["ligacao"] == "YNyn"
    assert ">YNyn<" in ws.canvas_html()

    # e volta: transformador → linha, o símbolo daquele ramo some
    ws.set_ligacao("linha")
    assert ws.ramo(ws.sel_id)["ligacao"] == "linha"
    assert ">YNyn<" not in ws.canvas_html()
