import numpy as np

from gui import casos, solver


def _sistema():
    barras, ramos, params = casos.carregar("d3")
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
    assert all("nome" in b for b in res["barras"])
    slack = next(b for b in res["barras"] if b["tipo"] == 3)
    assert abs(slack["V"] - 1.05) < 1e-6
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
    barras, ramos, params = casos.carregar("d5")
    res = solver.rodar_fluxo(barras, ramos, params)
    assert res["convergiu"] is True
    assert len(res["ramos"]) == 7


def test_rodar_curto_trifasica():
    barras, ramos, params = casos.carregar("d5")
    res = solver.rodar_curto(barras, ramos, params, {"tipo": "tri", "barra": 3, "Zf": 0.0})
    assert "erro" not in res
    assert res["Ipu"] > 0 and res["Ika"] > 0 and res["Scc"] > 0
    assert len(res["Zbus"]) == 5
    # trifásica: simétrica (as três fases com o mesmo módulo)
    mags = [abs(complex(*res["fases"][f])) for f in "abc"]
    assert max(mags) - min(mags) < 1e-6


def test_rodar_curto_monofasica():
    barras, ramos, params = casos.carregar("d5")
    res = solver.rodar_curto(barras, ramos, params, {"tipo": "mono", "barra": 3, "Zf": 0.0})
    assert "erro" not in res
    # monofásica fase-terra: só a fase A conduz
    assert abs(complex(*res["fases"]["a"])) > 1e-3
    assert abs(complex(*res["fases"]["b"])) < 1e-6
    assert res["contrib"]  # ramos incidentes contribuem


def test_rodar_curto_barra_inexistente():
    barras, ramos, params = casos.carregar("d3")
    res = solver.rodar_curto(barras, ramos, params, {"tipo": "tri", "barra": 99, "Zf": 0.0})
    assert res.get("erro")


def test_rodar_fluxo_ramos_paralelos_agregados():
    # Dois ramos em paralelo entre as mesmas barras: o relatório deve trazer UMA
    # linha por par (trânsito somado pelo núcleo), sem descartar o paralelo.
    barras = [
        {"id": 1, "nome": "Slack", "tipo": 3, "V": 1.05, "theta": 0.0,
         "P": 0.0, "Q": 0.0, "kv": 138.0},
        {"id": 2, "nome": "Carga", "tipo": 1, "V": 1.0, "theta": 0.0,
         "P": -0.5, "Q": -0.2, "kv": 138.0},
    ]
    ramos = [
        {"id": 1, "de": 1, "para": 2, "r": 0.02, "x": 0.06, "b": 0.0, "tap": 1.0},
        {"id": 2, "de": 1, "para": 2, "r": 0.02, "x": 0.06, "b": 0.0, "tap": 1.0},
    ]
    res = solver.rodar_fluxo(barras, ramos, {"tolerancia": 1e-8, "max_iter": 50, "Sbase": 100})
    assert res["convergiu"] is True
    assert len(res["ramos"]) == 1
    linha = res["ramos"][0]
    assert linha["n_paralelos"] == 2
    assert set(linha["ids"]) == {1, 2}
    assert linha["P_loss"] >= 0


def test_exportar_sistema_estrutura():
    barras, ramos, params = _sistema()
    d = solver.exportar_sistema(barras, ramos, params)
    assert set(d) >= {"barras", "fluxos", "perdas", "parametros", "matriz_admitancia"}
    assert len(d["barras"]) == 3
