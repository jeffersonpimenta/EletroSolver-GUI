"""Workspace unificado (Editar/Fluxo/Curto) — espelha o ``modelo/`` (157-499).

Builders chamados pelas regiões ``@ui.refreshable`` do :class:`gui.workspace.Workspace`:
``toolbar``, ``sob_canvas`` (tabelas de fluxo / detalhe de curto), ``painel_topo``
e ``painel_extra`` (painel direito por modo) e ``canvas_hint`` (rodapé).
"""
from __future__ import annotations

import math

from nicegui import ui

from gui import diagrama, graficos
from gui.campos import fmt, rad_para_graus
from gui.componentes import botao_estilo, campo, campo_texto, chip, rotulo, selecao, stat_row
from gui.layout import (
    ACCENT,
    CARD_BOX,
    CARTAO_STAT,
    INP_OFF,
    ROXO,
    STAT_LABEL,
    STAT_VAL,
    TD_L,
    TD_R,
    TH_L,
    TH_R,
    TH_ROW,
    TOOL_BTN,
)

# Rótulos / notas das ligações de transformador (modelo 1303-1313).
LIG_LABELS = {
    "linha": "Linha / cabo", "YNyn": "Trafo YNyn (Yg–Yg)", "Dyn": "Trafo Dyn (Δ–Yg)",
    "YNd": "Trafo YNd (Yg–Δ)", "Dd": "Trafo Dd (Δ–Δ)", "Yy": "Trafo Yy (Y–Y)",
    "Yyn": "Trafo Yyn (Y–Yg)", "YNy": "Trafo YNy (Yg–Y)",
}
LIG_NOTAS = {
    "linha": "Linha de transmissão — conduz a sequência zero pela própria z₀.",
    "YNyn": "Estrela-aterrada nos dois lados — conduz a sequência zero entre as barras.",
    "Dyn": "Δ na origem, estrela-aterrada no destino — aterra a seq. zero na barra destino.",
    "YNd": "Estrela-aterrada na origem, Δ no destino — aterra a seq. zero na barra origem.",
    "Dd": "Δ–Δ — bloqueia totalmente a sequência zero.",
    "Yy": "Estrela–estrela sem aterramento — bloqueia a sequência zero.",
    "Yyn": "Estrela / estrela-aterrada — bloqueia (sem retorno do outro lado).",
    "YNy": "Estrela-aterrada / estrela — bloqueia (sem retorno do outro lado).",
}
_USA_Z0 = ("linha", "YNyn", "Dyn", "YNd")
_TIPO_NOME = {"tri": "Falta trifásica (3φ)", "mono": "Falta monofásica (1φ-terra)",
              "bi": "Falta bifásica (2φ)", "biT": "Falta bifásica-terra"}
_COR_FASE = ("#2b6cf0", "#1f9d57", "#e08a16")

_IC_MAIS = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14"/></svg>')
_IC_LIGAR = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
             '<path d="M9 17H7A5 5 0 0 1 7 7h2M15 7h2a5 5 0 0 1 0 10h-2M8 12h8"/></svg>')
_IC_ORG = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
           'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
           '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>'
           '<rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>')

_EXCLUIR = ("border:none;background:#fdecec;color:#d4453b;font-size:12px;font-weight:500;"
            "padding:5px 10px;border-radius:7px;cursor:pointer")
_SEG_BASE = ("flex:1;padding:7px 0;border-radius:7px;border:1px solid #dde1e7;font-size:12px;"
             "font-weight:600;cursor:pointer;font-family:inherit;text-align:center")
_NOTA = "font-size:11.5px;color:#9aa3b8;margin-top:10px;line-height:1.5"


# ----------------------------------------------------------------- utilidades
def _label(txt, cor="#8a909c"):
    return (f'<div style="font-size:11px;font-weight:600;letter-spacing:1px;color:{cor};'
            f'margin-bottom:14px">{txt}</div>')


def _mag(z):
    return math.hypot(z[0], z[1])


def _ang(z):
    return math.degrees(math.atan2(z[1], z[0]))


def _zfmt(z, c=3):
    sg = "+ j" if z[1] >= 0 else "− j"
    return f"{fmt(z[0], c)} {sg}{fmt(abs(z[1]), c)}"


def canvas_hint(ws) -> str:
    if ws.modo == "editar":
        if ws.ligar_ativo:
            return ("Modo Ligar: clique a segunda barra para criar o ramo." if ws.ligar_de
                    else "Modo Ligar: clique na primeira barra.")
        return ("Arraste para reposicionar · clique para editar "
                "(cosmético, não altera o cálculo).")
    if ws.modo == "fluxo":
        return ("Tensões (pu/°) e injeções P/Q nos nós; trânsito P + jQ nos ramos."
                if ws.proj.resultado_fluxo else
                "Defina os parâmetros e clique em Calcular para sobrepor o fluxo.")
    cu = ws.proj.resultado_curto
    if cu and not cu.get("erro"):
        return ("Barra em falta destacada em vermelho; corrente de curto exibida no nó. "
                "Clique numa barra para mudar a falta.")
    return "Escolha a barra (ou clique no diagrama) e o tipo de falta, depois calcule."


# --------------------------------------------------------------------- toolbar
def _modo_seg(ws, m, rotulo_btn, acao):
    ativo = ws.modo == m
    base = ("padding:6px 15px;border:none;border-radius:7px;font-size:12.5px;font-weight:600;"
            "cursor:pointer;font-family:inherit;")
    estilo = base + ("background:#fff;color:#1f2430;box-shadow:0 1px 3px rgba(16,24,40,.13)"
                     if ativo else "background:transparent;color:#8a909c")
    botao_estilo(rotulo_btn, estilo, acao)


