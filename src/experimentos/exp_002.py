"""EXP-002: adaptação quando a regra do ambiente muda sem aviso."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Situacao:
    massa: float
    forca: float

    @property
    def relacao_forca_massa(self) -> float:
        return self.forca / self.massa


class AmbienteComLimiar:
    def __init__(self, limiar_de_movimento: float) -> None:
        self.limiar_de_movimento = limiar_de_movimento

    def executar(self, situacao: Situacao) -> bool:
        if situacao.massa <= 0:
            raise ValueError("A massa precisa ser maior que zero.")
        if situacao.forca < 0:
            raise ValueError("A força não pode ser negativa neste ambiente.")
        return situacao.relacao_forca_massa >= self.limiar_de_movimento


class ModeloDeLimiarRecente:
    """Modelo que estima o limiar usando apenas experiências recentes.

    A janela limitada é uma estratégia de adaptação, não um mecanismo completo
    de retenção. Ela descarta evidências antigas quando recebe novas experiências.
    """

    def __init__(self, tamanho_da_janela: int = 6) -> None:
        if tamanho_da_janela < 2:
            raise ValueError("A janela precisa comportar pelo menos duas experiências.")
        self.experiencias: deque[tuple[Situacao, bool]] = deque(
            maxlen=tamanho_da_janela
        )

    def observar(self, situacao: Situacao, resultado: bool) -> None:
        self.experiencias.append((situacao, resultado))

    @property
    def limiar_estimado(self) -> float | None:
        sem_movimento = [
            situacao.relacao_forca_massa
            for situacao, resultado in self.experiencias
            if not resultado
        ]
        com_movimento = [
            situacao.relacao_forca_massa
            for situacao, resultado in self.experiencias
            if resultado
        ]
        if not sem_movimento or not com_movimento:
            return None
        return (max(sem_movimento) + min(com_movimento)) / 2

    def prever(self, situacao: Situacao) -> bool:
        limiar = self.limiar_estimado
        if limiar is None:
            raise RuntimeError("Ainda não há evidência dos dois resultados possíveis.")
        return situacao.relacao_forca_massa >= limiar


APRENDIZAGEM_FASE_1 = (
    Situacao(1, 0.5),
    Situacao(2, 1),
    Situacao(3, 1.5),
    Situacao(1, 1),
    Situacao(2, 2),
    Situacao(3, 3),
)
AVALIACAO_FASE_1 = (
    Situacao(4, 2),
    Situacao(5, 2.5),
    Situacao(4, 4),
    Situacao(2, 3),
)

APRENDIZAGEM_APOS_MUDANCA = (
    Situacao(4, 3),
    Situacao(7, 7),
    Situacao(5, 7),
    Situacao(6, 9),
    Situacao(5, 8),
    Situacao(3, 6),
)
AVALIACAO_APOS_MUDANCA = (
    Situacao(5, 5),
    Situacao(5, 6),
    Situacao(4, 6),
    Situacao(2, 4),
)


def _acuracia(modelo: ModeloDeLimiarRecente, ambiente: AmbienteComLimiar, amostras: tuple[Situacao, ...]) -> float:
    return sum(
        modelo.prever(situacao) == ambiente.executar(situacao) for situacao in amostras
    ) / len(amostras)


def executar_experimento() -> dict[str, object]:
    ambiente_inicial = AmbienteComLimiar(limiar_de_movimento=1.0)
    ambiente_alterado = AmbienteComLimiar(limiar_de_movimento=1.5)
    adaptativo = ModeloDeLimiarRecente(tamanho_da_janela=6)
    congelado = ModeloDeLimiarRecente(tamanho_da_janela=6)

    for situacao in APRENDIZAGEM_FASE_1:
        resultado = ambiente_inicial.executar(situacao)
        adaptativo.observar(situacao, resultado)
        congelado.observar(situacao, resultado)

    limiar_inicial_estimado = adaptativo.limiar_estimado
    acuracia_inicial = _acuracia(adaptativo, ambiente_inicial, AVALIACAO_FASE_1)
    acuracia_antes_da_adaptacao = _acuracia(
        adaptativo, ambiente_alterado, AVALIACAO_APOS_MUDANCA
    )

    for situacao in APRENDIZAGEM_APOS_MUDANCA:
        adaptativo.observar(situacao, ambiente_alterado.executar(situacao))

    acuracia_depois_da_adaptacao = _acuracia(
        adaptativo, ambiente_alterado, AVALIACAO_APOS_MUDANCA
    )
    acuracia_modelo_congelado = _acuracia(
        congelado, ambiente_alterado, AVALIACAO_APOS_MUDANCA
    )

    return {
        "experimento": "EXP-002",
        "limiar_inicial_estimado": limiar_inicial_estimado,
        "limiar_adaptado_estimado": adaptativo.limiar_estimado,
        "acuracia_inicial": acuracia_inicial,
        "acuracia_apos_mudanca_antes_de_novas_experiencias": acuracia_antes_da_adaptacao,
        "acuracia_apos_adaptacao": acuracia_depois_da_adaptacao,
        "acuracia_modelo_congelado_apos_mudanca": acuracia_modelo_congelado,
        "avaliacao_apos_mudanca": [
            {
                **asdict(situacao),
                "resultado_real": ambiente_alterado.executar(situacao),
                "previsao_adaptativa": adaptativo.prever(situacao),
                "previsao_congelada": congelado.prever(situacao),
            }
            for situacao in AVALIACAO_APOS_MUDANCA
        ],
    }


if __name__ == "__main__":
    print(json.dumps(executar_experimento(), ensure_ascii=False, indent=2))
