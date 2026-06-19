# CLAUDE.md — guia do repositório

`EletroSolver-GUI` é a interface web (NiceGUI) do núcleo `EletroSolver`. Consome
**apenas a API pública** do núcleo; o núcleo permanece intocado.

## Convenções
- Python ≥ 3.10, **NiceGUI ≥ 2**, **Plotly**, **numpy**.
- **ruff** (`E,F,I,W,UP,B`, linha 100). **pytest** + **pytest-asyncio** (`asyncio_mode=auto`).
- Textos e nomes em **PT-BR**. Licença GPL-3.0-or-later.
- Cálculo pesado em subprocesso via `nicegui.run.cpu_bound` (funções **picáveis**:
  entrada/saída em tipos simples, objetos do núcleo construídos dentro da função).
- Estado **por aba** (`app.storage.tab`); resultados não são persistidos no `to_dict`.
- Índices `de`/`para`/`barra` são **1-based** (compatível com a API do núcleo).
- **Estilo inline / tema `es-*`** em `layout.py`; não introduzir frameworks de CSS.

## Camadas (não misturar)
- `campos.py`, `estado.py`, `solver.py`, `diagrama.py`, `graficos.py`, `casos.py`
  são **puros / testáveis headless** (sem importar `nicegui.ui`).
- `componentes.py`, `layout.py`, `paginas/` são a camada de UI.

## Fonte da verdade do diagrama
Os **dados** (`barras`/`ramos`) são a fonte da verdade. Topologia muda por
**clique + painel** (reducers puros em `diagrama.py`). Arraste **só** atualiza `x`/`y`
(cosmético) — nunca topologia nem cálculo.

## API do núcleo consumida
Ver `spec.md` §7. Resumo:
- `EletroSolver`: `Barra(indice,tipo,V,theta,P,Q)`, `Linha(de,para,z,b,tap)`,
  `SistemaPotencia(barras,Y,tolerancia,max_iter,Sbase,linhas)` →
  `calcular_fluxo()`, `transito()`, `losses()`, `totlosses()`,
  `calcular_sensibilidade()`, `exportar()`.
- `Faltas` (fase 3): `Gerador`, `Ramo`, `Carga`, `EstudoCurtoCircuito`.
