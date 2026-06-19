"""Casos de teste prontos (didáticos / IEEE).

Funções puras: devolvem ``(barras, ramos, params)`` em dicts simples, prontos
para ``Projeto.definir_sistema``. Sem dependência de UI. Dados portados do
design ``modelo/`` (caso3, caso5, IEEE 9, IEEE 14).

Convenções: ``tipo`` 1=PQ, 2=PV, 3=Slack; ``theta`` em rad; ``de``/``para``
1-based (= id da barra). Impedância de sequência positiva em ``r``/``x``,
susceptância shunt total em ``b``, tap em ``tap``. Para o curto-circuito: ``kv``
(nível de tensão da barra), ``xd``/``xd0`` (reatâncias subtransitórias da fonte)
e, por ramo, ``ligacao`` + sequência zero ``r0``/``x0``/``b0``.
"""
from __future__ import annotations

PARAMS = {"tolerancia": 1e-6, "max_iter": 100, "Sbase": 100.0}


def _b(bid, nome, tipo, V, P, Q, x, y, kv=138.0, xd=None, xd0=None, theta=0.0):
    d = {"id": bid, "nome": nome, "tipo": tipo, "V": V, "theta": theta,
         "P": P, "Q": Q, "x": x, "y": y, "kv": kv}
    if xd is not None:
        d["xd"] = xd
    if xd0 is not None:
        d["xd0"] = xd0
    return d


def _r(rid, de, para, r, x, b, tap, ligacao, r0, x0, b0):
    return {"id": rid, "de": de, "para": para, "r": r, "x": x, "b": b, "tap": tap,
            "ligacao": ligacao, "r0": r0, "x0": x0, "b0": b0}


def _caso3():
    barras = [
        _b(1, "Slack", 3, 1.05, 0.0, 0.0, 180, 110, kv=13.8, xd=0.10, xd0=0.06),
        _b(2, "Geração", 2, 1.03, 0.30, 0.0, 540, 110, kv=138, xd=0.12, xd0=0.08),
        _b(3, "Carga", 1, 1.00, -0.55, -0.20, 360, 340, kv=138),
    ]
    ramos = [
        _r(1, 1, 2, 0.03, 0.10, 0.0, 1, "Dyn", 0.03, 0.10, 0.0),
        _r(2, 1, 3, 0.05, 0.16, 0.03, 1, "linha", 0.15, 0.48, 0.02),
        _r(3, 2, 3, 0.04, 0.12, 0.03, 1, "linha", 0.12, 0.36, 0.02),
    ]
    return barras, ramos, dict(PARAMS)


def _caso5():
    barras = [
        _b(1, "Usina", 3, 1.04, 0.0, 0.0, 140, 90, kv=13.8, xd=0.10, xd0=0.06),
        _b(2, "Subest. 2", 2, 1.02, 0.40, 0.0, 440, 90, kv=138, xd=0.12, xd0=0.08),
        _b(3, "Carga 3", 1, 1.00, -0.45, -0.15, 140, 340, kv=138),
        _b(4, "Carga 4", 1, 1.00, -0.40, -0.05, 440, 340, kv=138),
        _b(5, "Carga 5", 1, 1.00, -0.60, -0.10, 710, 215, kv=138),
    ]
    ramos = [
        _r(1, 1, 2, 0.02, 0.06, 0.0, 1, "Dyn", 0.02, 0.06, 0.0),
        _r(2, 1, 3, 0.08, 0.24, 0.05, 1, "linha", 0.24, 0.72, 0.03),
        _r(3, 2, 3, 0.06, 0.18, 0.04, 1, "linha", 0.18, 0.54, 0.02),
        _r(4, 2, 4, 0.06, 0.18, 0.04, 1, "linha", 0.18, 0.54, 0.02),
        _r(5, 2, 5, 0.04, 0.12, 0.03, 1, "linha", 0.12, 0.36, 0.02),
        _r(6, 3, 4, 0.01, 0.03, 0.02, 1, "linha", 0.03, 0.09, 0.01),
        _r(7, 4, 5, 0.08, 0.24, 0.05, 1, "linha", 0.24, 0.72, 0.03),
    ]
    return barras, ramos, dict(PARAMS)


