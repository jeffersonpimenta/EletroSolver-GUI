"""Analise de curto-circuito (corrente de faltas) por componentes simetricas.

Monta as redes de sequencia positiva, negativa e zero a partir dos dados de
geradores, ramos (linhas/trafos) e cargas, e calcula:
  - falta trifasica simetrica (3f);
  - falta monofasica (fase-terra, FT);
  - falta bifasica (fase-fase, FF);
  - falta bifasica-terra (FFT).

E independente do caminho de fluxo de potencia: usa o SistemaPotencia apenas
para n_barras, base (Sbase) e, opcionalmente, as tensoes pre-falta convergidas.

Convencao de componentes simetricas: fase = A @ sequencia, com a ordem de
sequencia [zero, positiva, negativa] = [I0, I1, I2].

As "contribuicoes" (por ramo, gerador e carga) sao dadas no sentido de
superposicao (rede de variacao): quanto de corrente cada elemento injeta em
direcao a falta em relacao ao estado pre-falta. Por construcao, a soma das
contribuicoes que chegam a barra em falta e igual a corrente de falta (KCL).
"""
from dataclasses import dataclass

import numpy as np

# Operador de rotacao de 120 graus.
ALFA = np.exp(2j * np.pi / 3)

# Matriz de transformacao: fase = A @ sequencia ([I0, I1, I2]).
A = np.array([
    [1, 1, 1],
    [1, ALFA ** 2, ALFA],
    [1, ALFA, ALFA ** 2],
])

# Modulo minimo de tensao para tratar uma barra como energizada (evita divisao
# por zero ao converter carga em admitancia).
TOL_TENSAO = 1e-9

# Ligacoes de transformador que conduzem sequencia zero atraves dos enrolamentos.
_LIGACOES_PASSANTES = ("linha", "YNyn")
# Ligacoes que aterram apenas o lado estrela-aterrado (delta isola o outro lado).
_LIGACOES_ATERRAM_DE = ("YNd",)     # estrela aterrada no 'de', delta no 'para'
_LIGACOES_ATERRAM_PARA = ("Dyn",)   # delta no 'de', estrela aterrada no 'para'
# Ligacoes que bloqueiam totalmente a sequencia zero.
_LIGACOES_BLOQUEIO = ("Dd", "Yy", "Yyn", "YNy")


@dataclass
class Gerador:
    """Maquina sincrona vista pela falta (reatancias subtransitorias, pu).

    X1 = X''d (sequencia positiva); X2 default = X1; X0 e Zn so entram na
    sequencia zero e somente se `aterrado`. Zn entra como 3*Zn.
    """
    barra: int                 # 1-based
    X1: float                  # = X''d, pu
    X2: float = None           # None => assume X1
    X0: float = None           # None => nao contribui em sequencia zero
    Zn: complex = 0.0          # impedancia de aterramento do neutro (entra como 3*Zn)
    aterrado: bool = True      # False => sem caminho de terra em sequencia zero
    R1: float = 0.0
    R2: float = 0.0
    R0: float = 0.0


@dataclass
class Ramo:
    """Linha ou transformador, com impedancias de sequencia (pu).

    b1/b0 sao a susceptancia shunt TOTAL da linha (carregamento capacitivo) nas
    sequencias positiva/negativa e zero, modelo pi (metade em cada extremidade).
    """
    de: int                    # 1-based
    para: int                  # 1-based
    z1: complex                # serie sequencia positiva
    z2: complex = None         # None => assume z1
    z0: complex = None         # obrigatoria p/ FT/FFT; roteada por `ligacao`
    b1: float = 0.0            # shunt total sequencia +/- (carregamento de linha)
    b0: float = 0.0            # shunt total sequencia zero (carregamento de linha)
    ligacao: str = "linha"     # "linha"|"YNyn"|"Dyn"|"YNd"|"Dd"|"Yy"|"Yyn"|"YNy"
    tap: float = 1.0


@dataclass
class Carga:
    """Carga modelada como impedancia constante (P, Q consumidos em pu).

    Y_L = conj(P + jQ) / |Vpre|^2, aplicada em sequencia positiva e negativa.
    Sequencia zero e omitida (carga tipicamente em delta ou nao aterrada).
    """
    barra: int                 # 1-based
    P: float                   # potencia ativa consumida, pu
    Q: float                   # potencia reativa consumida, pu (>0 indutiva)


