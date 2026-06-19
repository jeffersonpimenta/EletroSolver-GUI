from gui import casos
from gui import diagrama as dg


def _sistema():
    barras, ramos, _ = casos.carregar("d3")
    return barras, ramos


def test_adicionar_e_remover_barra():
    barras = dg.adicionar_barra([])
    assert len(barras) == 1 and barras[0]["id"] == 1
    assert barras[0]["kv"] == 138.0
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
    assert b["tipo"] == antes["tipo"] and b["V"] == antes["V"] and b["P"] == antes["P"]


def test_conectar_evita_duplicado_e_traz_seq_zero():
    ramos = dg.conectar([], 1, 2)
    assert {"ligacao", "r0", "x0", "b0"} <= set(ramos[0])
    ramos = dg.conectar(ramos, 2, 1)  # mesmo par, sentido invertido
    assert len(ramos) == 1
    ramos = dg.conectar(ramos, 1, 1)  # auto-laço ignorado
    assert len(ramos) == 1


def test_auto_organizar_so_move():
    barras, _ = _sistema()
    novo = dg.auto_organizar(barras)
    assert {b["id"] for b in novo} == {b["id"] for b in barras}
    assert any(n["x"] != b["x"] or n["y"] != b["y"] for n, b in zip(novo, barras, strict=True))


def test_imutabilidade():
    barras = [{"id": 1, "nome": "x", "tipo": 1, "V": 1.0, "theta": 0,
               "P": 0, "Q": 0, "x": 0, "y": 0}]
    novo = dg.atualizar_barra(barras, 1, V=1.05)
    assert barras[0]["V"] == 1.0
    assert novo[0]["V"] == 1.05


def test_validar_ok():
    barras, ramos = _sistema()
    checks = dg.validar(barras, ramos)
    assert all(isinstance(c, dict) and "ok" in c and "texto" in c for c in checks)
    assert dg.eh_valido(barras, ramos)


def test_validar_sem_slack():
    barras, ramos = _sistema()
    for b in barras:
        b["tipo"] = 1
    checks = dg.validar(barras, ramos)
    assert not dg.eh_valido(barras, ramos)
    assert any("Slack" in c["texto"] for c in checks)


def test_validar_nao_conexo():
    barras, ramos = _sistema()
    barras = dg.adicionar_barra(barras)  # barra solta
    checks = dg.validar(barras, ramos)
    assert any("ilhada" in c["texto"] for c in checks)
    assert not dg.eh_valido(barras, ramos)


def test_render_canvas_contem_nos():
    barras, ramos = _sistema()
    html = dg.render_canvas(barras, ramos, modo="editar", sel_kind="barra", sel_id=1)
    assert 'id="es-canvas"' in html
    assert 'data-bid="1"' in html
    assert html.count('data-bid="') == len(barras)


def test_render_canvas_reflete_ligacao_de_trafo():
    """Trocar a ligação para transformador deve mudar o desenho (2 bobinas + rótulo)."""
    barras, ramos = _sistema()  # d3: ramo 1 (1→2) já é 'Dyn'
    html = dg.render_canvas(barras, ramos, modo="editar")
    assert ">Dyn<" in html  # rótulo do trafo desenhado no canvas

    # ao virar 'linha', o símbolo (2 círculos) e o rótulo somem
    so_linha = dg.atualizar_ramo(ramos, ramos[0]["id"], ligacao="linha")
    html_l = dg.render_canvas(barras, so_linha, modo="editar")
    assert ">Dyn<" not in html_l
    assert html_l.count("<circle") == html.count("<circle") - 2

    # e ao virar transformador, o símbolo reaparece para aquele ramo
    com_trafo = dg.atualizar_ramo(so_linha, so_linha[1]["id"], ligacao="YNyn")
    html_t = dg.render_canvas(barras, com_trafo, modo="editar")
    assert ">YNyn<" in html_t
    assert html_t.count("<circle") == html_l.count("<circle") + 2


def test_cor_v_extremos():
    assert dg.cor_v(0.90).startswith("hsl(0")
    assert "130" in dg.cor_v(1.05)
