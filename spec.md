# EletroSolver-GUI — Documento de Design (spec)

- **Data:** 2026-06-17
- **Status:** aprovado (sessão de brainstorming)
- **Padrão de referência:** [`EarthSolver-GUI`](https://github.com/jeffersonpimenta/EarthSolver-GUI)
- **Núcleo a embrulhar:** [`EletroSolver`](https://github.com/jeffersonpimenta/EletroSolver)

---

## 1. Contexto e objetivo

`EletroSolver` é um solver de **sistemas elétricos de potência** em Python/numpy, com
duas análises:

1. **Fluxo de potência** por Newton-Raphson (`EletroSolver.py`).
2. **Curto-circuito** por componentes simétricas (`Faltas.py`).

Hoje o uso é via scripts (`Simplificado.py`, `Curtos.py`). O objetivo é uma
**interface web** que torne o motor utilizável sem código, **espelhando as
convenções, a stack e o sistema visual do `EarthSolver-GUI`** — porém adaptando a
metáfora de UI: `EarthSolver-GUI` é um *pipeline linear*; aqui o artefato central é
uma **rede** (barras + ramos) sobre a qual se rodam análises.

A GUI vive em repositório separado e consome **apenas a API pública** do núcleo — o
núcleo permanece intocado (ver §3).

## 2. Escopo

Implementação **faseada**. Esta spec projeta as duas análises, mas a primeira entrega
cobre o fluxo de potência; o curto-circuito é projetado aqui e implementado depois.

**Nesta entrega (fases 0–2):**
- Editor de **diagrama unifilar** (barras + ramos) com Ybus automática.
- **Fluxo de potência** completo (resultados, gráficos, export).
- **Visualizador** de resultados exportados.
- Casos **IEEE** prontos, import/export de projeto.

**Fase posterior (fase 3):**
- **Curto-circuito**: geradores, cargas, impedâncias de sequência por ramo, os 4
  tipos de falta, contribuições, fasores.

**Fora de escopo (YAGNI):**
- Autenticação/multiusuário/persistência em banco (estado é por aba do navegador).
- Edição colaborativa em tempo real.
- Curva de convergência por iteração (o núcleo só expõe contagem de iterações e
  tempo; uma curva por iteração exigiria mexer no núcleo — ver §7 e §13).
- Estabilidade transitória, despacho econômico, otimização — não existem no núcleo.

## 3. Dependência do núcleo (decisão)

`EarthSolver-GUI` declara o núcleo como `earthsolver @ git+https://...` (pacote
instalável). **`EletroSolver` não é empacotado**: são os módulos `EletroSolver.py` e
`Faltas.py` soltos na raiz, sem `pyproject.toml`.

**Decisão:** adicionar **apenas um `pyproject.toml`** ao repositório `EletroSolver`,
expondo os módulos de topo, **sem tocar no código**:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "eletrosolver"
version = "0.1.0"
requires-python = ">=3.10"
dependencies = ["numpy>=1.20"]

[tool.hatch.build.targets.wheel]
# ship os módulos de topo: habilita `import EletroSolver` / `import Faltas`
only-include = ["EletroSolver.py", "Faltas.py"]
```

A GUI então depende de `eletrosolver @ git+https://github.com/jeffersonpimenta/EletroSolver.git`
e importa `from EletroSolver import Barra, Linha, SistemaPotencia` /
`from Faltas import Gerador, Ramo, Carga, EstudoCurtoCircuito`. Mantém o padrão do
molde (consumir só a API pública; núcleo intocado).

> Em desenvolvimento, instalar o núcleo em modo editável a partir do repo vizinho
> (`pip install -e ..\EletroSolver`).

## 4. Stack e convenções (idênticas ao molde)

- **NiceGUI ≥ 2** (web), **Plotly** (gráficos), **numpy**.
- Build **hatchling**; entry point `eletrosolver-gui = "gui.main:main"`.
- **ruff** (`E,F,I,W,UP,B`, linha 100); **pytest** + **pytest-asyncio** (`asyncio_mode=auto`).
- Nomenclatura e textos em **PT-BR**; licença **GPL-3.0-or-later**.
- Cálculo pesado roda em subprocesso via `nicegui.run.cpu_bound` (funções picáveis).
- Estado **por aba** do navegador (`app.storage.tab`).
- Testes **espelham módulos** (`test_estado`, `test_solver`, `test_graficos`,
  `test_diagrama`, `test_paginas`, `test_integracao`).
- Sistema visual reaproveitado do molde: shell escuro + tema `es-*`, IBM Plex
  Sans/Mono, cartões claros, selo de veredito, campo numérico, controle segmentado,
  dropzone, barra de progresso.

## 5. Estrutura de pastas

```
gui/
  main.py          ponto de entrada (ui.run); importa as páginas (registra rotas)
  layout.py        moldura comum (gaveta escura + cabeçalho + tema es-*)
  estado.py        Projeto por aba (app.storage.tab); to_dict/from_dict
  solver.py        funções picáveis sobre o núcleo (montar_ybus, rodar_fluxo, ...)
  diagrama.py      editor de diagrama unifilar (canvas + nós + ramos) + funções puras
  graficos.py      figuras Plotly (perfil de tensão, trânsito, fasores, ...)
  componentes.py   cartões/selo/campo_num/segmented/dropzone/progresso reutilizados
  campos.py        parsing de campos (sem dependência de UI)
  casos.py         casos IEEE prontos (carregadores)
  paginas/         inicio, sistema, fluxo, visualizador  (+ curto na fase 3)
tests/             espelham os módulos acima
exemplos/          projetos e casos de exemplo (JSON)
Dockerfile
pyproject.toml
README.md
CLAUDE.md
spec.md
```

## 6. Modelo de dados — `Projeto` (estado.py)

`Projeto` é um dataclass guardado em `app.storage.tab`, uma instância por aba.
Espelha o schema de `exemplos/projeto.json`; `to_dict/from_dict` dão import/export
de graça. Resultados **não** entram no `to_dict` (são recalculáveis / download à
parte).

```python
@dataclass
class Projeto:
    # entradas (persistidas / compartilháveis)
    barras: list[dict]   # {id, nome, tipo(1=PQ|2=PV|3=Slack), V, theta, P, Q, x, y}
    ramos: list[dict]    # {id, de, para, r, x, b, tap}
    params_fluxo: dict   # {tolerancia, max_iter, Sbase}
    # fase 3 (curto-circuito)
    geradores: list[dict] | None  # {barra, X1, X2, X0, Zn, aterrado, R1, R2, R0}
    cargas: list[dict] | None     # {barra, P, Q}
    seq_ramos: dict | None        # por ramo: {z1, z2, z0, b1, b0, ligacao}
    # resultados (NÃO persistidos)
    resultado_fluxo: dict | None
    resultado_curto: dict | None
```

- `de`/`para`/`barra` são **1-based** (compatível com a API do núcleo).
- `x`/`y` são coordenadas do nó no canvas — **cosméticas** (ver §9): só posicionam o
  desenho, nunca afetam o cálculo.

## 7. Mapa da API do núcleo consumida

**Fluxo (`EletroSolver`):**
- `Barra(indice, tipo, V, theta, P, Q)` — `tipo` 1=PQ, 2=PV, 3=Slack.
- `Linha(de, para, z, b=0.0, tap=1.0)` — `de`/`para` 1-based; `z` complexo (pu).
- `SistemaPotencia(barras, Y, tolerancia=1e-6, max_iter=100, Sbase=100, linhas=None)`:
  - `calcular_fluxo()` → define `convergiu`, `convergencia` (nº iterações), `tempo`.
  - `v(i)`, `theta(i)` (1-based); `alterar_barra(...)`.
  - `transito(de, para)` → `{S_ij, P_ij, Q_ij}`.
  - `losses(de, para)` → `{S_loss, P_loss, Q_loss}`; `totlosses()` → `{P_loss, Q_loss}`.
  - `calcular_sensibilidade()` → matriz (inversa da última Jacobiana).
  - `exportar(arquivo)` → JSON com barras, fluxos, perdas, parâmetros, Ybus.

**Curto (`Faltas`, fase 3):**
- `Gerador(barra, X1, X2=None, X0=None, Zn=0, aterrado=True, R1=0, R2=0, R0=0)`.
- `Ramo(de, para, z1, z2=None, z0=None, b1=0, b0=0, ligacao="linha", tap=1.0)` —
  `ligacao` ∈ `linha|YNyn|Dyn|YNd|Dd|Yy|Yyn|YNy`.
- `Carga(barra, P, Q)`.
- `EstudoCurtoCircuito(sistema, geradores, ramos, cargas=None, incluir_cargas=True,
  incluir_shunt_linha=True, prefault="flat"|"fluxo")`:
  - `falta_trifasica(barra, Zf=0)`, `falta_monofasica(barra, Zf=0, Zg=0)`,
    `falta_bifasica(barra, Zf=0)`, `falta_bifasica_terra(barra, Zf=0, Zg=0)`.
  - Resultado: `{tipo, barra, Vf, I_seq, I_fase{a,b,c}, V_seq, V_fase,
    contrib_linha, contrib_gerador, contrib_carga, contrib_shunt_linha}`.
  - `corrente_kA(I_pu, kV_base)`, `potencia_curto_MVA(barra, tipo)`.

**Limitação conhecida:** o núcleo não expõe o histórico de resíduos por iteração —
só `convergencia` (contagem) e `tempo`. A GUI mostra **resumo de convergência**, não
curva por iteração.

## 8. Páginas

Gaveta (drawer) com funções de simular fluxo de potência ou correntes de falta;
**Visualizador** separado, como no molde.

### `/` Início
Visão geral + estado da sessão (o que já está definido), importar/exportar projeto
(JSON), atalhos para casos IEEE prontos. Espelha `paginas/inicio.py` do molde.

### `/sistema` — editor de diagrama unifilar (coração)
Detalhado em §9. Edita barras e ramos; monta a Ybus automaticamente; valida o
sistema (§11) e indica pendências antes de liberar o cálculo.
Possibilidade de importar e exportar sistemas por meio de json.

### `/fluxo` — Fluxo de potência
Pré-requisito: sistema válido. Parâmetros (`tolerancia`, `max_iter`, `Sbase`) e botão
**Calcular** (roda `rodar_fluxo` via `run.cpu_bound` + barra de progresso).
Resultados:
- **Selo/cartões**: convergiu? nº de iterações, tempo, perdas totais (P/Q).
- **Tabela de barras**: V (pu), θ (graus), P, Q (inclui P/Q resolvidos da slack/PV).
- **Trânsito por ramo**: P_ij, Q_ij, |S_ij|, sentido; **perdas por ramo**.
- **Sensibilidade** (opcional): visualização da matriz.
- **Diagrama colorido por |V|** (reaproveita o canvas em modo read-only).
- **Perfil de tensão** (Plotly): |V| e θ por barra.
- **Exportar JSON** (usa `exportar` do núcleo) e baixar.

### `/curto` — Curto-circuito 
Entradas extra (geradores, cargas, sequências dos ramos), escolha de barra + tipo de
falta + `Zf`/`Zg` + tensão base (kV) para kA. Resultados: correntes de falta (pu e
kA), potência de curto (MVA), contribuições por elemento, fasores das correntes de
fase. `prefault` "flat" ou "fluxo" (reusa o fluxo convergido, se houver).



## 9. Diagrama unifilar (diagrama.py)

**Princípio de de-risco:** a **fonte da verdade são os dados** (`barras`/`ramos`). A
edição de topologia é por **clique + painel lateral** (NiceGUI puro, robusto). O
**arraste apenas reposiciona** o nó (atualiza `x`/`y`), nunca altera topologia nem
cálculo. O editor nunca quebra por causa do arraste.

**Composição do canvas:**
- Container `ui.element('div')` com posição relativa e área rolável.
- **Camada SVG** (`ui.html`) embaixo, desenhando os ramos como linhas entre as
  âncoras das barras (e rótulos pós-cálculo).
- **Nós** das barras como elementos DOM posicionados em absoluto (`left:x; top:y`),
  estilizados por tipo (Slack/PV/PQ) e, pós-cálculo, por |V|.

**Funções puras (testáveis headless, sem navegador):**
- `gerar_svg_ramos(barras, ramos, resultados=None) -> str` — SVG das linhas/rótulos.
- `ancora(barra) -> (x, y)` — ponto de conexão de um nó.
- **Reducers de edição** (puros): `adicionar_barra`, `remover_barra` (e ramos
  incidentes), `ligar(de, para)`, `remover_ramo`, `mover(id, x, y)`,
  `editar_barra(id, **campos)`, `editar_ramo(id, **campos)`. Recebem e devolvem
  `(barras, ramos)`; testados como transições puras.

**Interação:**
- Toolbar: **+ Barra**, **modo Ligar** (toggle; clicar duas barras cria ramo e abre
  editor), **Excluir**, **Auto-organizar** (layout simples em grade/círculo),
  **Importar/Exportar**, **Casos IEEE**.
- Clique em barra → painel lateral (nome, tipo, V, θ, P, Q).
- Clique em ramo → painel lateral (r, x, b, tap; sequências na fase 3).
- Arraste de nó → JS move o elemento localmente e, no `pointerup`, emite a posição
  final de volta ao Python (evento NiceGUI) → `mover(id, x, y)`. Topologia jamais
  depende do arraste.

## 10. Camada solver (solver.py) — funções picáveis

Entrada/saída em tipos simples (dicts/listas/números); objetos do núcleo construídos
**dentro** da função (picável p/ `cpu_bound`, evita problemas de pickling no Windows).

- `montar_ybus(barras, ramos) -> list[list[complex]]` — estampa a Ybus a partir dos
  ramos (igual ao laço de `Simplificado.py`): `ys = 1/z`, soma na diagonal e subtrai
  fora dela; respeita `tap`/`b` no modelo π.
- `rodar_fluxo(barras, ramos, params) -> dict` — monta `Barra` + `Linha` +
  `SistemaPotencia`, chama `calcular_fluxo()`, coleta: estado por barra (V, θ, P, Q),
  trânsito e perdas por ramo, perdas totais, convergência (convergiu, iterações,
  tempo) e, opcionalmente, a sensibilidade. Tudo serializado em tipos nativos.
- `exportar_sistema(barras, ramos, params) -> dict` — equivalente ao `exportar` do
  núcleo, para download/visualizador.
- (Fase 3) `rodar_curto(barras, ramos, seq_ramos, geradores, cargas, falta) -> dict`.
- Carregadores de casos IEEE (ver §12).

Cap de segurança opcional (env `ELETROGUI_MAX_BARRAS`) para o demo público, espelhando
`EARTHGUI_MAX_SEG`.

## 11. Validações (espelham o núcleo, antes de calcular)

- **Exatamente uma** barra Slack (tipo 3) — `SistemaPotencia` exige isso.
- Índices de ramo dentro de `[1, n]`; `de != para`; `z != 0`; `tap != 0`.
- `V > 0` em toda barra; tipos válidos (1/2/3).
- **Conectividade**: avisar se o grafo está ilhado (Jacobiano singular provável).
- Mostrar pendências como avisos com link/ação (igual aos pré-requisitos do
  `paginas/calculo.py` do molde), bloqueando o cálculo até resolver.

## 12. Casos IEEE prontos (casos.py)

Carregadores que devolvem `(barras, ramos, params)` para popular o projeto com um
clique. Reaproveitar os dados de teste do núcleo (`tests/_ieee_data.py`,
`tests/_seq_data.py`) como base. Incluir ao menos um caso pequeno didático
(ex.: 5 barras de `Simplificado.py`) e um caso IEEE padrão.

## 13. Gráficos (graficos.py) — Plotly puro

Funções puras `-> go.Figure` (sem NiceGUI, testáveis headless):
- `perfil_tensao(barras_resultado)` — |V| (e θ) por barra.
- `transito(ramos_resultado)` — P/Q por ramo (barras ou setas).
- `resumo_convergencia(info)` — cartões/indicador (iterações, tempo, convergiu);
  **não** há curva por iteração (limitação §7).
- (Fase 3) `correntes_falta(...)`, `fasores(I_fase)` (polar a/b/c),
  `contribuicoes(contrib_*)` (barras empilhadas).

## 14. Import / Export

- **Projeto** (`to_dict`/`from_dict`): barras, ramos, params (e, na fase 3,
  geradores/cargas/sequências). Round-trip testado.
- **Resultado do fluxo**: JSON no formato do `exportar` do núcleo (download).
- **Visualizador** consome esse JSON sem recalcular.

## 15. Erros e estados de borda

- Não-convergência: o núcleo emite `warning` e deixa `convergiu=False`; a UI mostra
  selo de falha + dica (revisar dados/aumentar `max_iter`).
- Jacobiano/rede singular (`LinAlgError`): mensagem clara (sistema mal-condicionado /
  ilhado / sem referência).
- Falhas do subprocesso propagadas e exibidas via `ui.notify(type="negative")`
  (padrão do molde).

## 16. Testes

- `test_estado` — `to_dict/from_dict`, defaults, isolamento por aba (armazém injetável).
- `test_solver` — `montar_ybus` (contra a Ybus de `Simplificado.py`), `rodar_fluxo`
  (convergência e valores contra os testes do núcleo / caso de 5 barras).
- `test_diagrama` — reducers puros (add/ligar/remover/mover/editar) e geração de SVG.
- `test_graficos` — figuras geradas sem erro, traços esperados.
- `test_campos` / `test_casos` — parsing e carregadores IEEE.
- `test_paginas` — smoke test via `nicegui.testing` (páginas sobem e renderizam).
- `test_integracao` — montar sistema → rodar fluxo → exportar → reabrir no visualizador.

## 17. Fases de implementação

- **Fase 0 — Scaffold:** `pyproject.toml` da GUI; `pyproject.toml` no `EletroSolver`
  (§3); pacote `gui/` com `layout.py` (tema `es-*` portado), `estado.py`, `main.py`;
  CI/lint; `Dockerfile`; README.
- **Fase 1 — Editor unifilar:** modelo de dados; `diagrama.py` (canvas + nós + ramos +
  SVG puro + reducers); página `/sistema`; edição por clique; arraste cosmético;
  validações (§11); `montar_ybus`.
- **Fase 2 — Fluxo:** `rodar_fluxo`; página `/fluxo` (resultados, tabelas, diagrama
  colorido, perfil de tensão, sensibilidade, export); casos IEEE (`casos.py`);
  `/visualizador`; testes de integração.
- **Fase 3 — Curto-circuito (posterior):** entradas de sequência/geradores/cargas;
  `rodar_curto`; página `/curto`; fasores e contribuições.

## 18. Deploy

`Dockerfile` que instala a GUI (puxando `eletrosolver` via `git+https`) e sobe em modo
headless. Variáveis: `PORT`, `STORAGE_SECRET`, `ELETROGUI_HEADLESS`,
`ELETROGUI_MAX_BARRAS`. Compatível com Hugging Face Spaces (Docker) / Render /
Railway / Fly.io, como o molde.

## 19. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Arraste em NiceGUI puro ficar instável | Topologia por clique (autoritativa); arraste só move `x/y`. Fonte da verdade são os dados. |
| Empacotar o núcleo "mexer" no repo | Só adicionar `pyproject.toml` (metadados), sem tocar no código. |
| Fluxo lento em sistemas grandes | `run.cpu_bound` + cap `ELETROGUI_MAX_BARRAS`. |
| Expectativa de curva de convergência | Documentado: núcleo não expõe resíduos por iteração; mostrar resumo. |

## 20. Entregáveis desta sessão

- `spec.md` (este documento, na raiz) + cópia datada em
  `docs/superpowers/specs/2026-06-17-eletrosolver-gui-design.md`.
- `CLAUDE.md` (raiz) — guia do repositório para o Claude Code.
- Próximo passo: plano de implementação (skill `writing-plans`).
