"""Camada solver — funções **picáveis** sobre o núcleo ``EletroSolver``.

Entrada/saída em tipos simples (dicts/listas/números): os objetos do núcleo são
construídos **dentro** de cada função, para que possam rodar em subprocesso via
``nicegui.run.cpu_bound`` sem problemas de pickling (inclusive no Windows).

Índices ``de``/``para`` dos ramos são 1-based e iguais ao ``id`` das barras; as
funções mapeiam ``id`` → posição (1..n) na ordem crescente dos ids.
"""
from __future__ import annotations

import os
import warnings

import numpy as np

from EletroSolver import Barra, Linha, SistemaPotencia
from Faltas import EstudoCurtoCircuito, Gerador
from Faltas import Ramo as RamoFalta

# tipo da UI → (método de Faltas, nome do tipo no núcleo)
_FALTAS = {
    "tri": "falta_trifasica",
    "mono": "falta_monofasica",
    "bi": "falta_bifasica",
    "biT": "falta_bifasica_terra",
}


def _ordenar(barras: list[dict]):
    """Devolve (barras ordenadas por id, mapa id→posição 1-based)."""
    ordenadas = sorted(barras, key=lambda b: b["id"])
    id_para_pos = {b["id"]: i + 1 for i, b in enumerate(ordenadas)}
    return ordenadas, id_para_pos


def _z_ramo(ramo: dict) -> complex:
    return complex(float(ramo.get("r", 0.0)), float(ramo.get("x", 0.0)))


def montar_ybus(barras: list[dict], ramos: list[dict]) -> list[list[complex]]:
    """Estampa a Ybus (modelo π com tap, convenção MATPOWER).

    Para cada ramo: ``ys = 1/z``, ``bc = j·b/2``; soma ``(ys+bc)/tap²`` na
    diagonal 'de', ``ys+bc`` na diagonal 'para' e ``-ys/tap`` fora dela.
    """
    ordenadas, idpos = _ordenar(barras)
    n = len(ordenadas)
    Y = np.zeros((n, n), dtype=complex)
    for r in ramos:
        if r["de"] not in idpos or r["para"] not in idpos:
            continue
        i, j = idpos[r["de"]] - 1, idpos[r["para"]] - 1
        ys = 1.0 / _z_ramo(r)
        tap = float(r.get("tap", 1.0)) or 1.0
        bc = 1j * float(r.get("b", 0.0)) / 2.0
        Y[i, i] += (ys + bc) / (tap * tap)
        Y[j, j] += ys + bc
        Y[i, j] += -ys / tap
        Y[j, i] += -ys / tap
    return Y.tolist()


def _serializar(v):
    if isinstance(v, (complex, np.complexfloating)):
        return {"real": float(v.real), "imag": float(v.imag)}
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, np.integer):
        return int(v)
    if isinstance(v, np.floating):
        return float(v)
    return v


def _construir_sistema(barras, ramos, params):
    ordenadas, idpos = _ordenar(barras)
    Y = np.asarray(montar_ybus(barras, ramos), dtype=complex)
    core_barras = [
        Barra(i, int(b["tipo"]), float(b["V"]), float(b.get("theta", 0.0)),
              float(b.get("P", 0.0)), float(b.get("Q", 0.0)))
        for i, b in enumerate(ordenadas)
    ]
    linhas = [
        Linha(idpos[r["de"]], idpos[r["para"]], _z_ramo(r),
              float(r.get("b", 0.0)), float(r.get("tap", 1.0)) or 1.0)
        for r in ramos if r["de"] in idpos and r["para"] in idpos
    ]
    sp = SistemaPotencia(
        core_barras, Y,
        tolerancia=float(params.get("tolerancia", 1e-6)),
        max_iter=int(params.get("max_iter", 100)),
        Sbase=float(params.get("Sbase", 100.0)),
        linhas=linhas,
    )
    return sp, ordenadas, idpos


