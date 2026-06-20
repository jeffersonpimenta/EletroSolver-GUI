"""Modelo de dados ``Projeto`` — uma instância por aba do navegador.

Mantido puro/serializável: o estado é JSON-friendly (sem complexos nem numpy),
para caber em ``app.storage.tab`` e dar import/export de graça via
``to_dict``/``from_dict``. Resultados de cálculo **não** entram no ``to_dict``
(são recalculáveis / baixados à parte).

Convenções: ``barra.tipo`` 1=PQ, 2=PV, 3=Slack; ``theta`` em radianos; ``de``/
``para`` dos ramos são 1-based (= ``id`` da barra). ``x``/``y`` são cosméticos.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

PARAMS_PADRAO = {"tolerancia": 1e-6, "max_iter": 100, "Sbase": 100.0}


def _barra(bid, nome, tipo, V, theta, P, Q, x, y, kv=138.0, xd=None, xd0=None) -> dict:
    d = {"id": bid, "nome": nome, "tipo": tipo, "V": V, "theta": theta,
         "P": P, "Q": Q, "x": x, "y": y, "kv": kv}
    # xd (X''d) e xd0 (X0) só fazem sentido em barras de fonte (PV/Slack); o
    # editor/curto assumem 0.10/0.06 quando ausentes (igual ao modelo).
    if xd is not None:
        d["xd"] = xd
    if xd0 is not None:
        d["xd0"] = xd0
    return d


@dataclass
class Projeto:
    # entradas (persistidas / compartilháveis)
    barras: list[dict] = field(default_factory=list)
    ramos: list[dict] = field(default_factory=list)
    params_fluxo: dict = field(default_factory=lambda: dict(PARAMS_PADRAO))
    nome: str = "Sem título"
    # fase 3 (curto-circuito) — projetadas, ainda não usadas pela UI
    geradores: list[dict] | None = None
    cargas: list[dict] | None = None
    seq_ramos: dict | None = None
    # resultados (NÃO persistidos no to_dict)
    resultado_fluxo: dict | None = None
    resultado_curto: dict | None = None

    # ------------------------------------------------------------------ serial
    def to_dict(self) -> dict:
        """Somente entradas — resultados ficam de fora (recalculáveis)."""
        d = {
            "nome": self.nome,
            "barras": deepcopy(self.barras),
            "ramos": deepcopy(self.ramos),
            "params_fluxo": dict(self.params_fluxo),
        }
        if self.geradores is not None:
            d["geradores"] = deepcopy(self.geradores)
        if self.cargas is not None:
            d["cargas"] = deepcopy(self.cargas)
        if self.seq_ramos is not None:
            d["seq_ramos"] = deepcopy(self.seq_ramos)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Projeto:
        params = dict(PARAMS_PADRAO)
        params.update(d.get("params_fluxo") or {})
        return cls(
            nome=d.get("nome", "Sem título"),
            barras=deepcopy(d.get("barras") or []),
            ramos=deepcopy(d.get("ramos") or []),
            params_fluxo=params,
            geradores=deepcopy(d.get("geradores")) if d.get("geradores") is not None else None,
            cargas=deepcopy(d.get("cargas")) if d.get("cargas") is not None else None,
            seq_ramos=deepcopy(d.get("seq_ramos")) if d.get("seq_ramos") is not None else None,
        )

    # ------------------------------------------------------------------ estado
    @classmethod
    def vazio(cls) -> Projeto:
        return cls()

    @classmethod
    def exemplo(cls) -> Projeto:
        """Pequeno sistema de 3 barras pronto para uso (didático)."""
        from gui import casos
        barras, ramos, params = casos.carregar("d3")
        return cls(nome=casos.nome_caso("d3"), barras=barras, ramos=ramos,
                   params_fluxo=params)

    def definir_sistema(self, barras, ramos, params=None, nome=None) -> None:
        """Substitui o sistema (usado por casos prontos / import)."""
        self.barras = deepcopy(barras)
        self.ramos = deepcopy(ramos)
        if params:
            self.params_fluxo = dict(PARAMS_PADRAO) | dict(params)
        if nome:
            self.nome = nome
        self.resultado_fluxo = None
        self.resultado_curto = None

    def alterar_sbase(self, novo: float) -> None:
        """Troca a Sbase **preservando as potências físicas** (MW/Mvar).

        P/Q são guardados em pu na base do sistema; trocar a base sem reescalar
        mudaria silenciosamente os MW de cada barra. Reescala P/Q pelo fator
        ``base_antiga / base_nova`` para que os valores em MW não se alterem.
        Ignora valores não-positivos (o núcleo exige Sbase > 0).
        """
        novo = float(novo)
        if novo <= 0:
            return
        antiga = float(self.params_fluxo.get("Sbase", 100.0))
        fator = antiga / novo
        if fator != 1.0:
            for b in self.barras:
                b["P"] = b.get("P", 0.0) * fator
                b["Q"] = b.get("Q", 0.0) * fator
        self.params_fluxo["Sbase"] = novo
        self.resultado_fluxo = None
        self.resultado_curto = None

    # ------------------------------------------------------------------ resumo
    def estado_itens(self) -> list[dict]:
        """Itens do painel 'estado do projeto' — 5 itens, espelha o modelo.

        Cada item: ``label`` (com a contagem embutida), ``ok`` e ``warn``. O
        texto do selo ('pronto'/'pendente'/'vazio') é derivado na camada de UI.
        """
        from gui import diagrama
        nb, nr = len(self.barras), len(self.ramos)
        valido = diagrama.eh_valido(self.barras, self.ramos)
        fluxo_ok = bool((self.resultado_fluxo or {}).get("convergiu"))
        curto_ok = bool(self.resultado_curto) and not (self.resultado_curto or {}).get("erro")
        return [
            {"chave": "barras", "label": f"Barras definidas ({nb})",
             "ok": nb > 0, "warn": False},
            {"chave": "ramos", "label": f"Ramos definidos ({nr})",
             "ok": nr > 0, "warn": False},
            {"chave": "valido", "label": "Sistema válido",
             "ok": valido, "warn": not valido},
            {"chave": "fluxo", "label": "Fluxo de potência",
             "ok": fluxo_ok, "warn": False},
            {"chave": "curto", "label": "Curto-circuito (fase 3)",
             "ok": curto_ok, "warn": False},
        ]

    def progresso(self) -> float:
        itens = self.estado_itens()
        return sum(1 for it in itens if it["ok"]) / len(itens)


# --------------------------------------------------------------- estado por aba
def projeto_da_aba() -> Projeto:
    """Devolve o ``Projeto`` da aba atual (cria/desserializa sob demanda).

    Importa ``nicegui`` preguiçosamente para manter este módulo testável sem
    navegador.
    """
    from nicegui import app
    armazem = app.storage.tab
    dados = armazem.get("projeto")
    proj = Projeto.from_dict(dados) if dados else Projeto.vazio()
    return proj


def salvar_na_aba(proj: Projeto) -> None:
    from nicegui import app
    app.storage.tab["projeto"] = proj.to_dict()