def toolbar(ws) -> None:
    with ui.element("div").style("display:flex;align-items:center;gap:10px;padding:11px 22px;"
                                 "border-bottom:1px solid #e6e8ec;background:#fafbfc;flex-wrap:wrap"):
        with ui.element("div").style("display:inline-flex;background:#eceef1;border-radius:9px;"
                                     "padding:3px;gap:2px"):
            _modo_seg(ws, "editar", "Editar", ws.nav_editar)
            _modo_seg(ws, "fluxo", "Fluxo", ws.nav_fluxo)
            _modo_seg(ws, "curto", "Curto", ws.nav_curto)
        if ws.modo == "editar":
            ui.html('<div style="width:1px;height:22px;background:#e2e5ea"></div>')
            botao_estilo(_IC_MAIS + " Barra", TOOL_BTN, ws.add_barra)
            lig = TOOL_BTN + (f";background:{ACCENT};color:#fff;border-color:{ACCENT}"
                              if ws.ligar_ativo else "")
            botao_estilo(_IC_LIGAR + " Ligar", lig, ws.toggle_ligar)
            botao_estilo(_IC_ORG + " Organizar", TOOL_BTN, ws.auto_organizar)
        nb, nr = len(ws.proj.barras), len(ws.proj.ramos)
        selo = ""
        res = ws.proj.resultado_fluxo
        if ws.modo == "fluxo" and res:
            conv = res.get("convergiu")
            est = ("font-size:11.5px;font-weight:600;padding:3px 9px;border-radius:6px;"
                   + ("background:#e7f6ec;color:#1f9d57" if conv else "background:#fdecec;color:#d4453b"))
            selo = f'<span style="{est}">● {"convergiu" if conv else "falhou"}</span>'
        ui.html('<div style="margin-left:auto;display:flex;align-items:center;gap:12px;'
                "font-size:12.5px;color:#8a909c;font-family:'IBM Plex Mono',monospace\">"
                f'<span>{nb}b · {nr}r</span>{selo}</div>')


# --------------------------------------------------------------- sob o canvas
def sob_canvas(ws) -> None:
    res = ws.proj.resultado_fluxo
    cu = ws.proj.resultado_curto
    if ws.modo == "editar":
        _matriz_ybus(ws)
    elif ws.modo == "fluxo" and res and res.get("barras"):
        _fluxo_tabelas(ws, res)
    elif ws.modo == "curto" and cu and not cu.get("erro"):
        _curto_detalhe(ws, cu)


def _matriz_ybus(ws) -> None:
    """Matriz de admitância de barra (Ybus) que evolui conforme se monta o sistema.

    Seletor **Fluxo / Falta**: em *Fluxo* mostra a Ybus da rede (seq. positiva,
    sem fontes — a matriz nodal do fluxo); em *Falta* mostra a rede + reatância
    das fontes, com seletor de sequência **+/0** (a Zbus do curto é a inversa).
    Atualiza ao vivo (vive na região ``sob``).
    """
    if not ws.proj.barras:
        return
    n = len(ws.proj.barras)
    falta = ws.mat_estudo == "falta"
    seq = ws.mat_seq if falta else "pos"
    sub = "rede da falta (com fontes)" if falta else "rede do fluxo (sem fontes)"
    with ui.element("div").style("margin-top:18px"):
        with ui.element("div").style(CARD_BOX):
            with ui.element("div").style("display:flex;align-items:center;justify-content:space-between;"
                                         "gap:12px;margin-bottom:12px;flex-wrap:wrap"):
                ui.html('<div><div style="font-weight:600;font-size:13.5px">'
                        'Matriz de admitância de barra · Ybus</div>'
                        f'<div style="font-size:12px;color:#8a909c;margin-top:2px">{n}×{n} · '
                        f'em pu na base {fmt(ws.sbase, 0)} MVA · {sub}</div></div>')
                with ui.element("div").style("display:flex;flex-direction:column;gap:6px;width:220px"):
                    with ui.element("div").style("display:flex;gap:6px"):
                        _seg_estudo(ws, "fluxo", "Fluxo", ACCENT)
                        _seg_estudo(ws, "falta", "Falta", ROXO)
                    if falta:
                        with ui.element("div").style("display:flex;gap:6px"):
                            _seg_mat(ws, "pos", "Seq +", ACCENT)
                            _seg_mat(ws, "zero", "Seq 0", ROXO)
            ui.html(graficos.matriz_ybus_svg(ws.proj.barras, ws.proj.ramos, seq, ws.mat_estudo))
            ui.html(f'<div style="{_NOTA}">{_nota_ybus(ws.mat_estudo, seq)}</div>')


def _seg_estudo(ws, est, rotulo_btn, cor):
    ativo = ws.mat_estudo == est
    estilo = (f"flex:1;padding:6px 0;border-radius:7px;border:1px solid "
              f"{cor if ativo else '#dde1e7'};background:{cor if ativo else '#fff'};"
              f"color:{'#fff' if ativo else '#6b7280'};font-size:12px;font-weight:600;"
              f"cursor:pointer;font-family:inherit")
    botao_estilo(rotulo_btn, estilo, lambda est=est: ws.set_mat_estudo(est))


