"""Integração ponta-a-ponta (headless): caso → solver → diagrama → gráficos.

Exercita o caminho completo de dados sem UI, como faria a página /fluxo.
"""
from gui import casos
from gui import diagrama as dg
from gui import graficos, solver
from gui.estado import Projeto


def test_fluxo_completo_3_barras():
    barras, ramos, params = casos.carregar("3-barras")
    proj = Projeto()
    proj.definir_sistema(barras, ramos, params, nome="teste")

    # sistema válido
    assert dg.validar(proj.barras, proj.ramos) == []

    # resolve e guarda no projeto (como a página faz)
    res = solver.rodar_fluxo(proj.barras, proj.ramos, dict(proj.params_fluxo))
    proj.resultado_fluxo = res
    assert res["convergiu"]

    # gráficos consomem o resultado sem erro
    assert len(graficos.perfil_tensao(res).data) >= 1

    # diagrama anotado pelo resultado contém rótulo de fluxo
    svg = dg.gerar_svg(proj.barras, proj.ramos, resultado=res)
    assert "MW" in svg

    # progresso reflete fluxo calculado
    assert proj.progresso() == 1.0


def test_edicao_topologia_invalida_resultado_e_recalcula():
    barras, ramos, params = casos.carregar("5-barras")
    proj = Projeto()
    proj.definir_sistema(barras, ramos, params)
    res1 = solver.rodar_fluxo(proj.barras, proj.ramos, dict(proj.params_fluxo))
    assert res1["convergiu"]

    # adiciona barra + conecta → recalcula com 1 barra a mais
    proj.barras = dg.adicionar_barra(proj.barras, tipo=1)
    nova = proj.barras[-1]["id"]
    proj.ramos = dg.conectar(proj.ramos, 1, nova, r=0.03, x=0.09)
    res2 = solver.rodar_fluxo(proj.barras, proj.ramos, dict(proj.params_fluxo))
    assert res2["convergiu"]
    assert len(res2["barras"]) == len(res1["barras"]) + 1


def test_round_trip_projeto_preserva_calculabilidade():
    barras, ramos, params = casos.carregar("ieee-4")
    proj = Projeto()
    proj.definir_sistema(barras, ramos, params)
    proj2 = Projeto.from_dict(proj.to_dict())
    res = solver.rodar_fluxo(proj2.barras, proj2.ramos, dict(proj2.params_fluxo))
    assert res["convergiu"]
