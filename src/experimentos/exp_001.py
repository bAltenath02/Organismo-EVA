"""EXP-001: generalização da relação entre força, massa e movimento.

Este experimento é deliberadamente pequeno. Seu objetivo não é provar
inteligência geral, mas verificar se um mecanismo supera a memorização de casos
exatos em exemplos inéditos de um ambiente controlado.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Situacao:
    massa: float
    forca: float

    @property
    def relacao_forca_massa(self) -> float:
        return self.forca / self.massa


class AmbienteDeMovimento:
    """Ambiente oculto cuja regra é observada somente por meio de ações."""

    def executar(self, situacao: Situacao) -> bool:
        if situacao.massa <= 0:
            raise ValueError("A massa precisa ser maior que zero.")
        if situacao.forca < 0:
            raise ValueError("A força não pode ser negativa neste ambiente.")
        return situacao.forca >= situacao.massa


class MemorizadorExato:
    """Baseline: retém casos vistos; para casos novos usa a classe mais frequente."""

    def __init__(self) -> None:
        self.casos: dict[Situacao, bool] = {}
        self.resultados: list[bool] = []

    def observar(self, situacao: Situacao, resultado: bool) -> None:
        self.casos[situacao] = resultado
        self.resultados.append(resultado)

    def prever(self, situacao: Situacao) -> bool:
        if situacao in self.casos:
            return self.casos[situacao]
        return self.resultados.count(True) > self.resultados.count(False)


class AprendizDeLimiar:
    """Estima um limiar a partir de experiências positivas e negativas.

    A escolha da relação força/massa é um viés de projeto explícito. A regra
    exata do ambiente não é inserida: o limiar é calculado apenas a partir dos
    resultados observados.
    """

    def __init__(self) -> None:
        self.maior_relacao_sem_movimento: float | None = None
        self.menor_relacao_com_movimento: float | None = None

    def observar(self, situacao: Situacao, resultado: bool) -> None:
        relacao = situacao.relacao_forca_massa
        if resultado:
            if (
                self.menor_relacao_com_movimento is None
                or relacao < self.menor_relacao_com_movimento
            ):
                self.menor_relacao_com_movimento = relacao
        elif (
            self.maior_relacao_sem_movimento is None
            or relacao > self.maior_relacao_sem_movimento
        ):
            self.maior_relacao_sem_movimento = relacao

    @property
    def limiar_estimado(self) -> float | None:
        if (
            self.maior_relacao_sem_movimento is None
            or self.menor_relacao_com_movimento is None
        ):
            return None
        return (
            self.maior_relacao_sem_movimento + self.menor_relacao_com_movimento
        ) / 2

    def prever(self, situacao: Situacao) -> bool:
        limiar = self.limiar_estimado
        if limiar is None:
            raise RuntimeError("Ainda não há evidência suficiente para estimar um limiar.")
        return situacao.relacao_forca_massa >= limiar


AMOSTRAS_DE_APRENDIZAGEM = (
    Situacao(massa=1, forca=0.5),
    Situacao(massa=1, forca=1),
    Situacao(massa=2, forca=1),
    Situacao(massa=2, forca=2),
    Situacao(massa=3, forca=1.5),
    Situacao(massa=3, forca=3),
)

AMOSTRAS_DE_AVALIACAO = (
    Situacao(massa=4, forca=2),
    Situacao(massa=5, forca=2.5),
    Situacao(massa=6, forca=3),
    Situacao(massa=4, forca=4),
    Situacao(massa=3, forca=4.5),
    Situacao(massa=4, forca=6),
)


def _acuracia(previsoes: list[bool], resultados: list[bool]) -> float:
    return sum(previsao == resultado for previsao, resultado in zip(previsoes, resultados)) / len(
        resultados
    )


def executar_experimento() -> dict[str, object]:
    ambiente = AmbienteDeMovimento()
    eva = AprendizDeLimiar()
    baseline = MemorizadorExato()

    for situacao in AMOSTRAS_DE_APRENDIZAGEM:
        resultado = ambiente.executar(situacao)
        eva.observar(situacao, resultado)
        baseline.observar(situacao, resultado)

    resultados_reais = [ambiente.executar(situacao) for situacao in AMOSTRAS_DE_AVALIACAO]
    previsoes_eva = [eva.prever(situacao) for situacao in AMOSTRAS_DE_AVALIACAO]
    previsoes_baseline = [baseline.prever(situacao) for situacao in AMOSTRAS_DE_AVALIACAO]

    return {
        "experimento": "EXP-001",
        "amostras_de_aprendizagem": len(AMOSTRAS_DE_APRENDIZAGEM),
        "amostras_de_avaliacao": len(AMOSTRAS_DE_AVALIACAO),
        "limiar_estimado": eva.limiar_estimado,
        "acuracia_eva": _acuracia(previsoes_eva, resultados_reais),
        "acuracia_baseline": _acuracia(previsoes_baseline, resultados_reais),
        "avaliacao": [
            {
                **asdict(situacao),
                "resultado_real": resultado,
                "previsao_eva": previsao_eva,
                "previsao_baseline": previsao_baseline,
            }
            for situacao, resultado, previsao_eva, previsao_baseline in zip(
                AMOSTRAS_DE_AVALIACAO,
                resultados_reais,
                previsoes_eva,
                previsoes_baseline,
            )
        ],
    }


if __name__ == "__main__":
    print(json.dumps(executar_experimento(), ensure_ascii=False, indent=2))