def _nota_ybus(estudo, seq):
    if estudo == "falta" and seq == "zero":
        return ("Ybus de sequência zero da rede de falta: rede roteada pelas ligações dos trafos "
                "(linha/YNyn conduzem; Dyn/YNd aterram um lado; Dd/Yy/Yyn/YNy bloqueiam) mais o "
                "aterramento das fontes (1/(j·X₀)). A Z₀bus do curto é a inversa desta matriz.")
    if estudo == "falta":
        return ("Ybus de sequência positiva da rede de falta: rede π + a reatância subtransitória "
                "das fontes (1/(j·X″d)) na diagonal das barras Slack/PV. A Zbus do curto é a "
                "inversa desta matriz.")
    return ("Ybus de sequência positiva da rede de fluxo (Y₁ = estampagem π com tap), sem fontes "
            "— os geradores entram como injeção P/V, não na matriz. É a matriz nodal que alimenta "
            "o fluxo de potência.")


def _fluxo_tabelas(ws, res) -> None:
    sb = res["Sbase"]
    with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:18px"):
        with ui.element("div").style(CARD_BOX + ";padding-bottom:8px"):
            ui.html('<div style="font-weight:600;font-size:13.5px;margin-bottom:10px">'
                    'Resultado por barra</div>' + _tab_barras(res, sb))
        with ui.element("div").style(CARD_BOX + ";padding-bottom:8px"):
            with ui.element("div").style("display:flex;justify-content:space-between;"
                                         "align-items:center;margin-bottom:10px"):
                ui.html('<div style="font-weight:600;font-size:13.5px">'
                        'Trânsito e perdas por ramo</div>')
                botao_estilo("Exportar JSON", TOOL_BTN + ";padding:5px 9px;font-size:11.5px",
                             ws.exportar_resultado)
            ui.html(_tab_ramos(res, sb))


def _tab_barras(res, sb) -> str:
    linhas = []
    for b in res["barras"]:
        vcor = diagrama.cor_v(b["V"])
        linhas.append(
            f'<tr style="border-bottom:1px solid #f0f1f4">'
            f'<td style="{TD_L}"><span style="font-family:\'IBM Plex Sans\';font-weight:600">'
            f'{b["id"]} · {b["nome"]}</span></td>'
            f'<td style="{TD_R}"><span style="color:{vcor};font-weight:600">{fmt(b["V"], 4)}</span></td>'
            f'<td style="{TD_R}">{fmt(b["theta_deg"], 2)}</td>'
            f'<td style="{TD_R}">{fmt(b["P"] * sb, 1)}</td>'
            f'<td style="{TD_R}">{fmt(b["Q"] * sb, 1)}</td></tr>')
    return (f'<table style="width:100%;border-collapse:collapse;'
            "font-family:'IBM Plex Mono',monospace;font-size:12px\">"
            f'<thead><tr style="{TH_ROW}"><th style="{TH_L}">Barra</th><th style="{TH_R}">|V|</th>'
            f'<th style="{TH_R}">θ°</th><th style="{TH_R}">P</th><th style="{TH_R}">Q</th></tr></thead>'
            f'<tbody>{"".join(linhas)}</tbody></table>')


def _tab_ramos(res, sb) -> str:
    linhas = []
    for r in res["ramos"]:
        par = r.get("n_paralelos", 1)
        marca = (f' <span style="font-size:10px;color:{ROXO};font-weight:600" '
                 f'title="{par} ramos paralelos — trânsito somado">∥{par}</span>'
                 if par > 1 else "")
        linhas.append(
            f'<tr style="border-bottom:1px solid #f0f1f4">'
            f'<td style="{TD_L}"><span style="font-family:\'IBM Plex Sans\';font-weight:600">'
            f'{r["de"]} → {r["para"]}{marca}</span></td>'
            f'<td style="{TD_R}">{fmt(r["P_ij"] * sb, 1)}</td>'
            f'<td style="{TD_R}">{fmt(r["Q_ij"] * sb, 1)}</td>'
            f'<td style="{TD_R}">{fmt(r["S_ij"] * sb, 1)}</td>'
            f'<td style="{TD_R}"><span style="color:#d4453b">{fmt(r["P_loss"] * sb, 2)}</span></td></tr>')
    return (f'<table style="width:100%;border-collapse:collapse;'
            "font-family:'IBM Plex Mono',monospace;font-size:12px\">"
            f'<thead><tr style="{TH_ROW}"><th style="{TH_L}">Ramo</th><th style="{TH_R}">P_ij</th>'
            f'<th style="{TH_R}">Q_ij</th><th style="{TH_R}">|S|</th>'
            f'<th style="{TH_R}">Perda P</th></tr></thead><tbody>{"".join(linhas)}</tbody></table>')