def rodar_fluxo(barras: list[dict], ramos: list[dict], params: dict) -> dict:
    """Monta o sistema, roda Newton-Raphson e coleta tudo em tipos nativos.

    Nunca levanta: erros viram ``{"convergiu": False, "erro": "..."}`` para a UI
    exibir um selo de falha. ``params`` aceita ``sensibilidade: bool``.
    """
    cap = os.environ.get("ELETROGUI_MAX_BARRAS")
    if cap and len(barras) > int(cap):
        return {"convergiu": False, "erro": "limite",
                "mensagem": f"Demo limitada a {cap} barras."}
    try:
        sp, ordenadas, idpos = _construir_sistema(barras, ramos, params)
    except (ValueError, ZeroDivisionError) as exc:
        return {"convergiu": False, "erro": "entrada", "mensagem": str(exc)}

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            sp.calcular_fluxo()
    except np.linalg.LinAlgError as exc:
        return {"convergiu": False, "erro": "singular", "mensagem": str(exc)}

    pos_para_id = {p: bid for bid, p in idpos.items()}
    nome_por_id = {b["id"]: b.get("nome", "") for b in ordenadas}
    barras_res = []
    for pos, b in enumerate(sp.barras):
        barras_res.append({
            "id": pos_para_id[pos + 1],
            "nome": nome_por_id[pos_para_id[pos + 1]],
            "indice": pos + 1,
            "tipo": int(b.tipo),
            "V": float(b.V),
            "theta_rad": float(b.theta),
            "theta_deg": float(np.degrees(b.theta)),
            "P": float(b.P),
            "Q": float(b.Q),
        })

    ramos_res = []
    vistos = set()
    for r in ramos:
        if r["de"] not in idpos or r["para"] not in idpos:
            continue
        de, para = idpos[r["de"]], idpos[r["para"]]
        chave = (min(de, para), max(de, para))
        if chave in vistos:
            continue
        vistos.add(chave)
        try:
            t = sp.transito(de, para)
            perdas = sp.losses(de, para)
        except (ValueError, ZeroDivisionError):
            continue
        ramos_res.append({
            "id": r.get("id"),
            "de": r["de"], "para": r["para"],
            "P_ij": float(t["P_ij"]), "Q_ij": float(t["Q_ij"]),
            "S_ij": float(abs(t["S_ij"])),
            "P_loss": float(perdas["P_loss"]), "Q_loss": float(perdas["Q_loss"]),
            "sentido": 1 if t["P_ij"] >= 0 else -1,
        })

    perdas_tot = sp.totlosses()
    resultado = {
        "convergiu": bool(sp.convergiu),
        "iteracoes": int(sp.convergencia) if sp.convergencia else None,
        "tempo_ms": float(getattr(sp, "tempo", 0.0)) * 1000.0,
        "Sbase": float(sp.sbase),
        "barras": barras_res,
        "ramos": ramos_res,
        "perdas_totais": {"P_loss": float(perdas_tot["P_loss"]),
                          "Q_loss": float(perdas_tot["Q_loss"])},
    }
    if params.get("sensibilidade") and sp.convergiu:
        try:
            S = sp.calcular_sensibilidade()
            resultado["sensibilidade"] = np.asarray(S).tolist()
        except np.linalg.LinAlgError:
            resultado["sensibilidade"] = None
    return resultado


def _cs(z) -> list[float]:
    """Serializa um complexo como ``[re, im]`` (JSON/pickle-friendly)."""
    z = complex(z)
    return [float(z.real), float(z.imag)]


