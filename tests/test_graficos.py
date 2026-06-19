from gui import casos, graficos, solver


def _res():
    barras, ramos, params = casos.carregar("3-barras")
    return solver.rodar_fluxo(barras, ramos, params)


def test_figuras_com_resultado():
    res = _res()
    for fn in (graficos.perfil_tensao, graficos.transito_potencia,
               graficos.perdas_ramo, graficos.angulos):
        fig = fn(res)
        assert fig is not None
        assert len(fig.data) >= 1


def test_figuras_vazias_sem_resultado():
    for fn in (graficos.perfil_tensao, graficos.transito_potencia,
               graficos.perdas_ramo, graficos.angulos):
        fig = fn(None)
        assert fig is not None  # devolve placeholder, não quebra


def test_perfil_tensao_tem_uma_barra_por_no():
    res = _res()
    fig = graficos.perfil_tensao(res)
    assert len(fig.data[0].x) == len(res["barras"])
