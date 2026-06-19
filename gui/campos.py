"""Parsing e formatação de campos — sem dependência de UI (testável headless).

Aceita vírgula como separador decimal (PT-BR) e tolera entradas vazias,
devolvendo um default em vez de levantar exceção, para que a edição na UI nunca
quebre por um campo intermediário inválido.
"""
from __future__ import annotations

import math

_VAZIO = (None, "")


def para_float(texto, default: float = 0.0) -> float:
    """Converte texto em float. Aceita vírgula decimal; vazio → default."""
    if isinstance(texto, (int, float)):
        return float(texto)
    if texto in _VAZIO:
        return float(default)
    try:
        return float(str(texto).strip().replace(",", "."))
    except (TypeError, ValueError):
        return float(default)


def para_int(texto, default: int = 0) -> int:
    """Converte texto em int; vazio/invalido → default."""
    if isinstance(texto, bool):
        return int(texto)
    if isinstance(texto, int):
        return texto
    if texto in _VAZIO:
        return int(default)
    try:
        return int(round(float(str(texto).strip().replace(",", "."))))
    except (TypeError, ValueError):
        return int(default)


def para_complexo(texto, default: complex = 0j) -> complex:
    """Converte texto em complexo.

    Aceita ``"0.01+0.1j"``, ``"0.01 + 0.1i"`` ou o par ``"r,x"`` (parte real e
    imaginária separadas por vírgula seguida de outro número).
    """
    if isinstance(texto, (int, float, complex)):
        return complex(texto)
    if texto in _VAZIO:
        return complex(default)
    s = str(texto).strip().lower().replace(" ", "").replace("i", "j")
    # Par "r,x" (duas grandezas) — só quando NÃO há 'j' (senão é decimal PT-BR).
    if "," in s and "j" not in s:
        partes = s.split(",")
        if len(partes) == 2:
            return complex(para_float(partes[0]), para_float(partes[1]))
        s = s.replace(",", ".")
    try:
        return complex(s)
    except (TypeError, ValueError):
        return complex(default)


def graus_para_rad(graus) -> float:
    return math.radians(para_float(graus))


def rad_para_graus(rad) -> float:
    return math.degrees(para_float(rad))


def fmt(x, casas: int = 3) -> str:
    """Formata número para exibição; não-número → travessão."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(v):
        return "—"
    return f"{v:.{casas}f}"


def fmt_complexo(z, casas: int = 3) -> str:
    """Formata complexo como ``a+jb`` (sinal explícito na parte imaginária)."""
    try:
        z = complex(z)
    except (TypeError, ValueError):
        return "—"
    sinal = "+j" if z.imag >= 0 else "−j"
    return f"{z.real:.{casas}f}{sinal}{abs(z.imag):.{casas}f}"