class EstudoCurtoCircuito:
    """Estudo de curto-circuito por componentes simetricas.

    Recebe um SistemaPotencia ja construido (para n_barras, Sbase e tensoes
    pre-falta), a lista de geradores, a lista de ramos e, opcionalmente, a lista
    de cargas. Indexacao da API e 1-based (compativel com o restante do projeto).
    """

    def __init__(self, sistema, geradores, ramos, cargas=None,
                 incluir_cargas=True, incluir_shunt_linha=True,
                 prefault="flat"):
        if not geradores:
            raise ValueError(
                "e necessario ao menos um gerador (caminho de terra das "
                "sequencias positiva/negativa)."
            )
        if prefault not in ("flat", "fluxo"):
            raise ValueError(
                f"prefault invalido: {prefault!r} (use 'flat' ou 'fluxo')"
            )

        self.sistema = sistema
        self.n = sistema.n_barras
        self.sbase = sistema.sbase
        self.geradores = list(geradores)
        self.ramos = list(ramos)
        self.cargas = list(cargas) if cargas else []
        self.incluir_cargas = incluir_cargas
        self.incluir_shunt_linha = incluir_shunt_linha
        self.prefault = prefault

        # Validacao de indices.
        for g in self.geradores:
            self._validar_indice(g.barra)
        for r in self.ramos:
            self._validar_indice(r.de)
            self._validar_indice(r.para)
            if r.de == r.para:
                raise ValueError(
                    f"ramo invalido: 'de' == 'para' == {r.de}"
                )
        for c in self.cargas:
            self._validar_indice(c.barra)

        # Tensoes pre-falta (sequencia positiva) e admitancias de carga por barra.
        self.Vpre = self._tensoes_prefalta()
        self.Yc = self._admitancias_carga()

        # Carregamento capacitivo de linha, agregado por barra (shunt a terra).
        self.bsh1 = self._shunt_carregamento("pos")   # seq. positiva/negativa
        self._bsh0_vec = None                          # seq. zero (sob demanda)

        # Redes de sequencia positiva e negativa (Z0 e calculada sob demanda).
        self.Y1 = self._montar_y_seq("pos")
        self.Y2 = self._montar_y_seq("neg")
        self.Z1 = self._inverter(self.Y1, "positiva")
        self.Z2 = self._inverter(self.Y2, "negativa")
        self._Y0 = None
        self._Z0 = None

    # ------------------------------------------------------------------ utils
    def _validar_indice(self, indice: int) -> None:
        if not (1 <= indice <= self.n):
            raise ValueError(f"indice {indice} fora da faixa [1, {self.n}]")

    @staticmethod
    def _para_fase(I0, I1, I2):
        """Converte componentes de sequencia em fasores de fase a, b, c."""
        Iabc = A @ np.array([I0, I1, I2])
        return {"a": Iabc[0], "b": Iabc[1], "c": Iabc[2]}

    def _tensoes_prefalta(self):
        if self.prefault == "flat":
            return np.ones(self.n, dtype=complex)
        if not getattr(self.sistema, "convergiu", False):
            raise ValueError(
                "prefault='fluxo' exige fluxo de potencia convergido "
                "(rode sistema.calcular_fluxo() antes)."
            )
        return np.array(
            [b.V * np.exp(1j * b.theta) for b in self.sistema.barras],
            dtype=complex,
        )

    def _admitancias_carga(self):
        """Admitancia shunt equivalente de cada carga (sequencia +/-)."""
        Yc = np.zeros(self.n, dtype=complex)
        if not self.incluir_cargas:
            return Yc
        for c in self.cargas:
            k = c.barra - 1
            vmag2 = abs(self.Vpre[k]) ** 2
            if vmag2 < TOL_TENSAO:
                continue
            Yc[k] += np.conj(complex(c.P, c.Q)) / vmag2
        return Yc

    @staticmethod
    def _estampar_serie(Y, i, j, ys, tap, bc=0.0):
        """Estampa um ramo serie com tap (modelo MATPOWER, defasagem nula)."""
        Y[i, i] += (ys + bc) / (tap * tap)
        Y[j, j] += ys + bc
        Y[i, j] += -ys / tap
        Y[j, i] += -ys / tap

    def _shunt_carregamento(self, seq):
        """Susceptancia shunt de linha agregada por barra (modelo pi).

        seq 'pos'/'neg' usa b1; 'zero' usa b0 e so para ramos que conduzem
        sequencia zero (linha/YNyn). Metade do carregamento em cada extremidade,
        com a extremidade 'de' referida pelo tap (consistente com a serie).
        """
        bsh = np.zeros(self.n, dtype=complex)
        if not self.incluir_shunt_linha:
            return bsh
        for r in self.ramos:
            i, j = r.de - 1, r.para - 1
            tap = r.tap if r.tap else 1.0
            if seq == "zero":
                if r.ligacao not in _LIGACOES_PASSANTES:
                    continue
                bc = 1j * r.b0 / 2.0
            else:
                bc = 1j * r.b1 / 2.0
            if bc == 0:
                continue
            bsh[i] += bc / (tap * tap)
            bsh[j] += bc
        return bsh

    def _bsh0(self):
        if self._bsh0_vec is None:
            self._bsh0_vec = self._shunt_carregamento("zero")
        return self._bsh0_vec

    # ------------------------------------------------------- montagem das Ybus
    def _montar_y_seq(self, seq):
        """Monta Y de sequencia positiva ('pos') ou negativa ('neg')."""
        Y = np.zeros((self.n, self.n), dtype=complex)
        for r in self.ramos:
            i, j = r.de - 1, r.para - 1
            if seq == "pos":
                z = r.z1
            else:
                z = r.z2 if r.z2 is not None else r.z1
            ys = 1.0 / z
            tap = r.tap if r.tap else 1.0
            bc = 1j * r.b1 / 2.0 if self.incluir_shunt_linha else 0.0
            self._estampar_serie(Y, i, j, ys, tap, bc)

        for g in self.geradores:
            k = g.barra - 1
            if seq == "pos":
                Y[k, k] += 1.0 / complex(g.R1, g.X1)
            else:
                X2 = g.X2 if g.X2 is not None else g.X1
                Y[k, k] += 1.0 / complex(g.R2, X2)

        # Cargas como shunt (zeros se incluir_cargas=False).
        for k in range(self.n):
            Y[k, k] += self.Yc[k]
        return Y

    def _montar_y0(self):
        """Monta a Ybus de sequencia zero, roteada pelas conexoes dos ramos."""
        Y = np.zeros((self.n, self.n), dtype=complex)
        for r in self.ramos:
            i, j = r.de - 1, r.para - 1
            lig = r.ligacao
            if lig in _LIGACOES_PASSANTES:
                if r.z0 is None:
                    raise ValueError(
                        f"ramo {r.de}-{r.para}: z0 ausente "
                        f"(necessaria para sequencia zero)"
                    )
                ys = 1.0 / r.z0
                tap = r.tap if r.tap else 1.0
                bc = 1j * r.b0 / 2.0 if self.incluir_shunt_linha else 0.0
                self._estampar_serie(Y, i, j, ys, tap, bc)
            elif lig in _LIGACOES_ATERRAM_DE:
                if r.z0 is None:
                    raise ValueError(f"ramo {r.de}-{r.para}: z0 ausente")
                Y[i, i] += 1.0 / r.z0
            elif lig in _LIGACOES_ATERRAM_PARA:
                if r.z0 is None:
                    raise ValueError(f"ramo {r.de}-{r.para}: z0 ausente")
                Y[j, j] += 1.0 / r.z0
            elif lig in _LIGACOES_BLOQUEIO:
                continue
            else:
                raise ValueError(f"ligacao desconhecida: {lig!r}")

        for g in self.geradores:
            if g.aterrado and g.X0 is not None:
                k = g.barra - 1
                Y[k, k] += 1.0 / (complex(g.R0, g.X0) + 3 * g.Zn)
        return Y

    @staticmethod
    def _inverter(Y, nome):
        try:
            return np.linalg.inv(Y)
        except np.linalg.LinAlgError as exc:
            raise np.linalg.LinAlgError(
                f"rede de sequencia {nome} singular - verifique aterramento/"
                f"conexoes (sem caminho para o terra?)."
            ) from exc

    @property
    def Z0(self):
        """Matriz de impedancia de sequencia zero (calculada sob demanda)."""
        if self._Z0 is None:
            self._Y0 = self._montar_y0()
            self._Z0 = self._inverter(self._Y0, "zero")
        return self._Z0

    # ------------------------------------------------------------- resultados
    def _montar_resultado(self, tipo, k, I0, I1, I2, usar_z0):
        Vpre = self.Vpre
        V1 = Vpre - self.Z1[:, k] * I1
        V2 = -self.Z2[:, k] * I2
        if usar_z0:
            V0 = -self.Z0[:, k] * I0
        else:
            V0 = np.zeros(self.n, dtype=complex)

        # Tensoes de fase por barra (n x 3, colunas a/b/c).
        Vfase = (A @ np.vstack([V0, V1, V2])).T

        # Variacoes (rede de superposicao) para as contribuicoes.
        dV0, dV1, dV2 = V0, V1 - Vpre, V2

        return {
            "tipo": tipo,
            "barra": k + 1,
            "Vf": Vpre[k],
            "I_seq": (I0, I1, I2),
            "I_fase": self._para_fase(I0, I1, I2),
            "V_seq": (V0, V1, V2),
            "V_fase": Vfase,
            "contrib_linha": self._contrib_ramos(dV0, dV1, dV2),
            "contrib_gerador": self._contrib_geradores(V0, V1, V2),
            "contrib_carga": self._contrib_cargas(V0, V1, V2),
            "contrib_shunt_linha": self._contrib_shunt_linha(
                dV0, dV1, dV2, usar_z0),
        }

    def _contrib_ramos(self, dV0, dV1, dV2):
        linhas = []
        for r in self.ramos:
            i, j = r.de - 1, r.para - 1
            tap = r.tap if r.tap else 1.0
            y1 = 1.0 / r.z1
            y2 = 1.0 / (r.z2 if r.z2 is not None else r.z1)
            I1 = (y1 / tap) * (dV1[i] / tap - dV1[j])
            I2 = (y2 / tap) * (dV2[i] / tap - dV2[j])
            if r.ligacao in _LIGACOES_PASSANTES and r.z0 is not None:
                y0 = 1.0 / r.z0
                I0 = (y0 / tap) * (dV0[i] / tap - dV0[j])
            else:
                I0 = 0.0
            linhas.append({
                "linha": f"{r.de} -> {r.para}",
                "I_seq": (I0, I1, I2),
                "I_fase": self._para_fase(I0, I1, I2),
            })
        return linhas

    def _contrib_geradores(self, V0, V1, V2):
        out = []
        for g in self.geradores:
            k = g.barra - 1
            yg1 = 1.0 / complex(g.R1, g.X1)
            X2 = g.X2 if g.X2 is not None else g.X1
            yg2 = 1.0 / complex(g.R2, X2)
            Ig1 = yg1 * (self.Vpre[k] - V1[k])
            Ig2 = yg2 * (0.0 - V2[k])
            if g.aterrado and g.X0 is not None:
                yg0 = 1.0 / (complex(g.R0, g.X0) + 3 * g.Zn)
                Ig0 = yg0 * (0.0 - V0[k])
            else:
                Ig0 = 0.0
            out.append({
                "barra": g.barra,
                "I_seq": (Ig0, Ig1, Ig2),
                "I_fase": self._para_fase(Ig0, Ig1, Ig2),
            })
        return out

    def _contrib_shunt_linha(self, dV0, dV1, dV2, usar_z0):
        """Contribuicao capacitiva do carregamento de linha (shunt a terra).

        No sentido de superposicao, a corrente que cada shunt injeta em direcao
        a falta e -y_shunt * dV (dV = V_pos_falta - V_pre).
        """
        if not self.incluir_shunt_linha:
            return []
        bsh1 = self.bsh1
        bsh0 = self._bsh0() if usar_z0 else np.zeros(self.n, dtype=complex)
        out = []
        for bus in range(self.n):
            if abs(bsh1[bus]) < TOL_TENSAO and abs(bsh0[bus]) < TOL_TENSAO:
                continue
            I1 = -bsh1[bus] * dV1[bus]
            I2 = -bsh1[bus] * dV2[bus]
            I0 = -bsh0[bus] * dV0[bus]
            out.append({
                "barra": bus + 1,
                "I_seq": (I0, I1, I2),
                "I_fase": self._para_fase(I0, I1, I2),
            })
        return out

    def _contrib_cargas(self, V0, V1, V2):
        out = []
        if not self.incluir_cargas:
            return out
        for c in self.cargas:
            k = c.barra - 1
            vmag2 = abs(self.Vpre[k]) ** 2
            if vmag2 < TOL_TENSAO:
                continue
            yL = np.conj(complex(c.P, c.Q)) / vmag2
            Il1 = yL * (self.Vpre[k] - V1[k])
            Il2 = yL * (0.0 - V2[k])
            out.append({
                "barra": c.barra,
                "I_seq": (0.0, Il1, Il2),
                "I_fase": self._para_fase(0.0, Il1, Il2),
            })
        return out

    # ----------------------------------------------------------------- faltas
    def falta_trifasica(self, barra: int, Zf: complex = 0):
        """Falta trifasica simetrica na `barra` (1-based)."""
        self._validar_indice(barra)
        k = barra - 1
        I1 = self.Vpre[k] / (self.Z1[k, k] + Zf)
        return self._montar_resultado("trifasica", k, 0.0, I1, 0.0,
                                      usar_z0=False)

    def falta_monofasica(self, barra: int, Zf: complex = 0, Zg: complex = 0):
        """Falta monofasica (fase a - terra) na `barra` (1-based)."""
        self._validar_indice(barra)
        k = barra - 1
        Z1 = self.Z1[k, k]
        Z2 = self.Z2[k, k]
        Z0 = self.Z0[k, k]
        I = self.Vpre[k] / (Z1 + Z2 + Z0 + 3 * (Zf + Zg))
        return self._montar_resultado("monofasica", k, I, I, I, usar_z0=True)

    def falta_bifasica(self, barra: int, Zf: complex = 0):
        """Falta bifasica (fases b-c, sem terra) na `barra` (1-based)."""
        self._validar_indice(barra)
        k = barra - 1
        I1 = self.Vpre[k] / (self.Z1[k, k] + self.Z2[k, k] + Zf)
        return self._montar_resultado("bifasica", k, 0.0, I1, -I1,
                                      usar_z0=False)

    def falta_bifasica_terra(self, barra: int, Zf: complex = 0,
                             Zg: complex = 0):
        """Falta bifasica-terra (fases b-c + terra) na `barra` (1-based)."""
        self._validar_indice(barra)
        k = barra - 1
        Z1 = self.Z1[k, k]
        Za = self.Z2[k, k] + Zf
        Zb = self.Z0[k, k] + Zf + 3 * Zg
        I1 = self.Vpre[k] / (Z1 + Zf + (Za * Zb) / (Za + Zb))
        I2 = -I1 * Zb / (Za + Zb)
        I0 = -I1 * Za / (Za + Zb)
        return self._montar_resultado("bifasica_terra", k, I0, I1, I2,
                                      usar_z0=True)

    # ----------------------------------------------------------- relatorios
    def corrente_kA(self, I_pu: complex, kV_base: float) -> float:
        """Converte corrente em pu para kA, dada a tensao base de linha (kV)."""
        return abs(I_pu) * self.sbase / (np.sqrt(3) * kV_base)

    def potencia_curto_MVA(self, barra: int, tipo: str = "trifasica") -> float:
        """Potencia de curto-circuito (MVA) para o tipo de falta indicado."""
        metodo = {
            "trifasica": self.falta_trifasica,
            "monofasica": self.falta_monofasica,
            "bifasica": self.falta_bifasica,
            "bifasica_terra": self.falta_bifasica_terra,
        }.get(tipo)
        if metodo is None:
            raise ValueError(f"tipo de falta desconhecido: {tipo!r}")
        res = metodo(barra)
        I = max(abs(res["I_fase"][f]) for f in ("a", "b", "c"))
        return self.sbase * I

    def imprimir_falta(self, resultado, cd: int = 4) -> None:
        """Imprime o resumo de uma falta no estilo dos imprimir_* do projeto."""
        I = resultado["I_fase"]
        print(f"Falta {resultado['tipo']} na barra {resultado['barra']}:")
        print("-" * 40)
        for fase in ("a", "b", "c"):
            print(f"  I_{fase} = {abs(I[fase]):.{cd}f} pu "
                  f"/_ {np.degrees(np.angle(I[fase])):.{cd}f} graus")
        print("-" * 40)