def _ieee9():
    """IEEE 9 barras (WSCC, 3 geradores). pu na base de 100 MVA."""
    barras = [
        _b(1, "G1", 3, 1.040, 0.0, 0.0, 90, 150, kv=16.5, xd=0.10, xd0=0.06),
        _b(2, "G2", 2, 1.025, 1.63, 0.0, 170, 470, kv=18, xd=0.085, xd0=0.05),
        _b(3, "G3", 2, 1.025, 0.85, 0.0, 760, 110, kv=13.8, xd=0.12, xd0=0.07),
        _b(4, "Barra 4", 1, 1.0, 0.0, 0.0, 230, 150, kv=230),
        _b(5, "Carga A", 1, 1.0, -1.25, -0.50, 170, 320, kv=230),
        _b(6, "Carga B", 1, 1.0, -0.90, -0.30, 430, 90, kv=230),
        _b(7, "Barra 7", 1, 1.0, 0.0, 0.0, 310, 400, kv=230),
        _b(8, "Carga C", 1, 1.0, -1.00, -0.35, 560, 360, kv=230),
        _b(9, "Barra 9", 1, 1.0, 0.0, 0.0, 610, 170, kv=230),
    ]
    ramos = [
        _r(1, 1, 4, 0.0, 0.0576, 0.0, 1, "Dyn", 0.0, 0.0576, 0.0),
        _r(2, 4, 5, 0.0100, 0.0850, 0.176, 1, "linha", 0.030, 0.255, 0.10),
        _r(3, 4, 6, 0.0170, 0.0920, 0.158, 1, "linha", 0.051, 0.276, 0.09),
        _r(4, 5, 7, 0.0320, 0.1610, 0.306, 1, "linha", 0.096, 0.483, 0.18),
        _r(5, 6, 9, 0.0390, 0.1700, 0.358, 1, "linha", 0.117, 0.510, 0.21),
        _r(6, 7, 8, 0.0085, 0.0720, 0.149, 1, "linha", 0.026, 0.216, 0.09),
        _r(7, 8, 9, 0.0119, 0.1008, 0.209, 1, "linha", 0.036, 0.302, 0.12),
        _r(8, 2, 7, 0.0, 0.0625, 0.0, 1, "Dyn", 0.0, 0.0625, 0.0),
        _r(9, 3, 9, 0.0, 0.0586, 0.0, 1, "Dyn", 0.0, 0.0586, 0.0),
    ]
    return barras, ramos, dict(PARAMS)


def _ieee14():
    """IEEE 14 barras. pu na base de 100 MVA."""
    barras = [
        _b(1, "G1", 3, 1.060, 0.0, 0.0, 90, 440, kv=138, xd=0.10, xd0=0.06),
        _b(2, "G2", 2, 1.045, 0.40, 0.0, 220, 360, kv=138, xd=0.10, xd0=0.06),
        _b(3, "CS3", 2, 1.010, 0.0, 0.0, 220, 520, kv=138, xd=0.12, xd0=0.07),
        _b(4, "Barra 4", 1, 1.0, -0.478, 0.039, 400, 440, kv=138),
        _b(5, "Barra 5", 1, 1.0, -0.076, -0.016, 300, 430, kv=138),
        _b(6, "CS6", 2, 1.070, 0.0, 0.0, 95, 230, kv=69, xd=0.12, xd0=0.07),
        _b(7, "Barra 7", 1, 1.0, 0.0, 0.0, 520, 330, kv=69),
        _b(8, "CS8", 2, 1.090, 0.0, 0.0, 520, 200, kv=13.8, xd=0.12, xd0=0.07),
        _b(9, "Barra 9", 1, 1.0, -0.295, -0.166, 540, 470, kv=69),
        _b(10, "Barra 10", 1, 1.0, -0.090, -0.058, 560, 580, kv=69),
        _b(11, "Barra 11", 1, 1.0, -0.035, -0.018, 360, 250, kv=69),
        _b(12, "Barra 12", 1, 1.0, -0.061, -0.016, 95, 90, kv=69),
        _b(13, "Barra 13", 1, 1.0, -0.135, -0.058, 300, 95, kv=69),
        _b(14, "Barra 14", 1, 1.0, -0.149, -0.050, 700, 430, kv=69),
    ]
    ramos = [
        _r(1, 1, 2, 0.01938, 0.05917, 0.0528, 1, "linha", 0.058, 0.178, 0.03),
        _r(2, 1, 5, 0.05403, 0.22304, 0.0492, 1, "linha", 0.162, 0.669, 0.03),
        _r(3, 2, 3, 0.04699, 0.19797, 0.0438, 1, "linha", 0.141, 0.594, 0.03),
        _r(4, 2, 4, 0.05811, 0.17632, 0.0340, 1, "linha", 0.174, 0.529, 0.02),
        _r(5, 2, 5, 0.05695, 0.17388, 0.0346, 1, "linha", 0.171, 0.522, 0.02),
        _r(6, 3, 4, 0.06701, 0.17103, 0.0128, 1, "linha", 0.201, 0.513, 0.01),
        _r(7, 4, 5, 0.01335, 0.04211, 0.0, 1, "linha", 0.040, 0.126, 0.0),
        _r(8, 4, 7, 0.0, 0.20912, 0.0, 0.978, "Dyn", 0.0, 0.20912, 0.0),
        _r(9, 4, 9, 0.0, 0.55618, 0.0, 0.969, "Dyn", 0.0, 0.55618, 0.0),
        _r(10, 5, 6, 0.0, 0.25202, 0.0, 0.932, "Dyn", 0.0, 0.25202, 0.0),
        _r(11, 6, 11, 0.09498, 0.19890, 0.0, 1, "linha", 0.285, 0.597, 0.0),
        _r(12, 6, 12, 0.12291, 0.25581, 0.0, 1, "linha", 0.369, 0.767, 0.0),
        _r(13, 6, 13, 0.06615, 0.13027, 0.0, 1, "linha", 0.198, 0.391, 0.0),
        _r(14, 7, 8, 0.0, 0.17615, 0.0, 1, "Dyn", 0.0, 0.17615, 0.0),
        _r(15, 7, 9, 0.0, 0.11001, 0.0, 1, "linha", 0.0, 0.330, 0.0),
        _r(16, 9, 10, 0.03181, 0.08450, 0.0, 1, "linha", 0.095, 0.254, 0.0),
        _r(17, 9, 14, 0.12711, 0.27038, 0.0, 1, "linha", 0.381, 0.811, 0.0),
        _r(18, 10, 11, 0.08205, 0.19207, 0.0, 1, "linha", 0.246, 0.576, 0.0),
        _r(19, 12, 13, 0.22092, 0.19988, 0.0, 1, "linha", 0.663, 0.600, 0.0),
        _r(20, 13, 14, 0.17093, 0.34802, 0.0, 1, "linha", 0.513, 1.044, 0.0),
    ]
    return barras, ramos, dict(PARAMS)


