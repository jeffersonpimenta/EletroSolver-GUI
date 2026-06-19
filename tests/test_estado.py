from gui.estado import PARAMS_PADRAO, Projeto


def test_round_trip_serial():
    p = Projeto.exemplo()
    d = p.to_dict()
    q = Projeto.from_dict(d)
    assert q.nome == p.nome
    assert len(q.barras) == len(p.barras)
    assert q.params_fluxo["Sbase"] == p.params_fluxo["Sbase"]


def test_resultado_nao_persiste():
    p = Projeto.exemplo()
    p.resultado_fluxo = {"convergiu": True}
    assert "resultado_fluxo" not in p.to_dict()


def test_estado_itens_e_progresso():
    p = Projeto.vazio()
    itens = p.estado_itens()
    assert {it["chave"] for it in itens} == {"barras", "ramos", "slack", "fluxo"}
    assert p.progresso() == 0.0
    p = Projeto.exemplo()
    assert p.progresso() > 0.0


def test_definir_sistema_reseta_resultado():
    p = Projeto.exemplo()
    p.resultado_fluxo = {"x": 1}
    p.definir_sistema([], [], nome="vazio")
    assert p.resultado_fluxo is None


def test_params_padrao_default():
    p = Projeto.from_dict({})
    assert p.params_fluxo == PARAMS_PADRAO
