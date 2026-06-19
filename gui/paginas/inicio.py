"""Página Início — espelha o ``modelo/`` (94-154) e o visualizador (506-527)."""
from __future__ import annotations

import json

from nicegui import ui

from gui.componentes import botao_estilo
from gui.layout import ACCENT, BTN_GHOST, BTN_PRIMARY, CARD_BOX

_CHECK = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#1f9d57" '
          'stroke-width="2.2" style="flex-shrink:0"><circle cx="12" cy="12" r="9"/>'
          '<path d="m8.5 12 2.4 2.4 4.6-4.8" stroke-linecap="round" stroke-linejoin="round"/></svg>')
_CIRC = ('<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#c5cad3" '
         'stroke-width="2" style="flex-shrink:0"><circle cx="12" cy="12" r="9"/></svg>')


def _badge(ok, warn):
    base = ("font-size:11px;font-weight:600;padding:3px 9px;border-radius:6px;"
            "font-family:'IBM Plex Mono',monospace;")
    if ok:
        return "pronto", base + "background:#e7f6ec;color:#1f9d57"
    if warn:
        return "pendente", base + "background:#fdf2e0;color:#c47e10"
    return "vazio", base + "background:#eceef1;color:#9097a3"


def _modo_card(ws, icone_bg, icone_cor, icone, titulo, desc, on_click):
    card = ui.element("div").classes("es-cardhover").style(
        "background:#fff;border:1px solid #e6e8ec;border-radius:14px;padding:20px;cursor:pointer;"
        "box-shadow:0 1px 2px rgba(16,24,40,.04)").on("click", on_click)
    with card:
        ui.html(
            f'<div style="width:30px;height:30px;border-radius:8px;background:{icone_bg};'
            f'color:{icone_cor};display:flex;align-items:center;justify-content:center;'
            f'margin-bottom:14px">{icone}</div>'
            f'<div style="font-weight:600;font-size:15px;margin-bottom:6px">{titulo}</div>'
            f'<div style="font-size:13px;line-height:1.55;color:#6b7280">{desc}</div>')


def render(ws) -> None:
    with ui.element("div").style("max-width:1060px;margin:0 auto;padding:34px 40px 60px;"
                                 "animation:esFade .25s ease"):
        ui.html(
            f'<div style="font-size:12px;font-weight:600;letter-spacing:1.3px;color:{ACCENT};'
            'margin-bottom:10px">SUÍTE DE SISTEMAS DE POTÊNCIA</div>'
            '<h1 style="font-size:34px;font-weight:700;margin:0 0 14px;letter-spacing:-.5px">'
            'Bem-vindo ao EletroSolver</h1>'
            '<p style="font-size:15.5px;line-height:1.6;color:#5b6270;max-width:720px;'
            'margin:0 0 30px">Um único diagrama unifilar é o centro de tudo: monta a Ybus '
            'automaticamente e recebe, <strong style="color:#374151;font-weight:600">sobre o '
            'próprio desenho</strong>, o <strong style="color:#374151;font-weight:600">fluxo de '
            'potência</strong> (Newton-Raphson) e o <strong style="color:#374151;font-weight:600">'
            'curto-circuito</strong>. O estado é compartilhado durante a sessão.</p>')

        with ui.element("div").style("display:grid;grid-template-columns:1.3fr 1fr;gap:20px;"
                                     "margin-bottom:34px"):
            with ui.element("div").style(CARD_BOX + ";padding:22px 24px"):
                itens = ws.proj.estado_itens()
                prontos = sum(1 for it in itens if it["ok"])
                ui.html('<div style="display:flex;justify-content:space-between;align-items:baseline;'
                        'margin-bottom:16px"><div style="font-weight:600;font-size:15px">'
                        'Estado do projeto</div><div style="font-family:\'IBM Plex Mono\',monospace;'
                        f'font-size:12.5px;color:#8a909c">{prontos} prontos</div></div>')
                for it in itens:
                    txt, est = _badge(it["ok"], it.get("warn"))
                    icone = _CHECK if it["ok"] else _CIRC
                    ui.html('<div style="display:flex;align-items:center;gap:12px;padding:11px 0;'
                            f'border-bottom:1px solid #f0f1f4">{icone}'
                            f'<span style="flex:1;font-size:14px;color:#374151">{it["label"]}</span>'
                            f'<span style="{est}">{txt}</span></div>')
            with ui.element("div").style(CARD_BOX + ";padding:22px 24px;display:flex;"
                                         "flex-direction:column"):
                ui.html('<div style="font-weight:600;font-size:15px;margin-bottom:16px">Projeto</div>')
                botao_estilo(
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#fff" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v5h-5"/></svg>'
                    'Carregar caso exemplo', BTN_PRIMARY, ws.abrir_galeria)
                botao_estilo(
                    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#374151" '
                    'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
                    '<path d="M12 3v12"/><path d="m7 11 5 5 5-5"/><path d="M5 21h14"/></svg>'
                    'Baixar projeto atual', BTN_GHOST, ws.baixar_projeto)
                with ui.element("div").style("margin-top:auto;border:1.5px dashed #d3d7de;"
                                             "border-radius:11px;padding:14px;text-align:center"):
                    ui.html('<div style="font-size:13.5px;font-weight:500;color:#374151;'
                            'margin-bottom:6px">Importar <span style="font-family:'
                            "'IBM Plex Mono',monospace\">projeto.json</span></div>")
                    ui.upload(on_upload=lambda e: _importar(ws, e), auto_upload=True,
                              max_files=1).props("accept=.json flat dense").style("width:100%")

        ui.html('<div style="font-size:11.5px;font-weight:600;letter-spacing:1.3px;color:#8a909c;'
                'margin-bottom:14px">UM DIAGRAMA, TRÊS MODOS</div>')
        with ui.element("div").style("display:grid;grid-template-columns:repeat(3,1fr);gap:18px"):
            _modo_card(ws, "#eef3fe", ACCENT,
                       '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
                       'stroke="currentColor" stroke-width="2"><circle cx="6" cy="6" r="2.2"/>'
                       '<circle cx="18" cy="18" r="2.2"/><path d="M7.5 7.5 16.5 16.5"/></svg>',
                       "Editar", "Barras (Slack / PV / PQ) e ramos. Arraste, ligue, valide a rede.",
                       ws.nav_editar)
            _modo_card(ws, "#eef3fe", ACCENT,
                       '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
                       'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                       'stroke-linejoin="round"><path d="M4 14h3l2-7 4 14 2-7h5"/></svg>',
                       "Fluxo de potência",
                       "Tensões, ângulos e P/Q desenhados nos nós; trânsito nos ramos.",
                       ws.nav_fluxo)
            _modo_card(ws, "#f3f0fb", "#7c5cd6",
                       '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" '
                       'stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                       'stroke-linejoin="round"><path d="M13 2 4 14h7l-1 8 9-12h-7z"/></svg>',
                       "Curto-circuito",
                       "Barra em falta destacada no diagrama; corrente de curto no nó.",
                       ws.nav_curto)


