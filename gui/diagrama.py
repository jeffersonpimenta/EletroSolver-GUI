"""Editor de diagrama unifilar — **reducers puros** + geração do canvas (HTML/SVG).

Fonte da verdade são os **dados** (``barras``/``ramos`` do :class:`Projeto`).
Topologia só muda por estas funções puras (chamadas pelo painel/toolbar); o
arraste no canvas altera **apenas** ``x``/``y`` (cosmético) via :func:`mover_barra`.

``render_canvas`` espelha o ``buildDiagrama`` do design ``modelo/``: uma camada
SVG com os ramos (e símbolos de trafo / rótulos de fluxo) sob nós ``div``
posicionados em absoluto, coloridos conforme o modo (editar/fluxo/curto). É uma
função **pura** (string) — testável sem navegador.
"""
from __future__ import annotations

import math
from copy import deepcopy

from gui.campos import fmt

NB_MAX = 60  # teto defensivo da demo

ACCENT = "#2b6cf0"
ROXO = "#7c5cd6"
MONO = "'IBM Plex Mono',monospace"

_COR_TIPO_TXT = {1: "#2b6cf0", 2: "#16a34a", 3: "#7c5cd6"}
_ROT_TIPO = {1: "PQ", 2: "PV", 3: "Slack"}


def _novo_id(itens: list[dict]) -> int:
    return (max((it["id"] for it in itens), default=0) + 1)


# --------------------------------------------------------------------- barras
def adicionar_barra(barras, tipo=1) -> list[dict]:
    """Nova barra PQ com posição derivada do id (igual ao ``addBarra`` do modelo)."""
    barras = deepcopy(barras)
    bid = _novo_id(barras)
    x = 270 + (bid * 9) % 200
    y = 200 + (bid * 13) % 120
    barras.append({"id": bid, "nome": f"Barra {bid}", "tipo": tipo,
                   "V": 1.0, "theta": 0.0, "P": 0.0, "Q": 0.0,
                   "x": float(x), "y": float(y), "kv": 138.0})
    return barras


def remover_barra(barras, ramos, bid):
    """Remove a barra e **todos** os ramos incidentes (mantém consistência)."""
    barras = [b for b in deepcopy(barras) if b["id"] != bid]
    ramos = [r for r in deepcopy(ramos) if r["de"] != bid and r["para"] != bid]
    return barras, ramos


def atualizar_barra(barras, bid, **campos) -> list[dict]:
    barras = deepcopy(barras)
    for b in barras:
        if b["id"] == bid:
            b.update(campos)
            break
    return barras


def mover_barra(barras, bid, x, y) -> list[dict]:
    """Cosmético: só ``x``/``y``. Nunca toca topologia/elétrica."""
    return atualizar_barra(barras, bid, x=float(x), y=float(y))


def definir_tipo(barras, bid, tipo) -> list[dict]:
    return atualizar_barra(barras, bid, tipo=int(tipo))


def auto_organizar(barras) -> list[dict]:
    """Layout circular simples (igual ao ``autoOrganizar`` do modelo)."""
    barras = deepcopy(barras)
    n = len(barras)
    if n == 0:
        return barras
    cx, cy, R = 420, 235, min(180, 70 + n * 16)
    for i, b in enumerate(barras):
        ang = 2 * math.pi * i / n - math.pi / 2
        b["x"] = cx + R * math.cos(ang)
        b["y"] = cy + R * math.sin(ang)
    return barras


# ---------------------------------------------------------------------- ramos
def conectar(ramos, de, para, r=0.02, x=0.06, b=0.0, tap=1.0,
             ligacao="linha", r0=0.06, x0=0.18, b0=0.0):
    """Cria um ramo ``de→para`` se ainda não existir (em qualquer sentido)."""
    if de == para:
        return deepcopy(ramos)
    for rm in ramos:
        if {rm["de"], rm["para"]} == {de, para}:
            return deepcopy(ramos)
    ramos = deepcopy(ramos)
    ramos.append({"id": _novo_id(ramos), "de": de, "para": para,
                  "r": float(r), "x": float(x), "b": float(b), "tap": float(tap),
                  "ligacao": ligacao, "r0": float(r0), "x0": float(x0), "b0": float(b0)})
    return ramos


def remover_ramo(ramos, rid) -> list[dict]:
    return [r for r in deepcopy(ramos) if r["id"] != rid]