def _curto_detalhe(ws, cu) -> None:
    with ui.element("div").style("margin-top:18px;display:flex;flex-direction:column;gap:16px"):
        kv = cu.get("kv") or "—"
        ui.html('<div style="display:flex;align-items:center;gap:10px">'
                f'<span style="font-weight:600;font-size:15px">{_TIPO_NOME.get(cu["tipo"], "")}</span>'
                '<span style="font-size:11px;color:#7c5cd6;background:#f3f0fb;border-radius:6px;'
                f'padding:3px 10px;font-weight:600">barra {cu["barra"]} · {kv} kV</span></div>')

        with ui.element("div").style("display:grid;grid-template-columns:repeat(4,1fr);gap:14px"):
            _stat4("Corrente de falta", fmt(cu["Ika"], 2), "kA", ROXO)
            _stat4("Corrente (pu)", fmt(cu["Ipu"], 3), "")
            _stat4("Pot. de curto", fmt(cu["Scc"], 1), "MVA")
            with ui.element("div").style(CARTAO_STAT):
                ui.html(f'<div style="{STAT_LABEL}">Z Thévenin (pu)</div>'
                        '<div style="font-size:15px;font-weight:700;'
                        "font-family:'IBM Plex Mono';padding-top:9px\">"
                        f'{_zfmt(cu["Z1"])}</div>')

        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:16px"):
            with ui.element("div").style(CARD_BOX):
                ui.html('<div style="font-weight:600;font-size:13.5px;margin-bottom:2px">'
                        'Fasores das correntes de fase</div>' + graficos.fasores_svg(cu)
                        + '<div style="display:flex;gap:16px;justify-content:center;margin-top:2px">'
                        + _legenda_fase() + "</div>")
            with ui.element("div").style(CARD_BOX):
                ui.html('<div style="font-weight:600;font-size:13.5px;margin-bottom:14px">'
                        'Contribuições para a falta</div>' + graficos.contribuicoes_svg(cu)
                        + '<div style="font-size:11.5px;color:#9aa3b8;margin-top:14px;line-height:1.5">'
                        'Distribuição da corrente de sequência positiva pelos ramos incidentes '
                        'e pela fonte local.</div>')

        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:16px"):
            ui.html(f'<div style="{CARD_BOX};padding-bottom:8px">'
                    '<div style="font-weight:600;font-size:13.5px;margin-bottom:10px">'
                    'Componentes simétricas</div>' + _tab_seq(cu) + "</div>")
            ui.html(f'<div style="{CARD_BOX};padding-bottom:8px">'
                    '<div style="font-weight:600;font-size:13.5px;margin-bottom:10px">'
                    'Correntes de fase</div>' + _tab_fases(cu) + "</div>")

        ui.html(f'<div style="{CARD_BOX}"><div style="font-weight:600;font-size:13.5px;'
                'margin-bottom:6px">Memória de cálculo</div>'
                f'<div style="font-size:12.5px;color:#6b7280;line-height:1.6">{_descricao(cu)}</div>'
                "<div style=\"margin-top:13px;font-family:'IBM Plex Mono',monospace;font-size:12.5px;"
                'background:#f7f8fa;border:1px solid #eef0f3;border-radius:9px;padding:13px 15px;'
                f'color:#374151;line-height:1.7;white-space:pre-line">{_formula(cu)}</div></div>')

        _matriz(ws, cu)


def _stat4(label, valor, unidade, cor="#1f2430"):
    with ui.element("div").style(CARTAO_STAT):
        ui.html(f'<div style="{STAT_LABEL}">{label}</div>'
                f'<div style="{STAT_VAL};color:{cor}">{valor}'
                + (f'<span style="font-size:13px;font-weight:500;color:#8a909c;margin-left:5px">'
                   f'{unidade}</span>' if unidade else "") + "</div>")


def _legenda_fase():
    nomes = ("A", "B", "C")
    return "".join(
        f'<span style="display:flex;align-items:center;gap:6px;font-size:12px;color:#6b7280">'
        f'<span style="width:11px;height:11px;border-radius:3px;background:{_COR_FASE[i]}"></span>'
        f'Fase {nomes[i]}</span>' for i in range(3))


