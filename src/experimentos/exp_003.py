"""EXP-003: retenção de modelos quando um contexto conhecido retorna."""

from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Situacao:
    contexto: str
    massa: float
    forca: float

    @property
    def relacao_forca_massa(self) -> float:
        return self.forca / self.massa


class AmbientePorContexto:
    """Ambiente com contexto perceptível e uma regra por contexto."""

    def __init__(self, limiares: dict[str, float]) -> None:
        self.limiares = limiares

    def executar(self, situacao: Situacao) -> bool:
        if situacao.contexto not in self.limiares:
            raise ValueError(f"Contexto desconhecido: {situacao.contexto}.")
        if situacao.massa <= 0:
            raise ValueError("A massa precisa ser maior que zero.")
        return situacao.relacao_forca_massa >= self.limiares[situacao.contexto]


class ModeloDeLimiar:
    def __init__(self) -> None:
        self.experiencias: list[tuple[Situacao, bool]] = []

    def observar(self, situacao: Situacao, resultado: bool) -> None:
        self.experiencias.append((situacao, resultado))

    @property
    def limiar_estimado(self) -> float | None:
        negativos = [s.relacao_forca_massa for s, resultado in self.experiencias if not resultado]
        positivos = [s.relacao_forca_massa for s, resultado in self.experiencias if resultado]
        if not negativos or not positivos:
            return None
        return (max(negativos) + min(positivos)) / 2

    def prever(self, situacao: Situacao) -> bool:
        if self.limiar_estimado is None:
            raise RuntimeError("Não há evidências suficientes para estimar um limiar.")
        return situacao.relacao_forca_massa >= self.limiar_estimado


class MemoriaPorContexto:
    """Retém um modelo independente para cada contexto observado."""

    def __init__(self) -> None:
        self.modelos: dict[str, ModeloDeLimiar] = {}

    def observar(self, situacao: Situacao, resultado: bool) -> None:
        modelo = self.modelos.setdefault(situacao.contexto, ModeloDeLimiar())
        modelo.observar(situacao, resultado)

    def prever(self, situacao: Situacao) -> bool:
        if situacao.contexto not in self.modelos:
            raise RuntimeError(f"Ainda não existe modelo para o contexto '{situacao.contexto}'.")
        return self.modelos[situacao.contexto].prever(situacao)


class ModeloRecenteSemContexto:
    """Controle: conserva somente as últimas experiências, sem contexto."""

    def __init__(self, tamanho_da_janela: int = 6) -> None:
        self.experiencias: deque[tuple[Situacao, bool]] = deque(maxlen=tamanho_da_janela)

    def observar(self, situacao: Situacao, resultado: bool) -> None:
        self.experiencias.append((situacao, resultado))

    def prever(self, situacao: Situacao) -> bool:
        modelo = ModeloDeLimiar()
        for experiencia, resultado in self.experiencias:
            modelo.observar(experiencia, resultado)
        return modelo.prever(situacao)


APRENDIZAGEM_A = (
    Situacao("A", 2, 1),
    Situacao("A", 5, 3),
    Situacao("A", 1, 1),
    Situacao("A", 2, 2.4),
    Situacao("A", 3, 3),
    Situacao("A", 5, 6),
)
APRENDIZAGEM_B = (
    Situacao("B", 4, 3),
    Situacao("B", 4, 4),
    Situacao("B", 5, 7),
    Situacao("B", 2, 3),
    Situacao("B", 5, 8),
    Situacao("B", 3, 6),
)
AVALIACAO_RETORNO_A = (
    Situacao("A", 4, 2),
    Situacao("A", 4, 4.2),
    Situacao("A", 10, 11),
    Situacao("A", 10, 12),
    Situacao("A", 5, 8),
)


def _acuracia(modelo: object, ambiente: AmbientePorContexto) -> float:
    previsoes_corretas = sum(
        modelo.prever(situacao) == ambiente.executar(situacao)  # type: ignore[attr-defined]
        for situacao in AVALIACAO_RETORNO_A
    )
    return previsoes_corretas / len(AVALIACAO_RETORNO_A)


def executar_experimento() -> dict[str, object]:
    ambiente = AmbientePorContexto({"A": 1.0, "B": 1.5})
    eva = MemoriaPorContexto()
    controle = ModeloRecenteSemContexto()

    for situacao in APRENDIZAGEM_A + APRENDIZAGEM_B:
        resultado = ambiente.executar(situacao)
        eva.observar(situacao, resultado)
        controle.observar(situacao, resultado)

    return {
        "experimento": "EXP-003",
        "contextos_retidos": len(eva.modelos),
        "limiar_contexto_a": eva.modelos["A"].limiar_estimado,
        "limiar_contexto_b": eva.modelos["B"].limiar_estimado,
        "acuracia_eva_no_retorno_a": _acuracia(eva, ambiente),
        "acuracia_controle_no_retorno_a": _acuracia(controle, ambiente),
        "avaliacao_retorno_a": [
            {
                **asdict(situacao),
                "resultado_real": ambiente.executar(situacao),
                "previsao_eva": eva.prever(situacao),
                "previsao_controle": controle.prever(situacao),
            }
            for situacao in AVALIACAO_RETORNO_A
        ],
    }


if __name__ == "__main__":
    print(json.dumps(executar_experimento(), ensure_ascii=False, indent=2))