# (chave, construtor, metadados da galeria)
_CASOS = {
    "d3": (_caso3, {
        "nome": "Sistema didático", "sub": "3 barras", "nb": 3, "nr": 3,
        "kv": "13,8 / 138 kV", "tag": "Didático",
        "desc": "Slack, gerador PV e carga PQ. Ideal para um primeiro fluxo e "
                "uma falta simples."}),
    "d5": (_caso5, {
        "nome": "Sistema didático", "sub": "5 barras", "nb": 5, "nr": 7,
        "kv": "13,8 / 138 kV", "tag": "Didático",
        "desc": "Usina, subestação e três cargas em malha. Mostra trânsito de "
                "potência e curto em rede malhada."}),
    "ieee9": (_ieee9, {
        "nome": "IEEE 9 barras", "sub": "WSCC · 3 geradores", "nb": 9, "nr": 9,
        "kv": "13,8–230 kV", "tag": "IEEE",
        "desc": "Sistema clássico de 3 máquinas e 3 cargas (Anderson–Fouad). "
                "Referência para fluxo e estabilidade."}),
    "ieee14": (_ieee14, {
        "nome": "IEEE 14 barras", "sub": "Rede de transmissão", "nb": 14, "nr": 20,
        "kv": "13,8–138 kV", "tag": "IEEE",
        "desc": "Rede de transmissão com 5 geradores/condensadores e 3 "
                "transformadores com tap. Caso de teste padrão."}),
}

# Compatível com chamadas antigas por descrição.
CASOS = {chave: meta["nome"] + " · " + meta["sub"] for chave, (_, meta) in _CASOS.items()}


def lista_casos() -> list[dict]:
    """Metadados dos casos para a galeria (na ordem de exibição)."""
    return [{"chave": chave, **meta} for chave, (_, meta) in _CASOS.items()]


def nome_caso(chave: str) -> str:
    """Rótulo 'Nome · sub' do caso (para ``Projeto.nome``)."""
    meta = _CASOS[chave][1]
    return f"{meta['nome']} · {meta['sub']}"


def carregar(chave: str):
    """Devolve ``(barras, ramos, params)`` do caso pedido."""
    if chave not in _CASOS:
        raise KeyError(f"Caso desconhecido: {chave!r}")
    return _CASOS[chave][0]()
