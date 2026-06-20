"""Componentes reutilizáveis da UI (cartão, selo, campo numérico, segmentado).

Camada de UI: importa ``nicegui.ui``. Funções pequenas que padronizam o visual
``es-*`` para as páginas não repetirem estilos inline.
"""
from __future__ import annotations

from contextlib import contextmanager

from nicegui import ui

from gui.layout import (
    ACCENT,
    CARD,
    CARTAO_STAT,
    INP,
    LBL,
    MONO,
    STAT_LABEL,
    STAT_ROW,
    STAT_ROW_L,
    STAT_ROW_V,
    STAT_VAL,
    TEXTO,
)


@contextmanager
def cartao(titulo: str | None = None, extra: str = ""):
    """Cartão claro padrão; opcionalmente com título."""
    with ui.element("div").style(f"{CARD};padding:20px 22px;{extra}") as c:
        if titulo:
            ui.html(f'<div style="font-weight:600;font-size:15px;margin-bottom:14px;'
                    f'color:{TEXTO}">{titulo}</div>')
        yield c


def selo(ok: bool, texto: str, neutro: bool = False) -> None:
    """Selo de veredito (verde = ok, vermelho = falha, cinza = neutro)."""
    if neutro:
        fg, bg = "#5b6270", "#eef0f3"
    elif ok:
        fg, bg = "#15803d", "rgba(34,197,94,.14)"
    else:
        fg, bg = "#b91c1c", "rgba(239,68,68,.12)"
    ponto = "●" if not neutro else "○"
    ui.html(f'<span style="display:inline-flex;align-items:center;gap:7px;font-size:12.5px;'
            f'font-weight:600;color:{fg};background:{bg};border-radius:999px;padding:5px 12px">'
            f'<span style="font-size:9px">{ponto}</span>{texto}</span>')


def stat(rotulo: str, valor: str, unidade: str = "", cor: str = TEXTO) -> None:
    """Cartão-número compacto (KPI)."""
    with ui.element("div").style(f"{CARD};padding:16px 18px;min-width:0"):
        ui.html(f'<div style="font-size:11.5px;letter-spacing:.6px;color:#8a909c;'
                f'text-transform:uppercase;font-weight:600">{rotulo}</div>'
                f'<div class="es-mono" style="font-size:24px;font-weight:600;color:{cor};'
                f'margin-top:6px;line-height:1">{valor}'
                f'<span style="font-size:13px;color:#8a909c;margin-left:4px">{unidade}</span></div>')


def campo_num(rotulo: str, valor, on_change, *, passo: float = 0.01,
              formato: str | None = None, dica: str = ""):
    """Campo numérico estilizado (IBM Plex Mono)."""
    el = ui.number(label=rotulo, value=valor, step=passo, format=formato,
                   on_change=lambda e: on_change(e.value))
    el.props('outlined dense')
    el.style(f"font-family:{MONO}").classes("w-full")
    if dica:
        el.tooltip(dica)
    return el


def segmentado(opcoes: dict, valor, on_change):
    """Controle segmentado (toggle) no acento do tema."""
    el = ui.toggle(opcoes, value=valor, on_change=lambda e: on_change(e.value))
    el.props('unelevated color=primary toggle-color=primary').style(
        f"--q-primary:{ACCENT}")
    return el


def botao_primario(texto: str, on_click, icone: str | None = None):
    b = ui.button(texto, on_click=on_click)
    if icone:
        b = ui.button(texto, icon=icone, on_click=on_click)
    b.props("unelevated no-caps").style(
        f"background:{ACCENT};color:#fff;border-radius:9px;font-weight:600;"
        "text-transform:none;box-shadow:0 4px 12px rgba(43,108,240,.28)")
    return b


def botao_fantasma(texto: str, on_click, icone: str | None = None):
    b = ui.button(texto, icon=icone, on_click=on_click) if icone else ui.button(texto, on_click=on_click)
    b.props("outline no-caps").style(
        "color:#374151;border-radius:9px;font-weight:600;text-transform:none;"
        "border:1px solid #d3d7de;background:#fff")
    return b


