"""Modal 'Casos de exemplo' — espelha a galeria do ``modelo/`` (532-564)."""
from __future__ import annotations

from nicegui import ui

from gui import casos
from gui.layout import ACCENT

_ICONE = ('<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
          'stroke-width="2"><circle cx="6" cy="6" r="2.2"/><circle cx="18" cy="6" r="2.2"/>'
          '<circle cx="12" cy="18" r="2.2"/><path d="M7.4 7.2 11 16M16.6 7.2 13 16M7.6 6h8.8"/></svg>')


def criar(ws):
    dlg = ui.dialog()
    with dlg, ui.card().style(
        "background:#fff;border-radius:18px;width:920px;max-width:100%;max-height:88vh;"
        "overflow:auto;padding:0;box-shadow:0 24px 70px rgba(16,24,40,.35)"
    ):
        with ui.element("div").style("display:flex;align-items:flex-start;"
                                     "justify-content:space-between;padding:26px 30px 18px"):
            ui.html('<div><div style="font-weight:700;font-size:20px;letter-spacing:-.2px">'
                    'Casos de exemplo</div><div style="font-size:13.5px;color:#6b7280;'
                    'margin-top:4px">Escolha um sistema de teste para carregar no editor. '
                    'Você pode editar tudo depois.</div></div>')
            fechar = ui.element("button").style(
                "border:none;background:#f1f2f4;width:34px;height:34px;border-radius:9px;"
                "cursor:pointer;display:flex;align-items:center;justify-content:center;"
                "color:#6b7280").on("click", ws.fechar_galeria)
            with fechar:
                ui.html('<svg width="17" height="17" viewBox="0 0 24 24" fill="none" '
                        'stroke="currentColor" stroke-width="2.2" stroke-linecap="round">'
                        '<path d="M18 6 6 18M6 6l12 12"/></svg>')
        with ui.element("div").style("padding:4px 30px 30px;display:grid;"
                                     "grid-template-columns:1fr 1fr;gap:16px"):
            for c in casos.lista_casos():
                _card(ws, c)
    return dlg


def _card(ws, c):
    ieee = c["tag"] == "IEEE"
    tag = ("font-size:10.5px;font-weight:700;letter-spacing:.4px;padding:3px 8px;border-radius:6px;"
           + (f"background:#eef3fe;color:{ACCENT}" if ieee else "background:#f1f2f4;color:#6b7280"))
    card = ui.element("div").classes("es-cardhover").style(
        "border:1px solid #e6e8ec;border-radius:14px;padding:20px;cursor:pointer;"
        "display:flex;flex-direction:column").on("click", lambda c=c: ws.carregar_caso(c["chave"]))
    with card:
        ui.html(
            '<div style="display:flex;align-items:center;gap:9px;margin-bottom:12px">'
            f'<div style="width:34px;height:34px;border-radius:9px;background:#eef3fe;color:{ACCENT};'
            f'display:flex;align-items:center;justify-content:center;flex-shrink:0">{_ICONE}</div>'
            f'<div style="flex:1;line-height:1.25"><div style="font-weight:600;font-size:15.5px">'
            f'{c["nome"]}</div><div style="font-size:12.5px;color:#8a909c">{c["sub"]}</div></div>'
            f'<span style="{tag}">{c["tag"]}</span></div>'
            f'<div style="font-size:13px;line-height:1.55;color:#6b7280;flex:1">{c["desc"]}</div>'
            '<div style="display:flex;gap:16px;margin-top:14px;padding-top:13px;'
            "border-top:1px solid #f0f1f4;font-family:'IBM Plex Mono',monospace;font-size:12px;"
            'color:#5b6270">'
            f'<span><b style="color:#1f2430">{c["nb"]}</b> barras</span>'
            f'<span><b style="color:#1f2430">{c["nr"]}</b> ramos</span>'
            f'<span style="margin-left:auto;color:#8a909c">{c["kv"]}</span></div>')
