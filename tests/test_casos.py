import pytest

from gui import casos
from gui import diagrama as dg

_ESPERADO = {"r3": (3, 2), "d3": (3, 3), "d5": (5, 7), "ieee9": (9, 9), "ieee14": (14, 20)}


def test_lista_casos_chaves():
    chaves = {c["chave"] for c in casos.lista_casos()}
    assert chaves == {"r3", "d3", "d5", "ieee9", "ieee14"}


def test_casos_sem_aviso_niveis():
    for c in casos.lista_casos():
        barras, ramos, _ = casos.carregar(c["chave"])
        assert not any(ch.get("warn") for ch in dg.validar(barras, ramos)), c["chave"]


@pytest.mark.parametrize("chave,nb_nr", _ESPERADO.items())
def test_carregar_dimensoes(chave, nb_nr):
    nb, nr = nb_nr
    barras, ramos, params = casos.carregar(chave)
    assert len(barras) == nb
    assert len(ramos) == nr
    assert sum(1 for b in barras if b["tipo"] == 3) == 1  # exatamente um Slack
    assert params["Sbase"] == 100.0


def test_campos_curto_presentes():
    barras, ramos, _ = casos.carregar("d5")
    # barras de fonte trazem kv/xd/xd0; todas trazem kv
    assert all("kv" in b for b in barras)
    fontes = [b for b in barras if b["tipo"] in (2, 3)]
    assert all({"xd", "xd0"} <= set(b) for b in fontes)
    # ramos trazem ligacao + sequência zero
    assert all({"ligacao", "r0", "x0", "b0"} <= set(r) for r in ramos)


def test_caso_desconhecido():
    with pytest.raises(KeyError):
        casos.carregar("inexistente")