def _tab_seq(cu) -> str:
    seq = cu["seq"]
    dados = [("I₁ — positiva", seq["I1"]), ("I₂ — negativa", seq["I2"]), ("I₀ — zero", seq["I0"])]
    rows = "".join(
        f'<tr style="border-bottom:1px solid #f0f1f4"><td style="{TD_L}">'
        f'<span style="font-family:\'IBM Plex Sans\';font-weight:600">{nome}</span></td>'
        f'<td style="{TD_R}">{fmt(_mag(z), 3)}</td><td style="{TD_R}">{fmt(_ang(z), 1)}°</td></tr>'
        for nome, z in dados)
    return (f'<table style="width:100%;border-collapse:collapse;'
            "font-family:'IBM Plex Mono',monospace;font-size:12.5px\">"
            f'<thead><tr style="{TH_ROW}"><th style="{TH_L}">Sequência</th>'
            f'<th style="{TH_R}">|I| (pu)</th><th style="{TH_R}">ângulo</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def _tab_fases(cu) -> str:
    fases = cu["fases"]
    ib = cu.get("Ibase", 0.0)
    dados = [("A", fases["a"], _COR_FASE[0]), ("B", fases["b"], _COR_FASE[1]),
             ("C", fases["c"], _COR_FASE[2])]
    rows = "".join(
        f'<tr style="border-bottom:1px solid #f0f1f4"><td style="{TD_L}">'
        '<span style="display:inline-flex;align-items:center;gap:7px;'
        "font-family:'IBM Plex Sans';font-weight:600\">"
        f'<span style="width:9px;height:9px;border-radius:3px;background:{cor}"></span>Fase {nome}'
        f'</span></td><td style="{TD_R}">{fmt(_mag(z), 3)}</td>'
        f'<td style="{TD_R}">{fmt(_mag(z) * ib, 2)}</td>'
        f'<td style="{TD_R}">{fmt(_ang(z), 1)}°</td></tr>'
        for nome, z, cor in dados)
    return (f'<table style="width:100%;border-collapse:collapse;'
            "font-family:'IBM Plex Mono',monospace;font-size:12.5px\">"
            f'<thead><tr style="{TH_ROW}"><th style="{TH_L}">Fase</th><th style="{TH_R}">|I| (pu)</th>'
            f'<th style="{TH_R}">kA</th><th style="{TH_R}">ângulo</th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def _descricao(cu) -> str:
    if cu["tipo"] != "tri":
        return ("Faltas assimétricas combinam as redes de sequência positiva, negativa (Z₂ = Z₁) "
                "e zero. A rede de sequência zero é montada pelo tipo de ligação de cada ramo "
                "(linha/YNyn conduzem; Dyn/YNd aterram um lado; Dd/Yy/Yyn/YNy bloqueiam) e pelo "
                "aterramento das fontes. Tensão pré-falta plana de 1,0 pu e X″ = 0,1 pu nas barras "
                "de fonte.")
    return ("Corrente simétrica obtida da impedância de Thévenin na barra (diagonal da Zbus de "
            "sequência positiva), com tensão pré-falta plana de 1,0 pu e reatância subtransitória "
            "X″ = 0,1 pu nas barras de fonte (Slack/PV).")


def _formula(cu) -> str:
    z1, z0, seq = cu["Z1"], cu.get("Z0"), cu["seq"]
    z0txt = _zfmt(z0, 4) if z0 else "—"
    return (f"Z₁ = {_zfmt(z1, 4)} pu   (Z₂ = Z₁)\n"
            f"Z₀ = {z0txt} pu   (rede de seq. zero)\n"
            f"I₁ = {fmt(_mag(seq['I1']), 4)} ∠ {fmt(_ang(seq['I1']), 1)}° pu\n"
            f"If (fase) = {fmt(cu['Ipu'], 4)} pu = {fmt(cu['Ika'], 3)} kA   "
            f"(base {cu.get('kv', '—')} kV)")


def _matriz(ws, cu) -> None:
    dim = len(cu.get("barras_mat", []))
    sbase = cu.get("Sbase", 100.0)
    with ui.element("div").style(CARD_BOX):
        with ui.element("div").style("display:flex;align-items:center;justify-content:space-between;"
                                     "gap:12px;margin-bottom:12px;flex-wrap:wrap"):
            ui.html('<div><div style="font-weight:600;font-size:13.5px">'
                    'Matriz de impedância de barra · Zbus</div>'
                    f'<div style="font-size:12px;color:#8a909c;margin-top:2px">{dim}×{dim} · '
                    f'em pu na base {fmt(sbase, 0)} MVA</div></div>')
            with ui.element("div").style("display:flex;gap:6px;width:220px"):
                _seg_mat(ws, "pos", "Sequência +", ACCENT)
                _seg_mat(ws, "zero", "Sequência 0", ROXO)
        ui.html(graficos.matriz_zbus_svg(cu, ws.mat_seq))
        zkk = cu["Z0"] if (ws.mat_seq == "zero" and cu.get("Z0")) else cu["Z1"]
        ui.html('<div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:13px;font-size:12px;'
                "color:#5b6270;font-family:'IBM Plex Mono',monospace\">"
                f'<span>Barra em falta: <b style="color:#1f2430">{cu["barra"]}</b></span>'
                f'<span>Z<sub>kk</sub> (Thévenin): <b style="color:#1f2430">{_zfmt(zkk, 4)}</b>'
                '</span></div>'
                f'<div style="{_NOTA}">{_nota_mat(ws.mat_seq)}</div>')


def _seg_mat(ws, seq, rotulo_btn, cor):
    ativo = ws.mat_seq == seq
    estilo = (f"flex:1;padding:6px 0;border-radius:7px;border:1px solid "
              f"{cor if ativo else '#dde1e7'};background:{cor if ativo else '#fff'};"
              f"color:{'#fff' if ativo else '#6b7280'};font-size:12px;font-weight:600;"
              f"cursor:pointer;font-family:inherit")
    botao_estilo(rotulo_btn, estilo, lambda seq=seq: ws.set_mat_seq(seq))


def _nota_mat(seq):
    if seq == "zero":
        return ("Zbus de sequência zero (Z₀ = Y₀⁻¹). A diagonal Zₖₖ é a impedância de Thévenin de "
                "sequência zero vista da barra k; depende do roteamento das ligações dos "
                "transformadores.")
    return ("Zbus de sequência positiva (Z₁ = Y₁⁻¹), em pu na base do sistema. A diagonal Zₖₖ é a "
            "impedância de Thévenin que define a corrente de falta na barra k.")


# ----------------------------------------------------------- painel (topo)
def painel_topo(ws) -> None:
    if ws.modo == "editar":
        with ui.element("div").style("padding:18px 20px;border-bottom:1px solid #eef0f3"):
            ui.html(_label("EDIÇÃO"))
            sb, sr = ws.sel_barra(), ws.sel_ramo()
            if sb:
                _editor_barra(ws, sb)
            elif sr:
                _editor_ramo(ws, sr)
            else:
                ui.html('<div style="text-align:center;color:#9aa3b8;padding:24px 8px;'
                        'font-size:13px;line-height:1.6"><svg width="30" height="30" '
                        'viewBox="0 0 24 24" fill="none" stroke="#c5cad3" stroke-width="1.6" '
                        'style="margin-bottom:8px"><circle cx="9" cy="9" r="3"/>'
                        '<circle cx="17" cy="16" r="3"/><path d="M11.2 10.8 14.8 14"/></svg>'
                        '<div>Clique numa barra ou ramo<br>para editar seus parâmetros.</div></div>')
    elif ws.modo == "fluxo":
        with ui.element("div").style("padding:18px 20px;border-bottom:1px solid #eef0f3"):
            ui.html(_label("FLUXO DE POTÊNCIA", ACCENT))
            p = ws.proj.params_fluxo
            with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:10px"):
                with ui.element("div"):
                    campo("Tolerância", p.get("tolerancia", 1e-6), ws.set_tol, passo=1e-6)
                with ui.element("div"):
                    campo("Máx. iter.", p.get("max_iter", 100), ws.set_max_iter, passo=10)
                with ui.element("div"):
                    campo("Sbase (MVA)", p.get("Sbase", 100.0), ws.set_sbase, passo=10)
            label = ("Calculando…" if ws.calculando
                     else ("Recalcular" if ws.proj.resultado_fluxo else "Calcular fluxo"))
            estilo = (f"width:100%;margin-top:6px;padding:10px;border:none;border-radius:9px;"
                      f"background:{ACCENT};color:#fff;font-size:13.5px;font-weight:600;"
                      f"cursor:pointer;font-family:inherit")
            botao_estilo(label, estilo, ws.calcular_fluxo)
    else:
        _painel_curto(ws)


def _editor_barra(ws, sb) -> None:
    with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;"
                                 "margin-bottom:14px"):
        ui.html(f'<span style="font-weight:600;font-size:15px">Barra {sb["id"]}</span>')
        botao_estilo("Excluir", _EXCLUIR, ws.excluir_sel)
    campo_texto("Nome", sb.get("nome", ""), ws.set_nome)
    campo("Nível de tensão (kV)", sb.get("kv", 138.0), ws.set_kv, passo=0.1)
    _aspecto(ws)
    if ws.edit_aspecto == "fluxo":
        tipo = sb.get("tipo", 1)
        rotulo("Tipo de barramento")
        with ui.element("div").style("display:flex;gap:6px;margin-bottom:14px"):
            chip("PQ", tipo == 1, lambda: ws.set_tipo(1), ACCENT)
            chip("PV", tipo == 2, lambda: ws.set_tipo(2), ACCENT)
            chip("Slack", tipo == 3, lambda: ws.set_tipo(3), "#1f2937")
        can_v, can_p, can_q, can_th = tipo in (2, 3), tipo in (1, 2), tipo == 1, tipo == 3
        suf = " · resultado"
        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:10px"):
            with ui.element("div"):
                campo("V (pu)" if can_v else "V (pu)" + suf, sb.get("V", 1.0), ws.set_v,
                      passo=0.01, desabilitado=not can_v)
            with ui.element("div"):
                campo("θ (graus) · ref." if can_th else "θ (graus)" + suf,
                      round(rad_para_graus(sb.get("theta", 0.0)), 4), ws.set_theta_deg,
                      passo=0.1, desabilitado=not can_th)
            with ui.element("div"):
                campo("P (MW)" if can_p else "P (MW)" + suf,
                      round(sb.get("P", 0.0) * ws.sbase), ws.set_p_mw, passo=1,
                      desabilitado=not can_p)
            with ui.element("div"):
                campo("Q (MVAr)" if can_q else "Q (MVAr)" + suf,
                      round(sb.get("Q", 0.0) * ws.sbase), ws.set_q_mvar, passo=1,
                      desabilitado=not can_q)
        dica = {3: "Slack: especifica |V| e o ângulo de referência. P e Q são resultado do fluxo.",
                2: "PV: especifica P e |V|. Q (e θ) resultam do fluxo.",
                1: "PQ: especifica P e Q injetados. |V| e θ resultam do fluxo."}[tipo]
        ui.html(f'<div style="{_NOTA}">{dica}</div>')
    else:
        if sb.get("tipo") in (2, 3):
            with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:10px"):
                with ui.element("div"):
                    campo("X″d (pu)", sb.get("xd", 0.10), ws.set_xd, passo=0.01)
                with ui.element("div"):
                    campo("X₀ fonte (pu)", sb.get("xd0", 0.06), ws.set_xd0, passo=0.01)
            ui.html(f'<div style="{_NOTA}">Reatância subtransitória da fonte ao terra '
                    '(sequências positiva/negativa e zero). Só em barras Slack/PV.</div>')
        else:
            ui.html('<div style="text-align:center;color:#9aa3b8;padding:18px 8px;font-size:12.5px;'
                    'line-height:1.55">Barras de carga (PQ) não injetam corrente de falta — não têm '
                    'reatância de fonte. O nível de tensão (acima) define a base em kA.</div>')


def _editor_ramo(ws, sr) -> None:
    with ui.element("div").style("display:flex;justify-content:space-between;align-items:center;"
                                 "margin-bottom:14px"):
        ui.html(f'<span style="font-weight:600;font-size:15px">Ramo {sr["de"]} → {sr["para"]}</span>')
        botao_estilo("Excluir", _EXCLUIR, ws.excluir_sel)
    lig = sr.get("ligacao", "linha")
    selecao("Tipo de ligação", lig, dict(LIG_LABELS), ws.set_ligacao)
    ui.html('<div style="display:flex;gap:8px;align-items:flex-start;font-size:11.5px;color:#7c5cd6;'
            'background:#f6f3fc;border-radius:8px;padding:9px 11px;margin-bottom:16px;line-height:1.5">'
            '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            'stroke-width="2" style="flex-shrink:0;margin-top:1px"><circle cx="12" cy="12" r="9"/>'
            '<path d="M12 8v.5M12 11v5" stroke-linecap="round"/></svg>'
            f'<span>{LIG_NOTAS.get(lig, "")}</span></div>')
    _aspecto(ws)
    if ws.edit_aspecto == "fluxo":
        rotulo("Impedância de sequência positiva")
        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px"):
            with ui.element("div"):
                campo("r (pu)", sr.get("r", 0.0), ws.set_r, passo=0.001)
            with ui.element("div"):
                campo("x (pu)", sr.get("x", 0.0), ws.set_x, passo=0.001)
            with ui.element("div"):
                campo("b (pu)", sr.get("b", 0.0), ws.set_b, passo=0.001)
        ui.html(f'<div style="{_NOTA}">z = r + jx; b é a susceptância shunt total do modelo π. '
                'Usada no fluxo de potência.</div>')
        if lig != "linha":
            ui.html('<div style="height:1px;background:#eef0f3;margin:16px 0 14px"></div>'
                    '<div style="display:flex;align-items:center;gap:7px;margin-bottom:10px">'
                    '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#7c5cd6" '
                    'stroke-width="2"><circle cx="8" cy="12" r="5"/><circle cx="16" cy="12" r="5"/>'
                    f'</svg><span style="font-size:13px;font-weight:600;color:#374151">'
                    f'Transformador · {lig}</span></div>')
            campo("Relação de tap", sr.get("tap", 1.0), ws.set_tap, passo=0.01)
            ui.html('<div style="font-size:11.5px;color:#9aa3b8;margin-top:4px;line-height:1.5">'
                    'tap = 1,0 é nominal. Ajusta a relação de espiras no fluxo de potência.</div>')
    else:
        if lig in _USA_Z0:
            rotulo("Impedância de sequência zero")
            with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px"):
                with ui.element("div"):
                    campo("r₀ (pu)", sr.get("r0", 0.0), ws.set_r0, passo=0.001)
                with ui.element("div"):
                    campo("x₀ (pu)", sr.get("x0", 0.0), ws.set_x0, passo=0.001)
                with ui.element("div"):
                    campo("b₀ (pu)", sr.get("b0", 0.0), ws.set_b0, passo=0.001)
            ui.html(f'<div style="{_NOTA}">Impedância de sequência zero do ramo — usada nas faltas '
                    'à terra. O roteamento depende do tipo de ligação (acima).</div>')
        else:
            ui.html('<div style="text-align:center;color:#9aa3b8;padding:18px 8px;font-size:12.5px;'
                    'line-height:1.55">Esta ligação bloqueia a sequência zero — não conduz corrente '
                    'de falta à terra entre as barras, então não há impedância z₀ a definir.</div>')


def _painel_curto(ws) -> None:
    with ui.element("div").style("padding:18px 20px;border-bottom:1px solid #eef0f3"):
        ui.html('<div style="display:flex;align-items:center;gap:8px;margin-bottom:14px">'
                '<div style="font-size:11px;font-weight:600;letter-spacing:1px;color:#7c5cd6">'
                'CURTO-CIRCUITO</div><span style="font-size:9px;letter-spacing:.5px;color:#7c5cd6;'
                'background:#f3f0fb;border-radius:5px;padding:2px 6px;font-weight:600">FASE 3</span></div>')
        opcoes = {b["id"]: f'{b["id"]} · {b.get("nome", "")}' for b in ws.proj.barras}
        atual = ws.c_barra if ws.c_barra in opcoes else next(iter(opcoes), None)
        selecao("Barra em falta", atual, opcoes, ws.set_c_barra)
        rotulo("Tipo de falta")
        with ui.element("div").style("display:flex;flex-direction:column;gap:6px;margin-bottom:14px"):
            chip("Trifásica (3φ)", ws.c_tipo == "tri", lambda: ws.set_c_tipo("tri"), ROXO)
            with ui.element("div").style("display:flex;gap:6px"):
                chip("Monof.", ws.c_tipo == "mono", lambda: ws.set_c_tipo("mono"), ROXO)
                chip("Bif.", ws.c_tipo == "bi", lambda: ws.set_c_tipo("bi"), ROXO)
                chip("Bif-terra", ws.c_tipo == "biT", lambda: ws.set_c_tipo("biT"), ROXO)
        kv = ws.barra(atual).get("kv", "—") if ws.barra(atual) else "—"
        with ui.element("div").style("display:grid;grid-template-columns:1fr 1fr;gap:10px"):
            with ui.element("div"):
                campo("Zf (pu)", ws.c_zf, ws.set_zf, passo=0.001)
            with ui.element("div"):
                rotulo("kV da barra")
                ui.html(f'<input value="{kv}" disabled style="{INP_OFF}">')
        estilo = ("width:100%;margin-top:6px;padding:10px;border:none;border-radius:9px;"
                  "background:#7c5cd6;color:#fff;font-size:13.5px;font-weight:600;cursor:pointer;"
                  "font-family:inherit")
        botao_estilo("Calcular falta", estilo, ws.calcular_curto)


def _aspecto(ws) -> None:
    with ui.element("div").style("display:flex;gap:6px;margin:4px 0 16px"):
        for chave, txt in (("fluxo", "Fluxo de potência"), ("curto", "Curto-circuito")):
            ativo = ws.edit_aspecto == chave
            estilo = _SEG_BASE + (f";background:{ACCENT};border-color:{ACCENT};color:#fff"
                                  if ativo else ";background:#fff;color:#6b7280")
            botao_estilo(txt, estilo, lambda chave=chave: ws.set_aspecto(chave))


# ----------------------------------------------------------- painel (extra)
def painel_extra(ws) -> None:
    if ws.modo == "editar":
        with ui.element("div").style("padding:18px 20px"):
            ui.html(_label("VALIDAÇÕES"))
            for c in diagrama.validar(ws.proj.barras, ws.proj.ramos):
                _validacao(c)
    elif ws.modo == "fluxo":
        with ui.element("div").style("padding:18px 20px"):
            _fluxo_resultado(ws)
    else:
        with ui.element("div").style("padding:18px 20px"):
            _curto_resultado(ws)


def _validacao(c) -> None:
    ok = c["ok"]
    icone = ('<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1f9d57" '
             'stroke-width="2.4" style="flex-shrink:0;margin-top:1px"><path d="m5 13 4 4L19 7" '
             'stroke-linecap="round" stroke-linejoin="round"/></svg>') if ok else (
        '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#e08a16" '
        'stroke-width="2.2" style="flex-shrink:0;margin-top:1px"><path d="M12 8v5M12 16.5v.5" '
        'stroke-linecap="round"/><path d="M10.3 3.9 2.6 18a1.5 1.5 0 0 0 1.3 2.2h16.2A1.5 1.5 0 0 '
        '0 21.4 18L13.7 3.9a1.5 1.5 0 0 0-2.6 0Z"/></svg>')
    cor = "#5b6270" if ok else "#b06a10"
    ui.html('<div style="display:flex;align-items:flex-start;gap:9px;padding:7px 0;font-size:12.5px;'
            f'line-height:1.4">{icone}<span style="color:{cor}">{c["texto"]}</span></div>')


def _fluxo_resultado(ws) -> None:
    res = ws.proj.resultado_fluxo
    if not res:
        valido = diagrama.eh_valido(ws.proj.barras, ws.proj.ramos)
        titulo = "Pronto para calcular" if valido else "Sistema incompleto"
        texto = ("Clique em Calcular para rodar o Newton-Raphson e ver os resultados no diagrama."
                 if valido else "Há pendências — volte ao modo Editar para resolvê-las.")
        ui.html('<div style="text-align:center;color:#9aa3b8;padding:24px 6px;font-size:13px;'
                'line-height:1.6"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" '
                'stroke="#c5cad3" stroke-width="1.5" style="margin-bottom:8px"><path d="M3 3v18h18"/>'
                '<path d="m7 14 4-4 3 3 5-6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
                f'<div style="color:#374151;font-weight:500">{titulo}</div>'
                f'<div style="margin-top:4px">{texto}</div></div>')
        return
    conv = res.get("convergiu")
    grad = ("linear-gradient(135deg,#1f9d57,#168249)" if conv
            else "linear-gradient(135deg,#d4453b,#b5322a)")
    icone = ('<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" '
             'stroke-width="2.2"><path d="M5 13l4 4L19 7" stroke-linecap="round" '
             'stroke-linejoin="round"/></svg>') if conv else (
        '<svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#fff" '
        'stroke-width="2.2"><path d="M18 6 6 18M6 6l12 12" stroke-linecap="round"/></svg>')
    texto = "Convergiu" if conv else ("Singular" if res.get("erro") == "singular" else "Não convergiu")
    ui.html(f'<div style="border-radius:12px;padding:14px 16px;display:flex;align-items:center;'
            f'color:#fff;background:{grad}"><div style="display:flex;align-items:center;gap:10px">'
            f'{icone}<div><div style="font-size:11px;letter-spacing:.6px;opacity:.85;font-weight:600">'
            f'VEREDITO</div><div style="font-size:17px;font-weight:700">{texto}</div></div></div></div>')
    sb = res["Sbase"]
    perdas = res.get("perdas_totais", {})
    with ui.element("div").style("margin-top:14px"):
        stat_row("Iterações", str(res.get("iteracoes", "—")))
        stat_row("Tempo", f'{fmt(res.get("tempo_ms", 0), 1)} ms')
        stat_row("Perdas P", f'{fmt(perdas.get("P_loss", 0) * sb, 2)} MW')
        stat_row("Perdas Q", f'{fmt(perdas.get("Q_loss", 0) * sb, 2)} Mvar', ultima=True)
    ui.html('<div style="font-size:11px;font-weight:600;letter-spacing:1px;color:#8a909c;'
            'margin:18px 0 10px">PERFIL DE TENSÃO</div>' + graficos.perfil_tensao_svg(res))


def _curto_resultado(ws) -> None:
    cu = ws.proj.resultado_curto
    if cu and not cu.get("erro"):
        stat_row("I de falta (pu)", fmt(cu["Ipu"], 3))
        stat_row("I de falta (kA)", fmt(cu["Ika"], 2), cor=ROXO)
        stat_row("Pot. de curto (MVA)", fmt(cu["Scc"], 1), ultima=True)
    else:
        ui.html('<div style="text-align:center;color:#9aa3b8;padding:24px 6px;font-size:13px;'
                'line-height:1.6"><svg width="34" height="34" viewBox="0 0 24 24" fill="none" '
                'stroke="#c5cad3" stroke-width="1.5" style="margin-bottom:8px">'
                '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>'
                '<div>Escolha a barra e o tipo de falta,<br>depois calcule.</div></div>')
