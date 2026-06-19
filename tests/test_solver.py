import numpy as np

from gui import casos, solver


def _sistema():
    barras, ramos, params = casos.carregar("3-barras")
    return barras, ramos, params


def test_montar_ybus_simetrica():
    barras, ramos, _ = _sistema()
    Y = np.asarray(solver.montar_ybus(barras, ramos), dtype=complex)
    assert Y.shape == (3, 3)
    assert np.allclose(Y, Y.T)  # Ybus simétrica sem defasadores


def test_rodar_fluxo_converge():
    barras, ramos, params = _sistema()
    res = solver.rodar_fluxo(barras, ramos, params)
    assert res["convergiu"] is True
    assert len(res["barras"]) == 3
    # Slack mantém tensão de referência
    slack = next(b for b in res["barras"] if b["tipo"] == 3)
    assert abs(slack["V"] - 1.04) < 1e-6
    # tensões em faixa plausível
    assert all(0.8 < b["V"] < 1.2 for b in res["barras"])


def test_rodar_fluxo_perdas_positivas():
    barras, ramos, params = _sistema()
    res = solver.rodar_fluxo(barras, ramos, params)
    assert res["perdas_totais"]["P_loss"] >= 0


def test_rodar_fluxo_entrada_invalida_nao_levanta():
    res = solver.rodar_fluxo([], [], {"tolerancia": 1e-6, "max_iter": 10, "Sbase": 100})
    assert res["convergiu"] is False
    assert "erro" in res


def test_rodar_fluxo_5_barras():
    barras, ramos, params = casos.carregar("5-barras")
    res = solver.rodar_fluxo(barras, ramos, params)
    assert res["convergiu"] is True
    assert len(res["ramos"]) == 7


def test_exportar_sistema_estrutura():
    barras, ramos, params = _sistema()
    d = solver.exportar_sistema(barras, ramos, params)
    assert set(d) >= {"barras", "fluxos", "perdas", "parametros", "matriz_admitancia"}
    assert len(d["barras"]) == 3
