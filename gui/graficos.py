"""Visualizações de resultado em **SVG puro** (strings) — espelham o design.

Funções puras (sem NiceGUI, testáveis headless) que reproduzem os SVGs do
``modelo/``: perfil de tensão, fasores das correntes de fase, contribuições para
a falta e a matriz Zbus. Devolvem HTML/SVG pronto para ``ui.html``.
"""
from __future__ import annotations

import math

from gui.campos import fmt
from gui.diagrama import MONO, cor_v

# Cores das fases A/B/C (iguais ao modelo).
_COR_FASE = ("#2b6cf0", "#1f9d57", "#e08a16")


def perfil_tensao_svg(resultado) -> str:
    """Barras de |V| por barra (mini gráfico do painel de fluxo)."""
    if not resultado or not resultado.get("barras"):
        return ""
    bs = resultado["barras"]
    n = len(bs)
    W, H, padL, padB, padT = 300, 170, 32, 24, 8
    bw = (W - padL - 10) / n if n else 0
    vmin, vmax = 0.90, 1.06

    def yof(v):
        return padT + (1 - (v - vmin) / (vmax - vmin)) * (H - padT - padB)

    els = []
    for g in (0.95, 1.0, 1.05):
        col = "#cdd3de" if g == 1.0 else "#eef0f3"
        dash = "4 3" if g == 1.0 else "0"
        els.append(f'<line x1="{padL}" y1="{yof(g):.1f}" x2="{W - 4}" y2="{yof(g):.1f}" '
                   f'stroke="{col}" stroke-width="1" stroke-dasharray="{dash}"/>')
        els.append(f'<text x="4" y="{yof(g) + 3:.1f}" font-size="9" font-family="{MONO}" '
                   f'fill="#9aa3b8">{g:.2f}</text>')
    for i, b in enumerate(bs):
        x = padL + i * bw + 4
        y = yof(b["V"])
        els.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw - 8:.1f}" '
                   f'height="{(H - padB) - y:.1f}" rx="3" fill="{cor_v(b["V"])}"/>')
        els.append(f'<text x="{x + (bw - 8) / 2:.1f}" y="{H - padB + 12}" text-anchor="middle" '
                   f'font-size="9.5" font-family="{MONO}" fill="#6b7280">{b["id"]}</text>')
    return (f'<svg width="100%" viewBox="0 0 {W} {H}" style="display:block">'
            f'{"".join(els)}</svg>')


def fasores_svg(curto) -> str:
    """Diagrama polar das correntes de fase Ia/Ib/Ic."""
    if not curto or curto.get("erro") or "fases" not in curto:
        return ""
    W, H, cx, cy, R = 300, 260, 150, 130, 96
    f = curto["fases"]
    phs = [("A", f["a"], _COR_FASE[0]), ("B", f["b"], _COR_FASE[1]),
           ("C", f["c"], _COR_FASE[2])]
    maxm = max([math.hypot(z[0], z[1]) for _, z, _ in phs] + [1e-9])
    els = [
        f'<circle cx="{cx}" cy="{cy}" r="{R * 0.5:.0f}" fill="none" stroke="#eef0f3" stroke-width="1"/>',
        f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#eef0f3" stroke-width="1"/>',
        f'<line x1="{cx - R - 12}" y1="{cy}" x2="{cx + R + 12}" y2="{cy}" stroke="#e0e3e9" stroke-width="1"/>',
        f'<line x1="{cx}" y1="{cy - R - 12}" x2="{cx}" y2="{cy + R + 12}" stroke="#e0e3e9" stroke-width="1"/>',
    ]
    for n, z, c in phs:
        m = math.hypot(z[0], z[1])
        if m < 1e-6:
            continue
        ang = math.atan2(z[1], z[0])
        ln = R * m / maxm
        x, y = cx + ln * math.cos(ang), cy - ln * math.sin(ang)
        tx = x + (8 if x >= cx else -8)
        ty = y + (13 if y >= cy else -7)
        anchor = "start" if x >= cx else "end"
        els.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" stroke="{c}" '
                   f'stroke-width="2.5" stroke-linecap="round"/>')
        els.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="{c}"/>')
        els.append(f'<text x="{tx:.1f}" y="{ty:.1f}" font-size="11.5" font-weight="700" '
                   f'font-family="{MONO}" fill="{c}" text-anchor="{anchor}">{n}</text>')
    return (f'<svg width="100%" viewBox="0 0 {W} {H}" style="display:block;margin:4px 0">'
            f'{"".join(els)}</svg>')


def contribuicoes_svg(curto) -> str:
    """Barras horizontais das contribuições por elemento."""
    if not curto or curto.get("erro") or not curto.get("contrib"):
        return ""
    cs = curto["contrib"]
    mx = max([c["frac"] for c in cs] + [1e-9])
    linhas = []
    for c in cs:
        cor = "#7c5cd6" if c.get("fonte") else "#2b6cf0"
        pct = round(c["frac"] * 100)
        linhas.append(
            '<div>'
            '<div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:5px">'
            f'<span style="color:#374151;font-weight:500">{c["rotulo"]}</span>'
            f'<span style="font-family:{MONO};color:#6b7280">{fmt(c["ka"], 2)} kA · {pct}%</span></div>'
            '<div style="height:9px;border-radius:5px;background:#eef0f3;overflow:hidden">'
            f'<div style="height:100%;width:{c["frac"] / mx * 100:.1f}%;border-radius:5px;'
            f'background:{cor}"></div></div></div>')
    return f'<div style="display:flex;flex-direction:column;gap:13px">{"".join(linhas)}</div>'


