import json
import time
import warnings
from dataclasses import dataclass

import numpy as np

# Modulo minimo de Y[i, j] para considerar duas barras conectadas.
# Evita comparacoes de igualdade exata com complexos (sujeitas a erro de ponto flutuante).
TOL_CONEXAO = 1e-12


@dataclass
class Linha:
    """Ramo (linha ou transformador) para o calculo exato de transito/perdas.

    Modelo pi com tap (convencao MATPOWER, defasagem nula): a susceptancia b e
    o carregamento shunt TOTAL da linha (metade em cada extremidade); o tap
    refere a extremidade 'de'.
    """
    de: int          # 1-based
    para: int        # 1-based
    z: complex       # impedancia serie (pu)
    b: float = 0.0   # susceptancia shunt total da linha (modelo pi)
    tap: float = 1.0


class Barra:
    """Barra (no) do sistema eletrico.

    tipo: 1 = PQ, 2 = PV, 3 = Slack (referencia).
    V em pu, theta em radianos, P/Q injetados em pu (ou na base usada).
    """

    def __init__(self, indice: int, tipo: int, V: float, theta: float,
                 P: float, Q: float) -> None:
        if tipo not in (1, 2, 3):
            raise ValueError(
                f"tipo de barra invalido: {tipo!r} (esperado 1=PQ, 2=PV, 3=Slack)"
            )
        if V <= 0:
            raise ValueError(f"tensao V deve ser > 0 (recebido {V!r})")
        self.indice = indice  # Indice da barra (0-based)
        self.tipo = tipo      # 1 = PQ, 2 = PV, 3 = Slack
        self.V = float(V)     # Tensao na barra (pu)
        self.theta = float(theta)  # Angulo de fase (rad)
        self.P = float(P)     # Potencia ativa injetada
        self.Q = float(Q)     # Potencia reativa injetada


