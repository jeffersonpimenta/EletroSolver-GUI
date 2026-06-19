"""Moldura comum da GUI — gaveta escura + cabeçalho + tema ``es-*``.

App de **página única** (espelha o design ``modelo/``): a gaveta troca
``page``/``modo`` no controlador :class:`gui.workspace.Workspace` (sem navegar por
URL). Este módulo concentra o tema, os **tokens de estilo inline** do modelo (o
sistema visual ``es-*``) e a construção da gaveta/cabeçalho.
"""
from __future__ import annotations

from nicegui import ui

# --------------------------------------------------------------------- tokens
ACCENT = "#2b6cf0"
ROXO = "#7c5cd6"
TEXTO = "#1f2430"
CARD = ("background:#fff;border:1px solid #e6e8ec;border-radius:14px;"
        "box-shadow:0 1px 2px rgba(16,24,40,.04)")
MONO = "'IBM Plex Mono',monospace"
SANS = "'IBM Plex Sans',sans-serif"

# Tokens inline portados do ``renderVals`` do modelo (sistema visual es-*).
LBL = ("display:block;font-size:11px;font-weight:600;color:#8a909c;"
       "margin-bottom:5px;letter-spacing:.2px")
INP = ("width:100%;padding:8px 10px;border:1px solid #dde1e7;border-radius:8px;"
       "font-size:13px;color:#1f2430;outline:none;margin-bottom:12px;background:#fff")
INP_OFF = INP + ";background:#f4f5f7;color:#8a909c"
TOOL_BTN = ("display:inline-flex;align-items:center;gap:6px;padding:7px 11px;"
            "border:1px solid #e2e5ea;background:#fff;border-radius:8px;font-size:12.5px;"
            "font-weight:500;color:#374151;cursor:pointer;font-family:inherit")
BTN_PRIMARY = (f"display:flex;align-items:center;justify-content:center;gap:8px;width:100%;"
               f"padding:11px;border:none;border-radius:9px;background:{ACCENT};color:#fff;"
               f"font-size:13.5px;font-weight:600;cursor:pointer;font-family:inherit;"
               f"margin-bottom:10px")
BTN_GHOST = ("display:flex;align-items:center;justify-content:center;gap:8px;width:100%;"
             "padding:11px;border:1px solid #e2e5ea;border-radius:9px;background:#fff;"
             "color:#374151;font-size:13.5px;font-weight:500;cursor:pointer;"
             "font-family:inherit;margin-bottom:16px")
CARD_BOX = ("background:#fff;border:1px solid #e6e8ec;border-radius:14px;padding:18px 20px;"
            "box-shadow:0 1px 2px rgba(16,24,40,.04)")
CARTAO_STAT = "background:#fff;border:1px solid #e6e8ec;border-radius:12px;padding:15px 16px"
STAT_LABEL = "font-size:11.5px;color:#8a909c;font-weight:500;margin-bottom:5px"
STAT_VAL = f"font-size:21px;font-weight:700;font-family:{MONO};letter-spacing:-.5px"
STAT_ROW = ("display:flex;justify-content:space-between;align-items:center;padding:9px 0;"
            "border-bottom:1px solid #f0f1f4")
STAT_ROW_L = "font-size:12.5px;color:#6b7280"
STAT_ROW_V = f"font-size:15px;font-weight:700;font-family:{MONO}"
TH_ROW = "border-bottom:2px solid #eef0f3"
TH_L = (f"text-align:left;padding:7px 8px;font-size:10.5px;font-weight:600;color:#8a909c;"
        f"font-family:{SANS};letter-spacing:.3px")
TH_R = (f"text-align:right;padding:7px 8px;font-size:10.5px;font-weight:600;color:#8a909c;"
        f"font-family:{SANS};letter-spacing:.3px")
TD_L = "text-align:left;padding:8px;color:#374151"
TD_R = "text-align:right;padding:8px;color:#1f2430"

# Gaveta: (chave, rótulo, svg-inner, badge, grupo, ação)
_NAV = [
    ("inicio", "Início", '<path d="M3 11.5 12 4l9 7.5"/><path d="M5 10v10h14V10"/>',
     "", "espaco", "nav_inicio"),
    ("sistema", "Sistema",
     '<circle cx="6" cy="6" r="2.4"/><circle cx="18" cy="6" r="2.4"/>'
     '<circle cx="12" cy="18" r="2.4"/><path d="M7.6 7.4 11 15.8M16.4 7.4 13 15.8M8 6h8"/>',
     "DIAGRAMA", "espaco", "nav_editar"),
    ("fluxo", "Fluxo de potência", '<path d="M4 14h4l3-8 4 16 2-8h3"/>',
     "", "analise", "nav_fluxo"),
    ("curto", "Curto-circuito", '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
     "FASE 3", "analise", "nav_curto"),
]
_GRUPOS = {"espaco": "ESPAÇO DE TRABALHO", "analise": "ANÁLISE SOBRE O DIAGRAMA"}


def tema() -> None:
    ui.add_head_html(
        '<link rel="preconnect" href="https://fonts.googleapis.com">'
        '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600'
        '&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">'
        "<style>"
        "*{box-sizing:border-box}html,body{margin:0;padding:0}"
        f"body{{font-family:{SANS};color:{TEXTO};background:#f4f5f7}}"
        ".nicegui-content{padding:0;gap:0;max-width:none}"
        ".q-page,.q-layout{min-height:0}"
        "input,select{font-family:'IBM Plex Mono',monospace}"
        "::-webkit-scrollbar{width:10px;height:10px}"
        "::-webkit-scrollbar-thumb{background:#cfd3da;border-radius:8px;"
        "border:2px solid transparent;background-clip:content-box}"
        "::-webkit-scrollbar-track{background:transparent}"
        ".es-mono{font-family:" + MONO + "}"
        ".es-nav:hover{background:rgba(255,255,255,.05)!important}"
        ".es-cardhover{transition:transform .15s,box-shadow .15s}"
        ".es-cardhover:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(16,24,40,.08)}"
        "@keyframes esFade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}"
        "</style>"
    )