def atualizar_ramo(ramos, rid, **campos) -> list[dict]:
    ramos = deepcopy(ramos)
    for r in ramos:
        if r["id"] == rid:
            r.update(campos)
            break
    return ramos


# ----------------------------------------------------------- validação
def _mapa(barras) -> dict:
    return {b["id"]: b for b in barras}


def _conexo(barras, ramos) -> bool:
    if not barras:
        return False
    adj: dict[int, set] = {b["id"]: set() for b in barras}
    for r in ramos:
        if r["de"] in adj and r["para"] in adj:
            adj[r["de"]].add(r["para"])
            adj[r["para"]].add(r["de"])
    inicio = barras[0]["id"]
    visto = {inicio}
    pilha = [inicio]
    while pilha:
        u = pilha.pop()
        for v in adj[u]:
            if v not in visto:
                visto.add(v)
                pilha.append(v)
    return len(visto) == len(barras)


def validar(barras, ramos) -> list[dict]:
    """Checks estruturados ``{ok, texto, warn?}`` — espelha ``validar`` do modelo.

    ``warn=True`` marca avisos (níveis de tensão) que não bloqueiam o cálculo.
    """
    checks: list[dict] = []
    slacks = sum(1 for b in barras if b.get("tipo") == 3)
    checks.append({"ok": slacks == 1, "texto": (
        "Exatamente uma barra Slack" if slacks == 1 else
        ("Falta uma barra Slack (referência)" if slacks == 0 else
         f"{slacks} barras Slack — deve haver só uma"))})

    ids = {b["id"] for b in barras}

    def _ramo_ok(r):
        return (r["de"] in ids and r["para"] in ids and r["de"] != r["para"]
                and (float(r.get("x", 0)) != 0 or float(r.get("r", 0)) != 0))

    ramos_ok = all(_ramo_ok(r) for r in ramos)
    checks.append({"ok": ramos_ok, "texto": (
        "Ramos com índices e impedâncias válidos" if ramos_ok else
        "Há ramo com índice inválido, laço ou z = 0")})

    v_ok = all(float(b.get("V", 0)) > 0 for b in barras)
    checks.append({"ok": v_ok, "texto": (
        "Tensões base positivas em todas as barras" if v_ok else
        "Alguma barra com V ≤ 0")})

    conexo = len(barras) > 0
    if len(barras) > 1:
        conexo = _conexo(barras, ramos)
    checks.append({"ok": conexo, "texto": (
        "Rede conexa (sem barras ilhadas)" if conexo else
        "Rede com barras ilhadas — Jacobiano singular")})

    kv_of = {b["id"]: b.get("kv") for b in barras}
    sem_kv = any(not (b.get("kv") and b["kv"] > 0) for b in barras)
    if sem_kv:
        checks.append({"ok": False, "warn": True,
                       "texto": "Defina o nível de tensão (kV) de todas as barras"})
    else:
        probs = []
        for r in ramos:
            a, b = kv_of.get(r["de"]), kv_of.get(r["para"])
            if a is None or b is None:
                continue
            eh_linha = r.get("ligacao", "linha") == "linha"
            dif = abs(a - b) > 1e-6
            if eh_linha and dif:
                probs.append(f"Linha {r['de']}→{r['para']}: níveis diferentes "
                             f"({a} / {b} kV)")
            elif not eh_linha and not dif:
                probs.append(f"Transformador {r['de']}→{r['para']}: mesmo nível "
                             f"nos dois lados ({a} kV)")
        if not probs:
            checks.append({"ok": True,
                           "texto": "Níveis de tensão consistentes com os ramos"})
        else:
            for p in probs:
                checks.append({"ok": False, "warn": True, "texto": p})
    return checks


def eh_valido(barras, ramos) -> bool:
    """``True`` se nenhum check bloqueante (não-warn) falhou."""
    return bool(barras) and all(c["ok"] for c in validar(barras, ramos)
                                if not c.get("warn"))


# ------------------------------------------------------------- cores / canvas
def cor_tipo(t):
    """(bg, fg, borda) do nó por tipo de barra — igual ao ``corTipo`` do modelo."""
    if t == 3:
        return ("#1f2937", "#fff", "#1f2937")
    if t == 2:
        return (ACCENT, "#fff", ACCENT)
    return ("#fff", "#1f2430", "#cdd3de")