def rodar_curto(barras: list[dict], ramos: list[dict], params: dict,
                falta: dict) -> dict:
    """Curto-circuito por componentes simétricas via ``Faltas``.

    ``falta`` = ``{"tipo": "tri"|"mono"|"bi"|"biT", "barra": id, "Zf": float}``.
    Geradores = barras Slack/PV (X1=xd, X0=xd0). Cargas ignoradas (espelha o
    modelo). Nunca levanta: erros → ``{"erro": "...", "mensagem": "..."}``.
    """
    try:
        sp, ordenadas, idpos = _construir_sistema(barras, ramos, params)
    except (ValueError, ZeroDivisionError) as exc:
        return {"erro": "entrada", "mensagem": str(exc)}

    bar_por_id = {b["id"]: b for b in ordenadas}
    cbarra_id = int(falta.get("barra", 0))
    if cbarra_id not in idpos:
        return {"erro": "entrada", "mensagem": "Barra de falta inexistente."}
    k1 = idpos[cbarra_id]          # 1-based na ordem do núcleo
    k = k1 - 1

    geradores = [
        Gerador(barra=idpos[b["id"]], X1=float(b.get("xd") or 0.10),
                X0=float(b.get("xd0") or 0.06), aterrado=True)
        for b in ordenadas if b["tipo"] in (2, 3)
    ]
    if not geradores:
        return {"erro": "sem_fonte", "mensagem": "Sem barras de fonte (Slack/PV)."}

    ramos_validos = [r for r in ramos if r["de"] in idpos and r["para"] in idpos]
    ramos_f = []
    for r in ramos_validos:
        z1 = complex(float(r.get("r", 0.0)), float(r.get("x", 0.0)))
        if "r0" in r or "x0" in r:
            z0 = complex(float(r.get("r0", 0.0)), float(r.get("x0", 0.0)))
        else:
            z0 = 3 * z1
        ramos_f.append(RamoFalta(
            de=idpos[r["de"]], para=idpos[r["para"]], z1=z1, z0=z0,
            b1=float(r.get("b", 0.0)), b0=float(r.get("b0", 0.0)),
            ligacao=r.get("ligacao", "linha"),
            tap=float(r.get("tap", 1.0)) or 1.0,
        ))

    try:
        est = EstudoCurtoCircuito(sp, geradores, ramos_f, incluir_cargas=False,
                                  incluir_shunt_linha=True, prefault="flat")
    except (ValueError, ZeroDivisionError, np.linalg.LinAlgError) as exc:
        return {"erro": "entrada", "mensagem": str(exc)}

    metodo = _FALTAS.get(falta.get("tipo", "tri"), _FALTAS["tri"])
    Zf = complex(float(falta.get("Zf", 0.0)), 0.0)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = getattr(est, metodo)(k1, Zf)
    except np.linalg.LinAlgError as exc:
        return {"erro": "singular", "mensagem": str(exc)}
    except (ValueError, ZeroDivisionError) as exc:
        return {"erro": "entrada", "mensagem": str(exc)}

    I0, I1, I2 = res["I_seq"]
    Ia, Ib, Ic = res["I_fase"]["a"], res["I_fase"]["b"], res["I_fase"]["c"]
    Ipu = float(max(abs(Ia), abs(Ib), abs(Ic)))
    kv = float(bar_por_id[cbarra_id].get("kv") or 0.0)
    sbase = float(sp.sbase)
    Ika = float(est.corrente_kA(Ipu, kv)) if kv > 0 else 0.0
    Scc = Ipu * sbase

    try:
        Z0mat = est.Z0
        Z0d = _cs(Z0mat[k, k])
    except np.linalg.LinAlgError:
        Z0mat, Z0d = None, None

    contrib = []
    for r, cl in zip(ramos_validos, res["contrib_linha"], strict=False):
        if r["de"] != cbarra_id and r["para"] != cbarra_id:
            continue
        outro = r["para"] if r["de"] == cbarra_id else r["de"]
        contrib.append({"rotulo": f"Ramo {outro}→{cbarra_id}",
                        "mag": float(abs(cl["I_seq"][1])), "fonte": False})
    for g, cg in zip(geradores, res["contrib_gerador"], strict=False):
        if g.barra == k1:
            contrib.append({"rotulo": "Fonte local",
                            "mag": float(abs(cg["I_seq"][1])), "fonte": True})
    tot = sum(c["mag"] for c in contrib) or 1.0
    for c in contrib:
        c["frac"] = c["mag"] / tot
        c["ka"] = c["frac"] * Ika
    contrib.sort(key=lambda c: c["mag"], reverse=True)

    n = len(ordenadas)

    def _mat(M):
        if M is None:
            return None
        return [[_cs(M[i, j]) for j in range(n)] for i in range(n)]

    return {
        "tipo": falta.get("tipo", "tri"),
        "barra": cbarra_id,
        "kfault": k,
        "Ipu": Ipu, "Ika": Ika, "Scc": Scc,
        "kv": kv, "Ibase": (sbase / (3 ** 0.5 * kv)) if kv > 0 else 0.0,
        "Sbase": sbase,
        "Z1": _cs(est.Z1[k, k]), "Z2": _cs(est.Z2[k, k]), "Z0": Z0d,
        "seq": {"I0": _cs(I0), "I1": _cs(I1), "I2": _cs(I2)},
        "fases": {"a": _cs(Ia), "b": _cs(Ib), "c": _cs(Ic)},
        "contrib": contrib,
        "Zbus": _mat(est.Z1), "Z0bus": _mat(Z0mat),
        "barras_mat": [{"id": b["id"], "nome": b["nome"]} for b in ordenadas],
    }


def exportar_sistema(barras: list[dict], ramos: list[dict], params: dict) -> dict:
    """Dicionário no formato do ``exportar`` do núcleo (para download/visualizador)."""
    sp, ordenadas, idpos = _construir_sistema(barras, ramos, params)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sp.calcular_fluxo()

    fluxos = []
    for i, j in sp._pares_conectados():
        fluxos.append({"linha": f"{i + 1} -> {j + 1}",
                       **{c: _serializar(v) for c, v in sp.transito(i + 1, j + 1).items()}})
        fluxos.append({"linha": f"{j + 1} -> {i + 1}",
                       **{c: _serializar(v) for c, v in sp.transito(j + 1, i + 1).items()}})

    return {
        "barras": [
            {"indice": b.indice + 1, "tipo": b.tipo, "tensao": _serializar(b.V),
             "angulo": _serializar(b.theta), "potencia_ativa": _serializar(b.P),
             "potencia_reativa": _serializar(b.Q)}
            for b in sp.barras
        ],
        "fluxos": fluxos,
        "perdas": {k: _serializar(v) for k, v in sp.totlosses().items()},
        "parametros": {
            "tolerancia": sp.tolerancia, "max_iteracoes": sp.max_iter,
            "sbase": sp.sbase, "convergiu": sp.convergiu,
            "tempo_solucao": getattr(sp, "tempo", None),
        },
        "matriz_admitancia": [
            [_serializar(sp.Y[i, j]) for j in range(sp.n_barras)]
            for i in range(sp.n_barras)
        ],
    }
