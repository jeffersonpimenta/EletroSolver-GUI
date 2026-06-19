from gui import casos
from gui import diagrama as dg


def _sistema():
    barras, ramos, _ = casos.carregar("3-barras")
    return barras, ramos


def test_adicionar_e_remover_barra():
    barras = dg.adicionar_barra([])
    assert len(barras) == 1 and barras[0]["id"] == 1
    barras = dg.adicionar_barra(barras)
    assert barras[1]["id"] == 2
    barras, ramos = dg.remover_barra(barras, [], 1)
    assert [b["id"] for b in barras] == [2]


def test_remover_barra_remove_ramos_incidentes():
    barras, ramos = _sistema()
    barras, ramos = dg.remover_barra(barras, ramos, 1)
    assert all(r["de"] != 1 and r["para"] != 1 for r in ramos)


def test_mover_barra_so_cosmetico():
    barras, _ = _sistema()
    antes = dict(barras[0])
    novo = dg.mover_barra(barras, 1, 999, 888)
    b = next(x for x in novo if x["id"] == 1)
    assert b["x"] == 999 and b["y"] == 888
    # elétrica intocada
    assert b["tipo"] == antes["tipo"] and b["V"] == antes["V"] and b["P"] == antes["P"]


def test_conectar_evita_duplicado():
    ramos = dg.conectar([], 1, 2)
    ramos = dg.conectar(ramos, 2, 1)  # mesmo par, sentido invertido
    assert len(ramos) == 1
    ramos = dg.conectar(ramos, 1, 1)  # auto-laço ignorado
    assert len(ramos) == 1


def test_imutabilidade():
    barras = [{"id": 1, "nome": "x", "tipo": 1, "V": 1.0, "theta": 0,
               "P": 0, "Q": 0, "x": 0, "y": 0}]
    novo = dg.atualizar_barra(barras, 1, V=1.05)
    assert barras[0]["V"] == 1.0  # original não muda
    assert novo[0]["V"] == 1.05


def test_validar_ok():
    barras, ramos = _sistema()
    assert dg.validar(barras, ramos) == []


def test_validar_sem_slack():
    barras, ramos = _sistema()
    for b in barras:
        b["tipo"] = 1
    erros = dg.validar(barras, ramos)
    assert any("Slack" in e for e in erros)


def test_validar_nao_conexo():
    barras, ramos = _sistema()
    barras = dg.adicionar_barra(barras)  # barra solta
    barras = dg.definir_tipo(barras, barras[-1]["id"], 1)
    erros = dg.validar(barras, ramos)
    assert any("conexo" in e for e in erros)


def test_gerar_svg_contem_nos():
    barras, ramos = _sistema()
    svg = dg.gerar_svg(barras, ramos, sel_barra=1)
    assert svg.startswith("<svg")
    assert 'data-bid="1"' in svg
    assert svg.count("<line") == len(ramos)