def matriz_zbus_svg(curto, seq: str = "pos") -> str:
    """Tabela da matriz Zbus (sequência positiva ou zero), barra de falta destacada."""
    if not curto or curto.get("erro"):
        return ""
    M = curto.get("Z0bus") if seq == "zero" else curto.get("Zbus")
    if not M:
        return ('<div style="font-size:12.5px;color:#9aa3b8;padding:14px 2px">'
                'Rede de sequência zero singular (sem caminho de terra) — '
                'sem matriz a exibir.</div>')
    barras = curto.get("barras_mat", [])
    kf = curto.get("kfault", -1)
    accent = "#7c5cd6" if seq == "zero" else "#2b6cf0"
    hi_bg = "#f6f3fc" if seq == "zero" else "#eef3fe"

    def fmtz(c):
        re, im = c
        sg = "+j" if im >= 0 else "−j"
        return f"{fmt(re, 3)}{sg}{fmt(abs(im), 3)}"

    head = ['<td style="padding:5px 8px;border-bottom:1px solid #e6e8ec"></td>']
    for j, b in enumerate(barras):
        col = accent if j == kf else "#8a909c"
        head.append(f'<td style="padding:5px 8px;text-align:right;font-family:{MONO};'
                    f'font-size:11px;font-weight:700;color:{col};'
                    f'border-bottom:1px solid #e6e8ec">{b["id"]}</td>')
    rows = []
    for i, b in enumerate(barras):
        lblcol = accent if i == kf else "#8a909c"
        cells = [f'<td style="padding:5px 8px;font-family:{MONO};font-size:11px;font-weight:700;'
                 f'color:{lblcol};border-bottom:1px solid #f0f1f4;border-right:1px solid #eef0f3;'
                 f'position:sticky;left:0;background:#fff">{b["id"]}</td>']
        for j in range(len(barras)):
            hi = i == kf or j == kf
            diag = i == j
            color = accent if diag else "#374151"
            weight = 700 if diag else 400
            bg = hi_bg if hi else "transparent"
            cells.append(f'<td style="padding:5px 8px;text-align:right;white-space:nowrap;'
                         f'font-family:{MONO};font-size:11px;color:{color};font-weight:{weight};'
                         f'background:{bg};border-bottom:1px solid #f0f1f4">{fmtz(M[i][j])}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return ('<div style="overflow-x:auto;border:1px solid #eef0f3;border-radius:9px">'
            '<table style="border-collapse:collapse;width:100%">'
            f'<thead><tr>{"".join(head)}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def matriz_ybus_svg(barras, ramos, seq: str = "pos", estudo: str = "fluxo") -> str:
    """Tabela da matriz Ybus de barra, diagonal destacada, construída ao vivo.

    ``estudo='fluxo'`` → Ybus da rede (seq. positiva, sem fontes). ``'falta'`` →
    rede + reatância das fontes, na sequência ``seq`` ('pos'/'zero'). Espelha
    :func:`matriz_zbus_svg`, mas sem inverter (não falha em rede incompleta).
    """
    if not barras:
        return ""
    from gui.solver import (  # import tardio: não acopla graficos ao núcleo
        montar_ybus,
        montar_ybus0_falta,
        montar_ybus1_falta,
    )

    ordenadas = sorted(barras, key=lambda b: b["id"])
    try:
        if estudo == "falta":
            M = montar_ybus0_falta(barras, ramos) if seq == "zero" else montar_ybus1_falta(barras, ramos)
        else:
            M = montar_ybus(barras, ramos)  # fluxo: rede de seq. positiva
    except ZeroDivisionError:
        return ('<div style="font-size:12.5px;color:#9aa3b8;padding:14px 2px">'
                'Há ramo com z = 0 — defina r/x para ver a matriz Ybus.</div>')
    accent = "#7c5cd6" if (estudo == "falta" and seq == "zero") else "#2b6cf0"

    def fmty(c):
        sg = "+j" if c.imag >= 0 else "−j"
        return f"{fmt(c.real, 3)}{sg}{fmt(abs(c.imag), 3)}"

    head = ['<td style="padding:5px 8px;border-bottom:1px solid #e6e8ec"></td>']
    for b in ordenadas:
        head.append(f'<td style="padding:5px 8px;text-align:right;font-family:{MONO};'
                    f'font-size:11px;font-weight:700;color:#8a909c;'
                    f'border-bottom:1px solid #e6e8ec">{b["id"]}</td>')
    rows = []
    for i, b in enumerate(ordenadas):
        cells = [f'<td style="padding:5px 8px;font-family:{MONO};font-size:11px;font-weight:700;'
                 f'color:#8a909c;border-bottom:1px solid #f0f1f4;border-right:1px solid #eef0f3;'
                 f'position:sticky;left:0;background:#fff">{b["id"]}</td>']
        for j in range(len(ordenadas)):
            diag = i == j
            color = accent if diag else "#374151"
            weight = 700 if diag else 400
            cells.append(f'<td style="padding:5px 8px;text-align:right;white-space:nowrap;'
                         f'font-family:{MONO};font-size:11px;color:{color};font-weight:{weight};'
                         f'border-bottom:1px solid #f0f1f4">{fmty(M[i][j])}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return ('<div style="overflow-x:auto;border:1px solid #eef0f3;border-radius:9px">'
            '<table style="border-collapse:collapse;width:100%">'
            f'<thead><tr>{"".join(head)}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')
