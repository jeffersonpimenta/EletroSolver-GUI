"""Integração ponta-a-ponta (headless): caso → solver → diagrama → gráficos.

Exercita o caminho de dados sem UI, como faz o controlador da página única.
"""
from gui import casos, graficos, solver
from gui import diagrama as dg
from gui.estado import Projeto


def test_fluxo_completo_3_barras():
    barras, ramos, params = casos.carregar("d3")
    proj = Projeto()
    proj.definir_sistema(barras, ramos, params, nome="teste")

    assert dg.eh_valido(proj.barras, proj.ramos)

    res = solver.rodar_fluxo(proj.barras, proj.ramos, dict(proj.params_fluxo))
    proj.resultado_fluxo = res
    assert res["convergiu"]

    assert graficos.perfil_tensao_svg(res).startswith("<svg")

    # diagrama em modo fluxo anota o trânsito (MW) sobre os ramos
    html = dg.render_canvas(proj.barras, proj.ramos, modo="fluxo", resultado=res)
    assert "MW" in html

    assert proj.progresso() > 0.0


def test_curto_completo_5_barras():
    barras, ramos, params = casos.carregar("d5")
    proj = Projeto()
    proj.definir_sistema(barras, ramos, params)
    cu = solver.rodar_curto(proj.barras, proj.ramos, dict(proj.params_fluxo),
                            {"tipo": "tri", "barra": 3, "Zf": 0.0})
    proj.resultado_curto = cu
    assert "erro" not in cu
    # nó em falta destacado no diagrama (modo curto)
    html = dg.render_canvas(proj.barras, proj.ramos, modo="curto", curto=cu)
    assert "If =" in html
    assert graficos.fasores_svg(cu).startswith("<svg")


def test_edicao_topologia_recalcula():
    barras, ramos, params = casos.carregar("d5")
    proj = Projeto()
    proj.definir_sistema(barras, ramos, params)
    res1 = solver.rodar_fluxo(proj.barras, proj.ramos, dict(proj.params_fluxo))
    assert res1["convergiu"]

    proj.barras = dg.adicionar_barra(proj.barras, tipo=1)
    nova = proj.barras[-1]["id"]
    proj.ramos = dg.conectar(proj.ramos, 1, nova, r=0.03, x=0.09)
    res2 = solver.rodar_fluxo(proj.barras, proj.ramos, dict(proj.params_fluxo))
    assert res2["convergiu"]
    assert len(res2["barras"]) == len(res1["barras"]) + 1


def test_round_trip_projeto_preserva_calculabilidade():
    barras, ramos, params = casos.carregar("ieee9")
    proj = Projeto()
    proj.definir_sistema(barras, ramos, params)
    proj2 = Projeto.from_dict(proj.to_dict())
    res = solver.rodar_fluxo(proj2.barras, proj2.ramos, dict(proj2.params_fluxo))
    assert res["convergiu"]
