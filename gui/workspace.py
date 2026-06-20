"""Controlador reativo da página única (espelha o componente React do ``modelo/``).

Guarda **todo** o estado da sessão (barras/ramos/params + resultados em memória +
estado de UI: modo, seleção, falta, galeria) e expõe os *reducers* como métodos.
A renderização é dividida em regiões ``@ui.refreshable`` para que digitar num
campo nunca reconstrua o próprio campo (preserva o foco).

O diagrama é desenhado como HTML (:func:`gui.diagrama.render_canvas`) e um
controlador JS único trata arraste/clique, devolvendo eventos ``es_*`` ao Python
(arraste só reposiciona ``x``/``y`` — cosmético; topologia é por clique/painel).
"""
from __future__ import annotations

import json

from nicegui import run, ui

from gui import casos, diagrama, estado, solver
from gui.campos import graus_para_rad, para_float, para_int
from gui.paginas import galeria as pg_galeria
from gui.paginas import inicio as pg_inicio
from gui.paginas import sistema as pg_sistema

_CANVAS_JS = """
(function(){
  if (window.__esCanvasInit) return; window.__esCanvasInit = true;
  let drag = null;
  function emit(name, data){
    try { (window.emitEvent || emitEvent)(name, data); }
    catch(err){ console.log('ES emit error', name, ''+err); }
  }
  document.addEventListener('pointerdown', function(e){
    const node = e.target.closest && e.target.closest('[data-bid]');
    if (!node || !node.hasAttribute('data-drag') || !node.closest('#es-canvas')) return;
    console.log('ES down', node.getAttribute('data-bid'));
    const id = parseInt(node.getAttribute('data-bid'));
    const ox = parseFloat(node.style.left)||0, oy = parseFloat(node.style.top)||0;
    drag = {node:node, id:id, sx:e.clientX, sy:e.clientY, ox:ox, oy:oy, moved:false};
    try { node.setPointerCapture(e.pointerId); } catch(_) {}
    e.preventDefault();
  });
  document.addEventListener('pointermove', function(e){
    if (!drag) return;
    const dx = e.clientX-drag.sx, dy = e.clientY-drag.sy;
    if (Math.abs(dx)>3 || Math.abs(dy)>3) drag.moved = true;
    if (drag.moved){ drag.node.style.left=(drag.ox+dx)+'px'; drag.node.style.top=(drag.oy+dy)+'px'; }
  });
  document.addEventListener('pointerup', function(e){
    if (!drag) return; const d = drag; drag = null;
    if (d.moved) emit('es_node_move', {id:d.id, x:Math.round(d.ox+(e.clientX-d.sx)), y:Math.round(d.oy+(e.clientY-d.sy))});
    else emit('es_node_tap', {id:d.id});
  });
  document.addEventListener('click', function(e){
    const canvas = e.target.closest && e.target.closest('#es-canvas');
    if (!canvas) return;
    const rid = e.target.getAttribute && e.target.getAttribute('data-rid');
    if (rid){ emit('es_ramo_tap', {id:parseInt(rid)}); return; }
    if (e.target.closest('[data-bid]')) return;
    emit('es_canvas_tap', {});
  });
})();
"""


