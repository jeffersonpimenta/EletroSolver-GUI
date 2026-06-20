from gui import casos, graficos, solver


def _res():
    barras, ramos, params = casos.carregar("d3")
    return solver.rodar_fluxo(barras, ramos, params)


def _curto():
    barras, ramos, params = casos.carregar("d5")
    return solver.rodar_curto(barras, ramos, params, {"tipo": "mono", "barra": 3, "Zf": 0.0})


def test_perfil_tensao_svg():
    svg = graficos.perfil_tensao_svg(_res())
    assert svg.startswith("<svg")
    assert "rect" in svg
    assert graficos.perfil_tensao_svg(None) == ""


def test_fasores_svg():
    svg = graficos.fasores_svg(_curto())
    assert svg.startswith("<svg")
    assert graficos.fasores_svg(None) == ""
    assert graficos.fasores_svg({"erro": "x"}) == ""


def test_contribuicoes_svg():
    html = graficos.contribuicoes_svg(_curto())
    assert "kA" in html
    assert graficos.contribuicoes_svg(None) == ""


def test_matriz_zbus_svg():
    cu = _curto()
    pos = graficos.matriz_zbus_svg(cu, "pos")
    zero = graficos.matriz_zbus_svg(cu, "zero")
    assert "<table" in pos and "<table" in zero
    assert graficos.matriz_zbus_svg(None) == ""


def test_matriz_ybus_svg():
    barras, ramos, _ = casos.carregar("d3")
    fluxo = graficos.matriz_ybus_svg(barras, ramos, "pos", "fluxo")
    falta1 = graficos.matriz_ybus_svg(barras, ramos, "pos", "falta")
    falta0 = graficos.matriz_ybus_svg(barras, ramos, "zero", "falta")
    assert "<table" in fluxo and "<table" in falta1 and "<table" in falta0
    assert graficos.matriz_ybus_svg([], []) == ""