def _svg(inner: str, cor: str = "currentColor", tam: float = 17) -> str:
    return (f'<svg width="{tam}" height="{tam}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{cor}" stroke-width="2" stroke-linecap="round" '
            f'stroke-linejoin="round">{inner}</svg>')


def _nav_ativo(ws, chave: str) -> bool:
    if chave == "inicio":
        return ws.page == "inicio"
    return ws.page == "sistema" and ws.modo == {"sistema": "editar"}.get(chave, chave)


def montar_drawer(ws) -> None:
    """Gaveta escura interativa — itens trocam ``page``/``modo`` no controlador."""
    prontos = sum(1 for it in ws.proj.estado_itens() if it["ok"])
    with ui.element("aside").style(
        "width:266px;flex-shrink:0;background:#0b1220;color:#cdd3de;display:flex;"
        "flex-direction:column;border-right:1px solid #161d2e;height:100vh"
    ):
        ui.html(
            '<div style="display:flex;align-items:center;gap:12px;padding:20px 18px 18px">'
            f'<div style="width:40px;height:40px;border-radius:11px;background:{ACCENT};'
            'display:flex;align-items:center;justify-content:center;flex-shrink:0;'
            'box-shadow:0 4px 14px rgba(43,108,240,.35)">'
            '<svg width="22" height="22" viewBox="0 0 24 24"><path d="M13 2 4 14h7l-1 8 9-12h-7z" '
            'fill="#fff"/></svg></div>'
            '<div style="line-height:1.2"><div style="font-weight:700;font-size:16px;color:#fff;'
            'letter-spacing:.2px">EletroSolver</div>'
            '<div style="font-size:11.5px;color:#7f8aa3">Sistemas de potência</div></div></div>')
        with ui.element("div").style("flex:1;overflow-y:auto;padding:8px 12px"):
            grupo_atual = None
            for chave, rotulo, inner, badge, grupo, acao in _NAV:
                if grupo != grupo_atual:
                    grupo_atual = grupo
                    if grupo == "espaco":
                        ui.html('<div style="font-size:10.5px;letter-spacing:1.4px;color:#5e6a85;'
                                'font-weight:600;padding:12px 8px 8px">ESPAÇO DE TRABALHO</div>')
                    else:
                        ui.html('<div style="padding:6px 14px 4px;font-size:10.5px;color:#5e6a85;'
                                'letter-spacing:.5px">Análise sobre o diagrama</div>')
                ativo = _nav_ativo(ws, chave)
                cor_txt = "#fff" if ativo else "#aeb6c8"
                fundo = "background:rgba(43,108,240,.16);" if ativo else ""
                anel = "box-shadow:inset 0 0 0 1px rgba(43,108,240,.35);" if ativo else ""
                badge_html = ("" if not badge else
                              f'<span style="margin-left:auto;font-size:9.5px;letter-spacing:.5px;'
                              f'color:#7f8aa3;border:1px solid #2a3450;border-radius:5px;'
                              f'padding:1px 6px">{badge}</span>')
                item = ui.element("a").classes("es-nav").style(
                    f"display:flex;align-items:center;gap:11px;padding:9px 11px;border-radius:9px;"
                    f"cursor:pointer;font-size:13.5px;font-weight:{600 if ativo else 500};"
                    f"margin-bottom:3px;color:{cor_txt};{fundo}{anel}")
                with item:
                    ui.html(f"{_svg(inner)}<span>{rotulo}</span>{badge_html}")
                item.on("click", getattr(ws, acao))
        pct = f"{round(ws.proj.progresso() * 100)}%"
        ui.html(
            '<div style="padding:14px 16px 16px;border-top:1px solid #161d2e">'
            '<div style="display:flex;justify-content:space-between;align-items:center;'
            'font-size:12px;margin-bottom:8px">'
            f'<span style="color:#9aa3b8">Projeto · <span style="color:#cdd3de">'
            f'{ws.proj.nome}</span></span>'
            f'<span class="es-mono" style="color:#7f8aa3">{prontos} / 5</span></div>'
            '<div style="height:5px;border-radius:4px;background:#1a2236;overflow:hidden">'
            f'<div style="height:100%;border-radius:4px;background:{ACCENT};width:{pct};'
            'transition:width .4s"></div></div></div>')


def cabecalho_html(titulo: str) -> str:
    return (
        '<header style="height:56px;flex-shrink:0;display:flex;align-items:center;'
        'justify-content:space-between;padding:0 28px;border-bottom:1px solid #e6e8ec;'
        'background:#fafbfc">'
        f'<div style="font-size:13.5px;color:#8a909c">EletroSolver '
        '<span style="margin:0 7px;color:#c7ccd4">/</span>'
        f'<span style="color:{TEXTO};font-weight:600">{titulo}</span></div>'
        '<div style="display:flex;align-items:center;gap:8px;font-size:12.5px;color:#5b6270;'
        'border:1px solid #e2e5ea;border-radius:999px;padding:5px 12px;background:#fff">'
        '<span style="width:8px;height:8px;border-radius:50%;background:#22c55e;'
        'box-shadow:0 0 0 3px rgba(34,197,94,.16)"></span>Estado salvo na sessão</div></header>')