class Workspace:
    def __init__(self) -> None:
        proj = estado.projeto_da_aba()
        self.proj = proj
        self.modo = "editar"
        self.page = "inicio"
        self.sel_kind: str | None = None
        self.sel_id: int | None = None
        self.edit_aspecto = "fluxo"
        self.ligar_ativo = False
        self.ligar_de: int | None = None
        self.calculando = False
        self.c_barra: int | None = None
        self.c_tipo = "tri"
        self.c_zf = 0.0
        self.mat_seq = "pos"
        self._novo = not proj.barras
        self._dialogo_galeria = None
        # handles das regiões refreshable
        self._r_drawer = self._r_header = self._r_conteudo = None
        self._r_toolbar = self._r_canvas = self._r_sob = self._r_rodape = None
        self._r_painel_topo = self._r_painel_extra = None

    # ------------------------------------------------------------- utilidades
    @property
    def sbase(self) -> float:
        return float(self.proj.params_fluxo.get("Sbase", 100.0))

    def barra(self, bid):
        return next((b for b in self.proj.barras if b["id"] == bid), None)

    def ramo(self, rid):
        return next((r for r in self.proj.ramos if r["id"] == rid), None)

    def sel_barra(self):
        return self.barra(self.sel_id) if self.sel_kind == "barra" else None

    def sel_ramo(self):
        return self.ramo(self.sel_id) if self.sel_kind == "ramo" else None

    def page_title(self) -> str:
        if self.page == "sistema":
            sub = {"editar": "Editar", "fluxo": "Fluxo de potência",
                   "curto": "Curto-circuito"}[self.modo]
            return f"Sistema · {sub}"
        return {"inicio": "Início", "viz": "Visualizador"}.get(self.page, "Início")

    def _persistir(self) -> None:
        estado.salvar_na_aba(self.proj)

    def _limpar_resultados(self) -> None:
        self.proj.resultado_fluxo = None
        self.proj.resultado_curto = None

    # --------------------------------------------------------------- refresh
    def _refresh(self, *nomes) -> None:
        for n in nomes:
            r = getattr(self, f"_r_{n}", None)
            if r is not None:
                try:
                    r.refresh()
                except Exception:
                    pass

    def refresh_dados(self) -> None:
        """Após digitar num campo: não reconstrói os campos (preserva foco)."""
        self._refresh("canvas", "sob", "toolbar", "rodape", "drawer", "painel_extra")

    def refresh_estrutura(self) -> None:
        """Após clique que muda a estrutura do painel."""
        self._refresh("toolbar", "canvas", "sob", "rodape", "drawer",
                      "painel_topo", "painel_extra")

    def refresh_pagina(self) -> None:
        self._refresh("drawer", "header", "conteudo")

    # ------------------------------------------------------------ navegação
    def nav_inicio(self) -> None:
        self.page = "inicio"
        self.refresh_pagina()

    async def nav_editar(self) -> None:
        await self.set_modo("editar")

    async def nav_fluxo(self) -> None:
        await self.set_modo("fluxo")

    async def nav_curto(self) -> None:
        await self.set_modo("curto")

    async def set_modo(self, m: str) -> None:
        auto = (m == "fluxo" and self.proj.resultado_fluxo is None
                and diagrama.eh_valido(self.proj.barras, self.proj.ramos))
        self.modo = m
        self.page = "sistema"
        self.refresh_pagina()
        if auto:
            await self.calcular_fluxo()

    # -------------------------------------------------------------- reducers
    def add_barra(self) -> None:
        self.proj.barras = diagrama.adicionar_barra(self.proj.barras)
        self.sel_kind, self.sel_id = "barra", self.proj.barras[-1]["id"]
        self._limpar_resultados()
        self._persistir()
        self.refresh_estrutura()

    def toggle_ligar(self) -> None:
        self.ligar_ativo = not self.ligar_ativo
        self.ligar_de = None
        self._refresh("toolbar", "rodape", "canvas")

    def auto_organizar(self) -> None:
        self.proj.barras = diagrama.auto_organizar(self.proj.barras)
        self._persistir()
        self._refresh("canvas")

    def selecionar(self, kind, bid) -> None:
        self.sel_kind, self.sel_id = kind, bid
        self._refresh("painel_topo", "canvas")

    def excluir_sel(self) -> None:
        if self.sel_kind == "barra":
            self.proj.barras, self.proj.ramos = diagrama.remover_barra(
                self.proj.barras, self.proj.ramos, self.sel_id)
        elif self.sel_kind == "ramo":
            self.proj.ramos = diagrama.remover_ramo(self.proj.ramos, self.sel_id)
        self.sel_kind = self.sel_id = None
        self._limpar_resultados()
        self._persistir()
        self.refresh_estrutura()

    def ligar_click(self, bid) -> None:
        if self.ligar_de is None:
            self.ligar_de = bid
            self._refresh("canvas", "rodape")
            return
        if self.ligar_de == bid:
            self.ligar_de = None
            self._refresh("canvas", "rodape")
            return
        antes = len(self.proj.ramos)
        self.proj.ramos = diagrama.conectar(self.proj.ramos, self.ligar_de, bid)
        novo = len(self.proj.ramos) > antes
        if novo:
            self.sel_kind, self.sel_id = "ramo", self.proj.ramos[-1]["id"]
            self._limpar_resultados()
        self.ligar_de = None
        self._persistir()
        self.refresh_estrutura()

    def mover(self, bid, x, y) -> None:
        self.proj.barras = diagrama.mover_barra(self.proj.barras, bid, x, y)
        self._persistir()
        self._refresh("canvas")

    # -------- edição de barra (painel) -------------------------------------
    def _edit_barra(self, **campos) -> None:
        self.proj.barras = diagrama.atualizar_barra(self.proj.barras, self.sel_id, **campos)
        self._limpar_resultados()
        self._persistir()
        self.refresh_dados()

    def set_nome(self, v):
        self._edit_barra(nome=str(v or ""))

    def set_kv(self, v):
        self._edit_barra(kv=para_float(v))

    def set_v(self, v):
        self._edit_barra(V=para_float(v))

    def set_theta_deg(self, v):
        self._edit_barra(theta=graus_para_rad(v))

    def set_p_mw(self, v):
        self._edit_barra(P=para_float(v) / self.sbase)

    def set_q_mvar(self, v):
        self._edit_barra(Q=para_float(v) / self.sbase)

    def set_xd(self, v):
        self._edit_barra(xd=para_float(v))

    def set_xd0(self, v):
        self._edit_barra(xd0=para_float(v))

    def set_tipo(self, t) -> None:
        self.proj.barras = diagrama.definir_tipo(self.proj.barras, self.sel_id, t)
        self._limpar_resultados()
        self._persistir()
        self.refresh_estrutura()

    def set_aspecto(self, a) -> None:
        self.edit_aspecto = a
        self._refresh("painel_topo")

    # -------- edição de ramo (painel) --------------------------------------
    def _edit_ramo(self, **campos) -> None:
        self.proj.ramos = diagrama.atualizar_ramo(self.proj.ramos, self.sel_id, **campos)
        self._limpar_resultados()
        self._persistir()
        self.refresh_dados()

    def set_r(self, v):
        self._edit_ramo(r=para_float(v))

    def set_x(self, v):
        self._edit_ramo(x=para_float(v))

    def set_b(self, v):
        self._edit_ramo(b=para_float(v))

    def set_tap(self, v):
        self._edit_ramo(tap=para_float(v) or 1.0)

    def set_r0(self, v):
        self._edit_ramo(r0=para_float(v))

    def set_x0(self, v):
        self._edit_ramo(x0=para_float(v))

    def set_b0(self, v):
        self._edit_ramo(b0=para_float(v))

    def set_ligacao(self, v) -> None:
        self.proj.ramos = diagrama.atualizar_ramo(self.proj.ramos, self.sel_id, ligacao=v)
        self._limpar_resultados()
        self._persistir()
        self.refresh_estrutura()

    # -------- parâmetros do fluxo ------------------------------------------
    def set_tol(self, v):
        self.proj.params_fluxo["tolerancia"] = para_float(v, 1e-6) or 1e-6
        self._param_alterado()

    def set_max_iter(self, v):
        self.proj.params_fluxo["max_iter"] = para_int(v, 100) or 100
        self._param_alterado()

    def set_sbase(self, v):
        # Reescala P/Q (pu) para preservar os MW ao trocar a base. _param_alterado
        # limpa resultados e re-renderiza; os campos P/Q em MW não mudam de valor.
        self.proj.alterar_sbase(para_float(v, 100.0) or 100.0)
        self._param_alterado()

    def _param_alterado(self):
        self._limpar_resultados()
        self._persistir()
        self.refresh_dados()

    # -------- curto-circuito (painel) --------------------------------------
    def set_c_barra(self, bid) -> None:
        self.c_barra = int(bid)
        self.proj.resultado_curto = None
        self._refresh("painel_topo", "painel_extra", "sob", "canvas")

    def set_c_tipo(self, t) -> None:
        self.c_tipo = t
        self.proj.resultado_curto = None
        self._refresh("painel_topo", "painel_extra", "sob", "canvas")

    def set_zf(self, v):
        self.c_zf = para_float(v)
        self.proj.resultado_curto = None
        self._refresh("painel_extra", "sob", "canvas")

    def set_mat_seq(self, s) -> None:
        self.mat_seq = s
        self._refresh("sob")

    # ----------------------------------------------------------- cálculos
    async def calcular_fluxo(self) -> None:
        if not diagrama.eh_valido(self.proj.barras, self.proj.ramos):
            self.modo = "editar"
            self.refresh_pagina()
            ui.notify("Sistema inválido — corrija as pendências.", type="warning")
            return
        self.calculando = True
        self._refresh("painel_topo")
        res = await run.cpu_bound(solver.rodar_fluxo, self.proj.barras,
                                  self.proj.ramos, dict(self.proj.params_fluxo))
        self.proj.resultado_fluxo = res
        self.calculando = False
        self._refresh("painel_topo", "painel_extra", "canvas", "sob", "toolbar", "drawer")
        if not res.get("convergiu"):
            ui.notify(res.get("mensagem", "Não convergiu."), type="negative")

    async def calcular_curto(self) -> None:
        if not diagrama.eh_valido(self.proj.barras, self.proj.ramos):
            self.modo = "editar"
            self.refresh_pagina()
            ui.notify("Sistema inválido — corrija as pendências.", type="warning")
            return
        if self.c_barra is None and self.proj.barras:
            self.c_barra = self.proj.barras[0]["id"]
        falta = {"tipo": self.c_tipo, "barra": self.c_barra, "Zf": self.c_zf}
        res = await run.cpu_bound(solver.rodar_curto, self.proj.barras,
                                  self.proj.ramos, dict(self.proj.params_fluxo), falta)
        self.proj.resultado_curto = res
        self._refresh("painel_extra", "sob", "canvas", "toolbar", "drawer")
        if res.get("erro"):
            ui.notify(res.get("mensagem", "Falha no curto."), type="negative")

    # ----------------------------------------------------------- casos/IO
    def carregar_caso(self, chave) -> None:
        barras, ramos, params = casos.carregar(chave)
        self.proj.definir_sistema(barras, ramos, params, nome=casos.nome_caso(chave))
        self.sel_kind = self.sel_id = None
        self.c_barra = barras[0]["id"] if barras else None
        self.page, self.modo = "sistema", "editar"
        self.fechar_galeria()
        self._persistir()
        self.refresh_pagina()

    def baixar_projeto(self) -> None:
        dados = {"barras": self.proj.barras, "ramos": self.proj.ramos,
                 "params": self.proj.params_fluxo}
        ui.download(json.dumps(dados, indent=2).encode("utf-8"), "projeto.json")

    def exportar_resultado(self) -> None:
        if self.proj.resultado_fluxo:
            ui.download(json.dumps(self.proj.resultado_fluxo, indent=2).encode("utf-8"),
                        "resultado.json")

    def importar_projeto(self, dados: dict) -> None:
        proj = estado.Projeto.from_dict(dados)
        self.proj.definir_sistema(proj.barras, proj.ramos, proj.params_fluxo,
                                  nome=proj.nome)
        self.sel_kind = self.sel_id = None
        self.page, self.modo = "sistema", "editar"
        self._persistir()
        self.refresh_pagina()

    def abrir_galeria(self) -> None:
        if self._dialogo_galeria:
            self._dialogo_galeria.open()

    def fechar_galeria(self) -> None:
        if self._dialogo_galeria:
            self._dialogo_galeria.close()

    # ----------------------------------------------------- eventos do canvas
    @staticmethod
    def _ev(e) -> dict:
        a = getattr(e, "args", None)
        if isinstance(a, list):
            a = a[0] if a else {}
        return a or {}

    def _on_node_tap(self, e) -> None:
        a = self._ev(e)
        if "id" not in a:
            return
        bid = int(a["id"])
        if self.modo == "editar":
            if self.ligar_ativo:
                self.ligar_click(bid)
            else:
                self.selecionar("barra", bid)
        elif self.modo == "curto":
            self.set_c_barra(bid)

    def _on_node_move(self, e) -> None:
        a = self._ev(e)
        if {"id", "x", "y"} <= a.keys():
            self.mover(int(a["id"]), float(a["x"]), float(a["y"]))

    def _on_ramo_tap(self, e) -> None:
        a = self._ev(e)
        if self.modo == "editar" and "id" in a:
            self.selecionar("ramo", int(a["id"]))

    def _on_canvas_tap(self, e) -> None:
        if self.modo == "editar" and (self.sel_kind or not self.ligar_ativo):
            self.selecionar(None, None)

    # --------------------------------------------------------------- canvas
    def canvas_html(self) -> str:
        return diagrama.render_canvas(
            self.proj.barras, self.proj.ramos, modo=self.modo,
            resultado=self.proj.resultado_fluxo, curto=self.proj.resultado_curto,
            sel_kind=self.sel_kind, sel_id=self.sel_id,
            ligar_ativo=self.ligar_ativo, ligar_de=self.ligar_de)

    # -------------------------------------------------------------- montagem
    async def construir(self) -> None:
        from gui import layout
        layout.tema()
        ui.on("es_node_tap", self._on_node_tap)
        ui.on("es_node_move", self._on_node_move)
        ui.on("es_ramo_tap", self._on_ramo_tap)
        ui.on("es_canvas_tap", self._on_canvas_tap)
        self._dialogo_galeria = pg_galeria.criar(self)

        with ui.element("div").style(
            "display:flex;flex-wrap:nowrap;height:100vh;width:100%;overflow:hidden;"
            f"font-family:{layout.SANS};color:{layout.TEXTO}"
        ):
            @ui.refreshable
            def drawer():
                layout.montar_drawer(self)
            self._r_drawer = drawer
            drawer()

            with ui.element("div").style("flex:1;display:flex;flex-direction:column;overflow:hidden"):
                @ui.refreshable
                def header():
                    ui.html(layout.cabecalho_html(self.page_title()))
                self._r_header = header
                header()

                with ui.element("div").style("flex:1;overflow-y:auto"):
                    @ui.refreshable
                    def conteudo():
                        if self.page == "inicio":
                            pg_inicio.render(self)
                        elif self.page == "viz":
                            pg_inicio.render_viz(self)
                        else:
                            self._montar_sistema()
                    self._r_conteudo = conteudo
                    conteudo()

        # controlador de arraste/clique do canvas (delegação no document).
        # via run_javascript: <script> em innerHTML não executa.
        ui.run_javascript(_CANVAS_JS)

        # abertura idêntica ao .html: aba nova → 5 barras, modo Curto, falta na barra 3
        if self._novo:
            barras, ramos, params = casos.carregar("d5")
            self.proj.definir_sistema(barras, ramos, params, nome=casos.nome_caso("d5"))
            self.c_barra = 3
            self.page, self.modo = "sistema", "curto"
            self._persistir()
            self.refresh_pagina()
            await self.calcular_curto()

    def _montar_sistema(self) -> None:
        with ui.element("div").style("display:flex;height:100%;animation:esFade .25s ease"):
            with ui.element("div").style("flex:1;display:flex;flex-direction:column;min-width:0"):
                @ui.refreshable
                def toolbar():
                    pg_sistema.toolbar(self)
                self._r_toolbar = toolbar
                toolbar()

                with ui.element("div").style(
                    "flex:1;overflow:auto;background:#eef0f3;"
                    "background-image:radial-gradient(#dfe2e8 1px,transparent 1px);"
                    "background-size:22px 22px;padding:24px"
                ):
                    with ui.element("div").style("width:860px"):
                        @ui.refreshable
                        def canvas():
                            ui.html(self.canvas_html())
                        self._r_canvas = canvas
                        canvas()

                        @ui.refreshable
                        def sob():
                            pg_sistema.sob_canvas(self)
                        self._r_sob = sob
                        sob()

                @ui.refreshable
                def rodape():
                    ui.html('<div style="padding:9px 22px;border-top:1px solid #e6e8ec;'
                            'background:#fafbfc;font-size:12px;color:#8a909c">'
                            f'{pg_sistema.canvas_hint(self)}</div>')
                self._r_rodape = rodape
                rodape()

            with ui.element("div").style(
                "width:322px;flex-shrink:0;border-left:1px solid #e6e8ec;background:#fff;"
                "display:flex;flex-direction:column;overflow-y:auto"
            ):
                @ui.refreshable
                def painel_topo():
                    pg_sistema.painel_topo(self)
                self._r_painel_topo = painel_topo
                painel_topo()

                @ui.refreshable
                def painel_extra():
                    pg_sistema.painel_extra(self)
                self._r_painel_extra = painel_extra
                painel_extra()