class SistemaPotencia:
    """Resolve o fluxo de potencia por Newton-Raphson.

    A barra slack (tipo 3) pode ocupar qualquer posicao da lista de barras; o
    construtor exige exatamente uma barra tipo 3 e guarda sua posicao em
    self.slack_idx. O Jacobiano e a atualizacao de estado usam listas explicitas
    de indices nao-slack e PQ (em vez de assumir a slack no indice 0).

    Apos calcular_fluxo():
      - self.convergiu  -> bool indicando se o metodo convergiu.
      - self.convergencia -> numero de iteracoes ate convergir (None se nao convergiu).
    """

    def __init__(self, barras, Y, tolerancia: float = 1e-6,
                 max_iter: int = 100, Sbase: float = 100, linhas=None) -> None:
        n = len(barras)
        Y = np.asarray(Y)
        if Y.shape != (n, n):
            raise ValueError(f"matriz Y deve ser {n}x{n}, recebida {Y.shape}")
        if tolerancia <= 0:
            raise ValueError("tolerancia deve ser > 0")
        if max_iter < 1:
            raise ValueError("max_iter deve ser >= 1")
        if Sbase <= 0:
            raise ValueError("Sbase deve ser > 0")
        slacks = [i for i, b in enumerate(barras) if b.tipo == 3]
        if len(slacks) != 1:
            raise ValueError(
                f"sistema deve ter exatamente uma barra slack (tipo 3); "
                f"encontradas {len(slacks)}"
            )
        if linhas is not None:
            linhas = list(linhas)
            for lin in linhas:
                if not (1 <= lin.de <= n) or not (1 <= lin.para <= n):
                    raise ValueError(
                        f"linha {lin.de}-{lin.para}: indice fora da faixa [1, {n}]"
                    )
                if lin.de == lin.para:
                    raise ValueError(
                        f"linha invalida: 'de' == 'para' == {lin.de}"
                    )
                if lin.z == 0:
                    raise ValueError(
                        f"linha {lin.de}-{lin.para}: impedancia serie z nao pode ser 0"
                    )
                if lin.tap == 0:
                    raise ValueError(
                        f"linha {lin.de}-{lin.para}: tap nao pode ser 0"
                    )

        self.barras = barras  # Lista de objetos Barra
        self.slack_idx = slacks[0]  # Indice (0-based) da barra slack, em qualquer posicao
        self.Y = Y            # Matriz de admitancias
        self.linhas = linhas  # Dados de ramo (None => transito aproximado via Ybus)
        self.n_barras = n
        self.tolerancia = tolerancia
        self.max_iter = max_iter
        self.sbase = Sbase
        self.convergencia = None
        self.convergiu = False

    def _validar_indice_1based(self, indice: int) -> None:
        if not (1 <= indice <= self.n_barras):
            raise ValueError(
                f"indice {indice} fora da faixa [1, {self.n_barras}]"
            )

    def v(self, indice: int) -> float:
        """Retorna a tensao em pu da barra `indice` (1-based)."""
        self._validar_indice_1based(indice)
        return self.barras[indice - 1].V

    def theta(self, indice: int) -> float:
        """Retorna o angulo em radianos da barra `indice` (1-based)."""
        self._validar_indice_1based(indice)
        return self.barras[indice - 1].theta

    def inicializar_estado(self):
        """Inicializa os vetores de tensoes e angulos."""
        V = np.array([barra.V for barra in self.barras], dtype=float)
        theta = np.array([barra.theta for barra in self.barras], dtype=float)
        return V, theta

    def alterar_barra(self, indice: int, tipo=None, V=None, theta=None,
                      P=None, Q=None) -> None:
        """Altera as propriedades de uma barra (`indice` 1-based)."""
        self._validar_indice_1based(indice)
        barra = self.barras[indice - 1]
        if tipo is not None:
            if tipo not in (1, 2, 3):
                raise ValueError(f"tipo de barra invalido: {tipo!r}")
            # Preserva o invariante validado no construtor: exatamente 1 slack.
            tipos = [b.tipo for b in self.barras]
            tipos[indice - 1] = tipo
            n_slacks = tipos.count(3)
            if n_slacks != 1:
                raise ValueError(
                    f"alteracao deixaria o sistema com {n_slacks} barras slack "
                    f"(tipo 3); deve haver exatamente 1"
                )
            barra.tipo = tipo
            self.slack_idx = tipos.index(3)
        if V is not None:
            if V <= 0:
                raise ValueError(f"tensao V deve ser > 0 (recebido {V!r})")
            barra.V = float(V)
        if theta is not None:
            barra.theta = float(theta)
        if P is not None:
            barra.P = float(P)
        if Q is not None:
            barra.Q = float(Q)

    def calcular_fluxo(self) -> None:
        """Resolve o fluxo de potencia usando o metodo de Newton-Raphson."""
        start_time = time.time()
        V, theta = self.inicializar_estado()

        self.convergiu = False
        self.convergencia = None
        for k in range(self.max_iter):
            P_calc, Q_calc = self.fluxo_potencia(V, theta)
            dP, dQ = self.calcular_desvios(P_calc, Q_calc)
            dX = np.concatenate([dP, dQ])

            # Jacobiano no ponto atual (necessario tambem para a sensibilidade).
            J = self.calcular_jacobiano(V, theta, P_calc, Q_calc)
            self.ultimajacobiana = J

            if np.linalg.norm(dX) < self.tolerancia:
                self.convergencia = k + 1
                self.convergiu = True
                break

            try:
                delta_X = np.linalg.solve(J, dX)
            except np.linalg.LinAlgError as exc:
                raise np.linalg.LinAlgError(
                    "Jacobiano singular — sistema mal-condicionado ou ilhado."
                ) from exc

            # Atualiza theta (barras nao-slack) e V (barras PQ).
            # A slack mantem theta fixo (indice fora de nao_slack); os PV mantem
            # V fixo (indice fora de indices_pq).
            nao_slack = [i for i, b in enumerate(self.barras) if b.tipo != 3]
            indices_pq = [i for i, b in enumerate(self.barras) if b.tipo == 1]
            delta_theta = delta_X[:len(nao_slack)]
            delta_V = delta_X[len(nao_slack):]
            for idx, i in enumerate(nao_slack):
                theta[i] += delta_theta[idx]
            for idx, i in enumerate(indices_pq):
                V[i] += delta_V[idx]

        # Atualiza os valores de V e theta nas barras.
        for i, barra in enumerate(self.barras):
            barra.V = V[i]
            barra.theta = theta[i]

        # Grava as injecoes resolvidas onde elas eram incognitas: P e Q da
        # slack e Q das barras PV. Os alvos das PQ nao sao tocados, entao
        # re-resolver o sistema continua dando o mesmo resultado.
        if self.convergiu:
            for i, barra in enumerate(self.barras):
                if barra.tipo == 3:
                    barra.P = float(P_calc[i])
                    barra.Q = float(Q_calc[i])
                elif barra.tipo == 2:
                    barra.Q = float(Q_calc[i])

        self.tempo = time.time() - start_time

        if not self.convergiu:
            warnings.warn(
                f"Fluxo de potencia nao convergiu em {self.max_iter} iteracoes "
                f"(tolerancia {self.tolerancia})."
            )

    def calcular_desvios(self, P_calc, Q_calc):
        dP = np.array([b.P - P_calc[i] for i, b in enumerate(self.barras)
                       if b.tipo != 3])
        dQ = np.array([b.Q - Q_calc[i] for i, b in enumerate(self.barras)
                       if b.tipo == 1])
        return dP, dQ

    def calcular_jacobiano(self, V, theta, P_calc, Q_calc):
        # Indices das barras nao-slack e PQ, em ordem crescente (mesma ordenacao
        # usada por calcular_desvios para montar dX). A slack pode estar em
        # qualquer posicao: nao_slack simplesmente nao a inclui.
        nao_slack = [i for i, b in enumerate(self.barras) if b.tipo != 3]
        pq_indices = [i for i, b in enumerate(self.barras) if b.tipo == 1]
        n_ns = len(nao_slack)
        n_pq = len(pq_indices)
        H = np.zeros((n_ns, n_ns))
        N = np.zeros((n_ns, n_pq))
        M = np.zeros((n_pq, n_ns))
        L = np.zeros((n_pq, n_pq))

        # Calculo de H (derivada de P em relacao a theta).
        for idx_i, i in enumerate(nao_slack):
            for idx_j, j in enumerate(nao_slack):
                if i == j:
                    H[idx_i, idx_j] = -Q_calc[i] - (V[i] ** 2) * self.Y[i, i].imag
                else:
                    H[idx_i, idx_j] = V[i] * V[j] * (
                        self.Y[i, j].real * np.sin(theta[i] - theta[j])
                        - self.Y[i, j].imag * np.cos(theta[i] - theta[j]))

        # Calculo de N (derivada de P em relacao a V).
        for idx_i, i in enumerate(nao_slack):
            for idx_j, j in enumerate(pq_indices):
                if i == j:
                    soma = 0
                    for k in range(self.n_barras):
                        if k != i:
                            soma += V[k] * (
                                self.Y[i, k].real * np.cos(theta[i] - theta[k])
                                + self.Y[i, k].imag * np.sin(theta[i] - theta[k]))
                    N[idx_i, idx_j] = 2 * V[i] * self.Y[i, i].real + soma
                else:
                    N[idx_i, idx_j] = V[i] * (
                        self.Y[i, j].real * np.cos(theta[i] - theta[j])
                        + self.Y[i, j].imag * np.sin(theta[i] - theta[j]))

        # Calculo de M (derivada de Q em relacao a theta).
        for idx_i, i in enumerate(pq_indices):
            for idx_j, j in enumerate(nao_slack):
                if i == j:
                    M[idx_i, idx_j] = P_calc[i] - (V[i] ** 2) * self.Y[i, i].real
                else:
                    M[idx_i, idx_j] = -V[i] * V[j] * (
                        self.Y[i, j].real * np.cos(theta[i] - theta[j])
                        + self.Y[i, j].imag * np.sin(theta[i] - theta[j]))

        # Calculo de L (derivada de Q em relacao a V).
        for idx_i, i in enumerate(pq_indices):
            for idx_j, j in enumerate(pq_indices):
                if i == j:
                    soma = 0
                    for k in range(self.n_barras):
                        if k != i:
                            soma += V[k] * (
                                self.Y[i, k].real * np.sin(theta[i] - theta[k])
                                - self.Y[i, k].imag * np.cos(theta[i] - theta[k]))
                    L[idx_i, idx_j] = -2 * V[i] * self.Y[i, i].imag + soma
                else:
                    L[idx_i, idx_j] = V[i] * (
                        self.Y[i, j].real * np.sin(theta[i] - theta[j])
                        - self.Y[i, j].imag * np.cos(theta[i] - theta[j]))

        # Monta a Jacobiana a partir das submatrizes das derivadas de P e Q.
        return np.block([[H, N], [M, L]])

    def fluxo_potencia(self, V, theta):
        """Calcula a potencia ativa e reativa injetada em cada barra."""
        P_calc = np.zeros(self.n_barras)
        Q_calc = np.zeros(self.n_barras)

        for i in range(self.n_barras):
            for j in range(self.n_barras):
                P_calc[i] += V[i] * V[j] * (
                    self.Y[i, j].real * np.cos(theta[i] - theta[j])
                    + self.Y[i, j].imag * np.sin(theta[i] - theta[j]))
                Q_calc[i] += V[i] * V[j] * (
                    self.Y[i, j].real * np.sin(theta[i] - theta[j])
                    - self.Y[i, j].imag * np.cos(theta[i] - theta[j]))
        return P_calc, Q_calc

    def transito(self, de: int, para: int):
        """Calcula o transito de potencia entre duas barras (1-based).

        Convencao: S_ij e a potencia que SAI da barra `de` em direcao a `para`,
        medida na extremidade `de` (positiva no sentido de -> para).

        Com `linhas` fornecidas no construtor, usa o modelo pi com tap
        (MATPOWER) e soma os ramos paralelos entre o par — exato inclusive com
        tap e carregamento shunt. Sem `linhas`, usa -Y[de, para] * (Vi - Vj),
        exato apenas para ramo serie puro (sem tap nem carregamento).
        """
        self._validar_indice_1based(de)
        self._validar_indice_1based(para)
        if de == para:
            raise ValueError("as barras 'de' e 'para' devem ser diferentes")
        i = de - 1
        j = para - 1

        # Tensoes complexas nas barras.
        Vi = self.barras[i].V * (np.cos(self.barras[i].theta) + 1j * np.sin(self.barras[i].theta))
        Vj = self.barras[j].V * (np.cos(self.barras[j].theta) + 1j * np.sin(self.barras[j].theta))

        if self.linhas is not None:
            # Corrente total saindo de `de`, somando ramos paralelos.
            I_ij = 0.0 + 0.0j
            achou = False
            for lin in self.linhas:
                ys = 1.0 / lin.z
                bc = 1j * lin.b / 2.0
                tap = lin.tap
                if lin.de == de and lin.para == para:
                    # Lado 'de' do ramo (referido pelo tap).
                    I_ij += (ys + bc) / (tap * tap) * Vi - (ys / tap) * Vj
                    achou = True
                elif lin.de == para and lin.para == de:
                    # Lado 'para' do ramo.
                    I_ij += (ys + bc) * Vi - (ys / tap) * Vj
                    achou = True
            if not achou:
                raise ValueError(
                    f"nao ha linha entre as barras {de} e {para}"
                )
        else:
            # Y[i, j] = -y_serie (convencao Ybus): corrente de i para j.
            I_ij = -self.Y[i, j] * (Vi - Vj)

        # Potencia complexa de i para j.
        S_ij = Vi * np.conj(I_ij)
        P_ij = S_ij.real
        Q_ij = S_ij.imag

        return {"S_ij": S_ij, "P_ij": P_ij, "Q_ij": Q_ij}

    def losses(self, de: int, para: int):
        """Calcula as perdas de potencia na linha entre duas barras.

        P_loss e Q_loss sao somas com sinal das duas extremidades: P_loss >= 0
        em rede passiva; Q_loss negativo indica que a linha gera reativo
        (carregamento capacitivo). S_loss e o modulo da perda complexa.
        """
        transito_ij = self.transito(de, para)
        transito_ji = self.transito(para, de)

        S_loss = abs(transito_ij["S_ij"] + transito_ji["S_ij"])
        P_loss = transito_ij["P_ij"] + transito_ji["P_ij"]
        Q_loss = transito_ij["Q_ij"] + transito_ji["Q_ij"]

        return {"S_loss": S_loss, "P_loss": P_loss, "Q_loss": Q_loss}

    def _pares_conectados(self):
        """Gera pares (i, j) 0-based com i < j conectados.

        Com `linhas`, os pares vem da lista de ramos (paralelos deduplicados);
        sem, da varredura da Ybus (|Y[i, j]| > TOL_CONEXAO).
        """
        if self.linhas is not None:
            vistos = set()
            for lin in self.linhas:
                par = (min(lin.de, lin.para) - 1, max(lin.de, lin.para) - 1)
                if par not in vistos:
                    vistos.add(par)
                    yield par
            return
        for i in range(self.n_barras):
            for j in range(i + 1, self.n_barras):
                if abs(self.Y[i, j]) > TOL_CONEXAO:
                    yield i, j

    def totlosses(self):
        """Calcula as perdas totais de potencia ativa e reativa do sistema."""
        total_P_loss = 0.0
        total_Q_loss = 0.0
        for i, j in self._pares_conectados():
            perdas = self.losses(i + 1, j + 1)
            total_P_loss += perdas["P_loss"]
            total_Q_loss += perdas["Q_loss"]
        return {"P_loss": total_P_loss, "Q_loss": total_Q_loss}

    def calcular_sensibilidade(self):
        """Retorna a matriz de sensibilidade (inversa da ultima Jacobiana)."""
        if not hasattr(self, 'ultimajacobiana'):
            raise ValueError(
                "A Jacobiana ainda nao foi calculada. Rode calcular_fluxo() antes."
            )
        try:
            return np.linalg.inv(self.ultimajacobiana)
        except np.linalg.LinAlgError as exc:
            raise np.linalg.LinAlgError(
                "Jacobiano singular — sensibilidade indefinida."
            ) from exc

    def exportar(self, arquivo: str = "sistema.json") -> None:
        """Exporta todas as informacoes do sistema para um arquivo JSON."""
        def serializar_valor(valor):
            """Converte valores complexos/numpy em um formato serializavel."""
            if isinstance(valor, (complex, np.complexfloating)):
                return {"real": float(valor.real), "imag": float(valor.imag)}
            if isinstance(valor, np.ndarray):
                return valor.tolist()
            if isinstance(valor, np.integer):
                return int(valor)
            if isinstance(valor, np.floating):
                return float(valor)
            return valor

        fluxos = []
        for i, j in self._pares_conectados():
            fluxos.append({
                "linha": f"{i + 1} -> {j + 1}",
                **{c: serializar_valor(v) for c, v in self.transito(i + 1, j + 1).items()}
            })
            fluxos.append({
                "linha": f"{j + 1} -> {i + 1}",
                **{c: serializar_valor(v) for c, v in self.transito(j + 1, i + 1).items()}
            })

        dados = {
            "barras": [
                {
                    "indice": barra.indice + 1,
                    "tipo": barra.tipo,
                    "tensao": serializar_valor(barra.V),
                    "angulo": serializar_valor(barra.theta),
                    "potencia_ativa": serializar_valor(barra.P),
                    "potencia_reativa": serializar_valor(barra.Q)
                }
                for barra in self.barras
            ],
            "fluxos": fluxos,
            "perdas": self.totlosses(),
            "parametros": {
                "tolerancia": self.tolerancia,
                "max_iteracoes": self.max_iter,
                "sbase": self.sbase,
                "convergiu": self.convergiu,
                "tempo_solucao": getattr(self, 'tempo', None)
            },
            "matriz_admitancia": [
                [serializar_valor(self.Y[i, j]) for j in range(self.n_barras)]
                for i in range(self.n_barras)
            ]
        }

        try:
            with open(arquivo, 'w') as f:
                json.dump(dados, f, indent=4)
        except OSError as exc:
            raise OSError(f"Falha ao exportar para '{arquivo}': {exc}") from exc
        print(f"Informacoes exportadas para {arquivo}.")

    def imprimir_estado(self, cd: int = 4) -> None:
        print("Estado do Sistema:")
        print("-" * 40)
        for barra in self.barras:
            print(f"Barra {barra.indice + 1}: V = {barra.V:.{cd}f} pu, "
                  f"theta = {barra.theta:.{cd}f} rad")
        print("-" * 40)

    def imprimir_transito(self, cd: int = 4) -> None:
        """Imprime o transito de potencia em todas as linhas do sistema."""
        print("Transito de Potencias:")
        print("-" * 40)
        for i, j in self._pares_conectados():
            transito = self.transito(i + 1, j + 1)
            print(f"Linha {i + 1} -> {j + 1}: "
                  f"P = {transito['P_ij']:.{cd}f} pu, Q = {transito['Q_ij']:.{cd}f} pu")
        print("-" * 40)

    def imprimir_perdas(self, cd: int = 4) -> None:
        """Imprime as perdas de potencia em todas as linhas do sistema."""
        print("Perdas de Potencia nas Linhas:")
        print("-" * 40)
        for i, j in self._pares_conectados():
            perdas = self.losses(i + 1, j + 1)
            print(f"Linha {i + 1} -> {j + 1}: "
                  f"P_loss = {perdas['P_loss']:.{cd}f} pu, "
                  f"Q_loss = {perdas['Q_loss']:.{cd}f} pu")
        print("-" * 40)
