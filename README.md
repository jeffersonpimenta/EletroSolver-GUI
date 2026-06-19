# EletroSolver-GUI

Interface web para o **[EletroSolver](https://github.com/jeffersonpimenta/EletroSolver)** —
um solver de **sistemas elétricos de potência** em Python/numpy. Em vez de escrever
scripts, você monta um **diagrama unifilar** (barras + ramos) e roda análises **sobre o
próprio desenho**:

- **Fluxo de potência** por Newton-Raphson (entregue).
- **Curto-circuito** por componentes simétricas (projetado; fase 3).

Construída em **NiceGUI**, espelhando a stack e o sistema visual do
[`EarthSolver-GUI`](https://github.com/jeffersonpimenta/EarthSolver-GUI). Veja
[`spec.md`](spec.md) para o documento de design completo.

---

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
eletrosolver-gui            # ou: python -m gui.main
```

Abre em <http://localhost:8080>.

### Núcleo de cálculo

Canonicamente o núcleo é um pacote à parte
(`eletrosolver @ git+https://github.com/jeffersonpimenta/EletroSolver.git`). Para que
este repositório rode **sem clonar o núcleo**, os módulos `EletroSolver.py` e `Faltas.py`
estão **versionados na raiz** — `import EletroSolver` / `import Faltas` funcionam de
imediato. Para usar a versão oficial, remova os módulos da raiz e descomente a
dependência `git+https` em `pyproject.toml`.

---

## Estrutura

```
gui/
  main.py          ponto de entrada (ui.run); importa as páginas (registra rotas)
  layout.py        moldura comum (gaveta escura + cabeçalho + tema es-*)
  estado.py        Projeto por aba (app.storage.tab); to_dict/from_dict
  solver.py        funções picáveis sobre o núcleo (montar_ybus, rodar_fluxo, ...)
  diagrama.py      reducers puros do diagrama unifilar + geração de SVG
  graficos.py      figuras Plotly (perfil de tensão, trânsito, convergência)
  componentes.py   cartão / selo / campo_num / segmented / dropzone / progresso
  campos.py        parsing de campos (sem dependência de UI)
  casos.py         casos prontos (carregadores)
  paginas/         inicio, sistema, fluxo, visualizador
tests/             espelham os módulos acima
exemplos/          projetos e casos de exemplo (JSON)
```

---

## Testes e lint

```bash
pytest        # testes (espelham os módulos)
ruff check .  # lint (E,F,I,W,UP,B; linha 100)
```

---

## Deploy (Docker)

```bash
docker build -t eletrosolver-gui .
docker run -p 8080:8080 -e STORAGE_SECRET=troque-isto eletrosolver-gui
```

Variáveis: `PORT`, `STORAGE_SECRET`, `ELETROGUI_HEADLESS`, `ELETROGUI_MAX_BARRAS`.
Compatível com Hugging Face Spaces (Docker) / Render / Railway / Fly.io.

---

## Licença

GPL-3.0-or-later.
