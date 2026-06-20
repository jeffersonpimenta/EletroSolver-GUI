from gui.estado import PARAMS_PADRAO, Projeto


def test_round_trip_serial():
    p = Projeto.exemplo()
    d = p.to_dict()
    q = Projeto.from_dict(d)
    assert q.nome == p.nome
    assert len(q.barras) == len(p.barras)
    assert q.params_fluxo["Sbase"] == p.params_fluxo["Sbase"]


def test_round_trip_campos_curto():
    p = Projeto.exemplo()  # caso d3 traz kv/xd/xd0 e ligacao/r0/x0/b0
    q = Projeto.from_dict(p.to_dict())
    fonte = next(b for b in q.barras if b["tipo"] in (2, 3))
    assert {"kv", "xd", "xd0"} <= set(fonte)
    assert all({"ligacao", "r0", "x0", "b0"} <= set(r) for r in q.ramos)


def test_resultado_nao_persiste():
    p = Projeto.exemplo()
    p.resultado_fluxo = {"convergiu": True}
    p.resultado_curto = {"Ipu": 1.0}
    d = p.to_dict()
    assert "resultado_fluxo" not in d
    assert "resultado_curto" not in d


def test_estado_itens_cinco():
    p = Projeto.vazio()
    itens = p.estado_itens()
    assert {it["chave"] for it in itens} == {"barras", "ramos", "valido", "fluxo", "curto"}
    assert p.progresso() == 0.0
    p = Projeto.exemplo()
    assert p.progresso() > 0.0


def test_definir_sistema_reseta_resultado():
    p = Projeto.exemplo()
    p.resultado_fluxo = {"x": 1}
    p.resultado_curto = {"y": 2}
    p.definir_sistema([], [], nome="vazio")
    assert p.resultado_fluxo is None and p.resultado_curto is None


def test_params_padrao_default():
    p = Projeto.from_dict({})
    assert p.params_fluxo == PARAMS_PADRAO


def test_alterar_sbase_preserva_mw():
    p = Projeto.exemplo()  # caso d3: Sbase 100, carga P=-0.55 pu => -55 MW
    sb0 = p.params_fluxo["Sbase"]
    mw_antes = [b["P"] * sb0 for b in p.barras]
    mvar_antes = [b["Q"] * sb0 for b in p.barras]
    p.alterar_sbase(200.0)
    assert p.params_fluxo["Sbase"] == 200.0
    assert all(abs(b["P"] * 200.0 - mw) < 1e-9
               for b, mw in zip(p.barras, mw_antes, strict=True))
    assert all(abs(b["Q"] * 200.0 - mvar) < 1e-9
               for b, mvar in zip(p.barras, mvar_antes, strict=True))


def test_alterar_sbase_ignora_nao_positivo():
    p = Projeto.exemplo()
    pu_antes = [b["P"] for b in p.barras]
    p.alterar_sbase(0.0)
    assert p.params_fluxo["Sbase"] == 100.0  # inalterado
    assert [b["P"] for b in p.barras] == pu_antes