def _importar(ws, e) -> None:
    try:
        dados = json.loads(e.content.read().decode("utf-8"))
        ws.importar_projeto(dados)
        ui.notify("Projeto importado.", type="positive")
    except (ValueError, KeyError, UnicodeDecodeError) as exc:
        ui.notify(f"JSON inválido: {exc}", type="negative")


def render_viz(ws) -> None:
    res = ws.proj.resultado_fluxo
    with ui.element("div").style("max-width:760px;margin:0 auto;padding:34px 40px 60px;"
                                 "animation:esFade .25s ease"):
        ui.html(
            f'<div style="font-size:12px;font-weight:600;letter-spacing:1.3px;color:{ACCENT};'
            'margin-bottom:8px">VISUALIZADOR</div>'
            '<h1 style="font-size:27px;font-weight:700;margin:0 0 6px;letter-spacing:-.4px">'
            'Resultados exportados</h1>'
            '<p style="font-size:14px;color:#6b7280;margin:0 0 26px;line-height:1.55">Consome um '
            'JSON de resultado exportado pelo fluxo — sem recalcular.</p>')
        if res:
            perdas = res.get("perdas_totais", {}).get("P_loss", 0.0) * res.get("Sbase", 100.0)
            conv = "Convergiu" if res.get("convergiu") else "Falhou"
            with ui.element("div").style(CARD_BOX):
                ui.html('<div style="font-weight:600;font-size:14.5px;margin-bottom:12px">'
                        'Último resultado da sessão</div>'
                        '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px">'
                        + _mini("Convergência", conv)
                        + _mini("Iterações", str(res.get("iteracoes", "—")))
                        + _mini("Perdas P", f"{perdas:.2f}") + "</div>")


def _mini(label, valor):
    return ('<div style="background:#fff;border:1px solid #e6e8ec;border-radius:12px;'
            'padding:15px 16px"><div style="font-size:11.5px;color:#8a909c;font-weight:500;'
            f'margin-bottom:5px">{label}</div><div style="font-size:21px;font-weight:700;'
            f'font-family:\'IBM Plex Mono\',monospace">{valor}</div></div>')