# ----------------------------------------------------- helpers do modelo (es-*)
def botao_estilo(inner_html: str, estilo: str, on_click):
    """Botão ``<button>`` cru com estilo inline do modelo e HTML interno."""
    b = ui.element("button").style(estilo).on("click", on_click)
    with b:
        ui.html(inner_html)
    return b


def chip(texto: str, ativo: bool, on_click, cor: str = ACCENT):
    """Chip segmentado (PQ/PV/Slack, tipos de falta…) — espelha ``chip()``."""
    borda = cor if ativo else "#dde1e7"
    fundo = cor if ativo else "#fff"
    fg = "#fff" if ativo else "#6b7280"
    estilo = (f"flex:1;padding:7px 0;border-radius:7px;border:1px solid {borda};"
              f"background:{fundo};color:{fg};font-size:12px;font-weight:600;cursor:pointer;"
              f"font-family:inherit")
    return botao_estilo(texto, estilo, on_click)


def rotulo(texto: str) -> None:
    ui.html(f'<label style="{LBL}">{texto}</label>')


def campo(label: str | None, valor, on_change, *, passo: float = 0.01,
          desabilitado: bool = False, dica: str = "", inteiro: bool = False):
    """Rótulo (acima) + campo numérico estilo modelo (IBM Plex Mono)."""
    if label:
        rotulo(label)
    el = ui.number(value=valor, step=passo,
                   on_change=lambda e: on_change(e.value))
    el.props("outlined dense hide-bottom-space")
    el.style(f"{INP};margin-bottom:12px;font-family:{MONO}").classes("es-campo")
    if desabilitado:
        el.props("readonly").style("background:#f4f5f7;color:#8a909c")
    if dica:
        el.tooltip(dica)
    return el


def campo_texto(label: str | None, valor, on_change):
    if label:
        rotulo(label)
    el = ui.input(value=valor, on_change=lambda e: on_change(e.value))
    el.props("outlined dense hide-bottom-space")
    el.style(f"{INP};margin-bottom:12px").classes("es-campo")
    return el


def selecao(label: str | None, valor, opcoes: dict, on_change):
    """Rótulo + ``ui.select`` (dropdown) estilizado."""
    if label:
        rotulo(label)
    el = ui.select(opcoes, value=valor, on_change=lambda e: on_change(e.value))
    # NiceGUI ≥3 já modela as opções de dict como objetos {value,label} e emite o
    # objeto no change (Select._event_args_to_value traduz índice→chave). NÃO
    # adicionar 'emit-value'/'map-options' (idioma do NiceGUI 2): faria o Quasar
    # emitir um escalar e a troca não comitaria (dropdown reverte). Ver
    # tests/test_componentes_select.py.
    el.props("outlined dense hide-bottom-space")
    el.style(f"{INP};margin-bottom:12px").classes("es-campo")
    return el


def stat_card(label: str, valor: str, unidade: str = "", cor: str = TEXTO):
    """Cartão-número (cartaoStat) usado nos detalhes de fluxo/curto."""
    with ui.element("div").style(CARTAO_STAT):
        ui.html(f'<div style="{STAT_LABEL}">{label}</div>'
                f'<div style="{STAT_VAL};color:{cor}">{valor}'
                + (f'<span style="font-size:13px;font-weight:500;color:#8a909c;'
                   f'margin-left:5px">{unidade}</span>' if unidade else "")
                + "</div>")


def stat_row(label: str, valor: str, *, cor: str = TEXTO, ultima: bool = False) -> None:
    borda = ";border:none" if ultima else ""
    ui.html(f'<div style="{STAT_ROW}{borda}"><span style="{STAT_ROW_L}">{label}</span>'
            f'<span style="{STAT_ROW_V};color:{cor}">{valor}</span></div>')