def cor_v(v):
    """Cor da barra por |V| (verde→vermelho) — igual ao ``corV`` do modelo."""
    x = max(0.0, min(1.0, (float(v) - 0.93) / 0.07))
    return f"hsl({x * 130:.0f},62%,46%)"


def cor_tipo_texto(t):
    return _COR_TIPO_TXT.get(t, "#2b6cf0")


def rot_tipo(t):
    return _ROT_TIPO.get(t, "PQ")


def render_canvas(barras, ramos, *, modo="editar", resultado=None, curto=None,
                  sel_kind=None, sel_id=None, ligar_ativo=False, ligar_de=None,
                  mostrar_rotulos=True) -> str:
    """HTML do diagrama (camada SVG + nós absolutos), colorido conforme o modo."""
    W, H = 860, 480
    mb = _mapa(barras)
    res = resultado if (modo == "fluxo" and resultado and resultado.get("barras")) else None
    cu = curto if (modo == "curto" and curto and not curto.get("erro")) else None
    show_flux = res is not None
    show_curto = cu is not None
    editable = modo == "editar"
    sbase = float(res["Sbase"]) if res else 100.0
    res_barra = {b["id"]: b for b in (res["barras"] if res else [])}
    res_ramo = {(rr["de"], rr["para"]): rr for rr in (res["ramos"] if res else [])}

    linhas: list[str] = []
    for r in ramos:
        a, b = mb.get(r["de"]), mb.get(r["para"])
        if not a or not b:
            continue
        ax, ay, bx, by = a["x"], a["y"], b["x"], b["y"]
        sel = editable and sel_kind == "ramo" and sel_id == r["id"]
        stroke = ACCENT if sel else ("#8893a8" if show_flux else "#9aa3b8")
        linhas.append(f'<line x1="{ax:.0f}" y1="{ay:.0f}" x2="{bx:.0f}" y2="{by:.0f}" '
                      f'stroke="{stroke}" stroke-width="{3 if sel else 2}"/>')
        if editable:
            linhas.append(f'<line data-rid="{r["id"]}" x1="{ax:.0f}" y1="{ay:.0f}" '
                          f'x2="{bx:.0f}" y2="{by:.0f}" stroke="transparent" '
                          f'stroke-width="14" style="cursor:pointer;pointer-events:stroke"/>')
        mx, my = (ax + bx) / 2, (ay + by) / 2
        lig = r.get("ligacao", "linha")
        eh_trafo = bool(lig and lig != "linha")
        rr = res_ramo.get((r["de"], r["para"]))
        if eh_trafo:
            dxv, dyv = bx - ax, by - ay
            ln = math.hypot(dxv, dyv) or 1
            ux, uy = dxv / ln, dyv / ln
            col = ACCENT if sel else ROXO
            linhas.append(f'<circle cx="{mx - ux * 8:.1f}" cy="{my - uy * 8:.1f}" r="8.5" '
                          f'fill="#fff" stroke="{col}" stroke-width="2.2"/>')
            linhas.append(f'<circle cx="{mx + ux * 8:.1f}" cy="{my + uy * 8:.1f}" r="8.5" '
                          f'fill="#fff" stroke="{col}" stroke-width="2.2"/>')
            if editable:
                linhas.append(f'<text x="{mx:.0f}" y="{my - 15:.0f}" text-anchor="middle" '
                              f'font-size="9.5" font-weight="700" font-family="{MONO}" '
                              f'fill="{ROXO}">{lig}</text>')
        if show_flux and rr:
            pij, qij = rr["P_ij"] * sbase, rr["Q_ij"] * sbase
            linhas.append(f'<rect x="{mx - 38:.0f}" y="{my - 15:.0f}" width="76" height="30" '
                          f'rx="6" fill="#ffffff" stroke="#e0e3e9"/>')
            linhas.append(f'<text x="{mx:.0f}" y="{my - 2:.0f}" text-anchor="middle" '
                          f'font-size="10.5" font-weight="600" font-family="{MONO}" '
                          f'fill="#1f2430">{fmt(pij, 1)} MW</text>')
            linhas.append(f'<text x="{mx:.0f}" y="{my + 10:.0f}" text-anchor="middle" '
                          f'font-size="9.5" font-family="{MONO}" fill="#8a909c">'
                          f'{fmt(qij, 1)} Mvar</text>')
        elif editable and mostrar_rotulos and not eh_trafo:
            linhas.append(f'<rect x="{mx - 26:.0f}" y="{my - 9:.0f}" width="52" height="17" '
                          f'rx="5" fill="#ffffff" stroke="#e6e8ec"/>')
            linhas.append(f'<text x="{mx:.0f}" y="{my + 3:.0f}" text-anchor="middle" '
                          f'font-size="10" font-family="{MONO}" fill="#5b6270">'
                          f'x={fmt(float(r.get("x", 0)), 2)}</text>')

    nos: list[str] = []
    for b in barras:
        rb = res_barra.get(b["id"])
        faulted = show_curto and b["id"] == cu["barra"]
        op = 1.0
        if faulted:
            bg, fg, bd = "#d4453b", "#fff", "#b5322a"
        elif show_flux and rb:
            bg = cor_v(rb["V"])
            fg, bd = "#fff", bg
        else:
            bg, fg, bd = cor_tipo(b.get("tipo", 1))
            if show_curto:
                op = 0.5
        seln = editable and sel_kind == "barra" and sel_id == b["id"]
        ligde = editable and ligar_ativo and ligar_de == b["id"]
        wide = bool(show_flux and rb)
        if faulted:
            sub = (f'<div style="font-size:11px;font-weight:700;font-family:{MONO};'
                   f'margin-top:2px">If = {fmt(cu["Ika"], 1)} kA</div>')
        elif show_flux and rb:
            sub = (f'<div style="font-size:11px;font-weight:600;font-family:{MONO};'
                   f'margin-top:2px">{fmt(rb["V"], 3)} pu · {fmt(rb["theta_deg"], 1)}°</div>'
                   f'<div style="font-size:9.5px;font-family:{MONO};opacity:.92;'
                   f'margin-top:1px">P {fmt(rb["P"] * sbase, 0)} · '
                   f'Q {fmt(rb["Q"] * sbase, 0)}</div>')
        else:
            sub = (f'<div style="font-size:10px;font-weight:600;opacity:.7;margin-top:1px;'
                   f'letter-spacing:.4px">{rot_tipo(b.get("tipo", 1)).upper()}</div>')
        borda = ACCENT if seln else ("#e08a16" if ligde else ("#fff" if faulted else bd))
        if faulted:
            sombra = "0 0 0 4px rgba(212,69,59,.22),0 6px 18px rgba(212,69,59,.3)"
        elif seln:
            sombra = f"0 0 0 3px {ACCENT}33,0 6px 16px rgba(16,24,40,.16)"
        else:
            sombra = "0 3px 10px rgba(16,24,40,.12)"
        interativo = editable or modo == "curto"
        cursor = "grab" if interativo else "default"
        arraste = ' data-drag="1"' if interativo else ""
        z = 3 if (seln or faulted) else 2
        w = 124 if wide else 112
        nos.append(
            f'<div data-bid="{b["id"]}"{arraste} style="position:absolute;left:{b["x"]:.0f}px;'
            f'top:{b["y"]:.0f}px;transform:translate(-50%,-50%);width:{w}px;padding:9px 11px;'
            f'border-radius:11px;background:{bg};color:{fg};opacity:{op};'
            f'border:2px solid {borda};box-shadow:{sombra};cursor:{cursor};user-select:none;'
            f'text-align:left;z-index:{z}">'
            f'<div style="display:flex;align-items:center;gap:6px">'
            f'<span style="width:18px;height:18px;border-radius:5px;'
            f'background:rgba(127,127,127,.18);display:inline-flex;align-items:center;'
            f'justify-content:center;font-size:11px;font-weight:700;font-family:{MONO}">'
            f'{b["id"]}</span>'
            f'<span style="font-size:12.5px;font-weight:600;white-space:nowrap;'
            f'overflow:hidden;text-overflow:ellipsis">{b.get("nome", "")}</span></div>'
            f'{sub}</div>')

    return (f'<div id="es-canvas" style="position:relative;width:{W}px;height:{H}px">'
            f'<svg width="{W}" height="{H}" style="position:absolute;inset:0;overflow:visible;'
            f'pointer-events:none">{"".join(linhas)}</svg>{"".join(nos)}</div>')
