"""Regressão do dropdown ``selecao`` (NiceGUI 3.x).

O NiceGUI 3.x modela as opções como objetos ``{value: index, label}`` e emite o
objeto da opção no change; ``Select._event_args_to_value`` traduz index→chave. A
prop ``emit-value`` (idioma do NiceGUI 2) faz o Quasar emitir só o escalar e
quebra essa tradução — a troca "não entra" e o valor reverte.
"""
import pytest
from nicegui import ui
from nicegui.events import GenericEventArguments

from gui.componentes import selecao

pytestmark = pytest.mark.nicegui_main_file("gui/main.py")

OPCOES = {"linha": "Linha / cabo", "Dyn": "Trafo Dyn"}


async def test_selecao_dict_comita_chave(user) -> None:
    recebido = []
    ref = {}

    @ui.page("/t")
    def _p():
        ref["el"] = selecao("Lig", "linha", dict(OPCOES), recebido.append)

    await user.open("/t")
    el = ref["el"]

    # não pode forçar emit-value: quebraria o mapeamento objeto→chave no NiceGUI 3.x
    assert "emit-value" not in el._props
    assert "map-options" not in el._props

    # evento real do cliente: Quasar manda o OBJETO da opção 'Dyn' (index 1)
    e = GenericEventArguments(sender=el, client=el.client,
                              args={"value": 1, "label": "Trafo Dyn"})
    el.set_value(el._event_args_to_value(e))
    assert el.value == "Dyn"
    assert recebido == ["Dyn"]


async def test_emit_value_escalar_quebraria(user) -> None:
    """Documenta a causa: com escalar (o que ``emit-value`` produz) o map falha."""
    ref = {}

    @ui.page("/t2")
    def _p():
        ref["el"] = selecao("Lig", "linha", dict(OPCOES), lambda _v: None)

    await user.open("/t2")
    el = ref["el"]
    with pytest.raises((TypeError, KeyError, IndexError)):
        el._event_args_to_value(
            GenericEventArguments(sender=el, client=el.client, args=1))
