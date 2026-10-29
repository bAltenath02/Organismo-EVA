"""Infraestrutura de desenvolvimento do EXP-004.

O ambiente possui contextos A/B ocultos. Agentes recebem apenas entrada e
resultado: os rótulos reais ficam restritos ao avaliador.

Este módulo não executa a avaliação final reservada.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from random import Random
from typing import Protocol


LIMIARES_REAIS = {"A": 1.0, "B": 1.5}
TAMANHO_BLOCO = 40
SEMENTES_DESENVOLVIMENTO = (101, 211, 307, 401)
SEMENTES_AVALIACAO_FINAL_RESERVADAS = (1009, 1013, 1021, 1031, 1033)


@dataclass(frozen=True)
class Entrada:
    massa: float
    forca: float

    @property
    def relacao_forca_massa(self) -> float:
        return self.forca / self.massa

    @property
    def e_diagnostica(self) -> bool:
        return 1.0 <= self.relacao_forca_massa < 1.5


@dataclass(frozen=True)
class Observacao:
    """Única informação devolvida ao agente após uma previsão."""

    entrada: Entrada
    moveu: bool


@dataclass(frozen=True)
class Previsao:
    moveu: bool | None
    suporte_resultado: str
    hipotese_contexto: int | str | None
    suporte_contexto: str


@dataclass(frozen=True)
class Evento:
    indice: int
    tipo: str
    modelo_id: int | None


class AmbienteOculto:
    """Aplica a sequência A/B internamente e nunca a inclui em ``Observacao``."""

    def __init__(
        self,
        contextos_ocultos: tuple[str, ...],
        *,
        semente: int,
        probabilidade_de_ruido: float = 0.0,
    ) -> None:
        if not contextos_ocultos:
            raise ValueError("O ambiente exige pelo menos um contexto oculto.")
        if any(contexto not in LIMIARES_REAIS for contexto in contextos_ocultos):
            raise ValueError("O ambiente aceita somente os contextos A e B.")
        if not 0.0 <= probabilidade_de_ruido <= 1.0:
            raise ValueError("A probabilidade de ruído deve estar entre 0 e 1.")
        self._contextos = contextos_ocultos
        self._aleatorio = Random(semente)
        self._ruido = probabilidade_de_ruido
        self._indice = 0

    def observar(self, entrada: Entrada) -> Observacao:
        if self._indice >= len(self._contextos):
            raise RuntimeError("A sequência do ambiente já terminou.")
        if entrada.massa <= 0 or entrada.forca < 0:
            raise ValueError("Massa deve ser positiva e força não pode ser negativa.")
        contexto = self._contextos[self._indice]
        moveu = entrada.relacao_forca_massa >= LIMIARES_REAIS[contexto]
        if self._aleatorio.random() < self._ruido:
            moveu = not moveu
        self._indice += 1
        return Observacao(entrada=entrada, moveu=moveu)


class ModeloDeLimiar:
    """Modelo aprendido: não recebe o limiar real do ambiente."""

    def __init__(self) -> None:
        self.experiencias: list[Observacao] = []

    def atualizar(self, observacao: Observacao) -> None:
        self.experiencias.append(observacao)

    @property
    def limiar_estimado(self) -> float | None:
        negativos = [
            observacao.entrada.relacao_forca_massa
            for observacao in self.experiencias
            if not observacao.moveu
        ]
        positivos = [
            observacao.entrada.relacao_forca_massa
            for observacao in self.experiencias
            if observacao.moveu
        ]
        if not negativos or not positivos:
            return None
        return (max(negativos) + min(positivos)) / 2

    def prever(self, entrada: Entrada) -> bool | None:
        limiar = self.limiar_estimado
        return None if limiar is None else entrada.relacao_forca_massa >= limiar


class Agente(Protocol):
    eventos: list[Evento]

    def prever(self, entrada: Entrada) -> Previsao: ...

    def observar(self, observacao: Observacao, previsao_anterior: Previsao) -> None: ...


class ComparadorDeModelos:
    """Candidato principal: compara modelos aprendidos após erro acumulado.

    Um modelo estável não é atualizado com suas próprias previsões erradas. Os
    erros formam um buffer; após três erros em quatro previsões, o agente tenta
    recuperar outro modelo ou inicia o segundo modelo permitido pelo EXP-004.
    """

    def __init__(self, *, tamanho_janela_erro: int = 4, limite_erro: int = 3) -> None:
        self.modelos: dict[int, ModeloDeLimiar] = {0: ModeloDeLimiar()}
        self.modelo_ativo = 0
        self.eventos: list[Evento] = []
        self._indice = 0
        self._erros: deque[bool] = deque(maxlen=tamanho_janela_erro)
        self._buffer_de_mudanca: deque[Observacao] = deque(maxlen=tamanho_janela_erro)
        self._limite_erro = limite_erro
        self._suspeita_ativa = False
        self._contexto_sustentado: int | None = None

    def prever(self, entrada: Entrada) -> Previsao:
        previsoes: dict[int, bool] = {}
        for modelo_id, modelo in self.modelos.items():
            movimento = modelo.prever(entrada)
            if movimento is not None:
                previsoes[modelo_id] = movimento
        if not previsoes:
            return Previsao(None, "insuficiente", None, "insuficiente")

        resultados = set(previsoes.values())
        if len(resultados) == 1:
            hipotese = (
                self._contexto_sustentado
                if self._contexto_sustentado in previsoes
                else None
            )
            return Previsao(
                next(iter(resultados)),
                "concordante_entre_modelos" if len(previsoes) > 1 else "modelo_unico",
                hipotese,
                "historico_sustentado" if hipotese is not None else "insuficiente",
            )

        movimento = previsoes.get(self.modelo_ativo)
        if movimento is None:
            return Previsao(None, "insuficiente", None, "insuficiente")
        if self._contexto_sustentado == self.modelo_ativo:
            return Previsao(movimento, "modelos_divergentes", self.modelo_ativo, "historico_sustentado")
        if self._evidencias_diagnosticas(self.modelo_ativo) >= 2:
            return Previsao(
                movimento,
                "modelos_divergentes",
                self.modelo_ativo,
                "evidencia_diagnostica_acumulada",
            )
        return Previsao(movimento, "modelos_divergentes", None, "insuficiente")

    def observar(self, observacao: Observacao, previsao_anterior: Previsao) -> None:
        modelo_ativo = self.modelos[self.modelo_ativo]
        if previsao_anterior.moveu is None:
            self._atualizar_modelo(self.modelo_ativo, observacao)
            self._indice += 1
            return

        erro = previsao_anterior.moveu != observacao.moveu
        self._erros.append(erro)
        if erro:
            self._buffer_de_mudanca.append(observacao)
        else:
            self._atualizar_modelo(self.modelo_ativo, observacao)

        if len(self._erros) >= 2 and sum(self._erros) >= 2 and not self._suspeita_ativa:
            self.eventos.append(Evento(self._indice, "suspeita_de_mudanca", self.modelo_ativo))
            self._suspeita_ativa = True

        if len(self._erros) == self._erros.maxlen and sum(self._erros) >= self._limite_erro:
            self._detectar_e_selecionar_modelo()
        self._indice += 1

    def _detectar_e_selecionar_modelo(self) -> None:
        self.eventos.append(Evento(self._indice, "mudanca_detectada", self.modelo_ativo))
        alternativas = [
            (self._erros_no_buffer(modelo), modelo_id)
            for modelo_id, modelo in self.modelos.items()
            if modelo_id != self.modelo_ativo
        ]

        if alternativas:
            erros, modelo_id = min(alternativas)
            if erros == 0:
                self.modelo_ativo = modelo_id
                self._contexto_sustentado = modelo_id
                self.eventos.append(Evento(self._indice, "modelo_recuperado", modelo_id))
                for observacao in self._buffer_de_mudanca:
                    self._atualizar_modelo(modelo_id, observacao)
                self._reiniciar_evidencia()
                return

        if len(self.modelos) < 2:
            novo_id = max(self.modelos) + 1
            novo_modelo = ModeloDeLimiar()
            for observacao in self._buffer_de_mudanca:
                novo_modelo.atualizar(observacao)
            self.modelos[novo_id] = novo_modelo
            self.modelo_ativo = novo_id
            self.eventos.append(Evento(self._indice, "novo_modelo", novo_id))
            for _ in self._buffer_de_mudanca:
                self.eventos.append(Evento(self._indice, "modelo_atualizado", novo_id))
            self._reiniciar_evidencia()
        else:
            self.eventos.append(Evento(self._indice, "incerteza", None))

    def _erros_no_buffer(self, modelo: ModeloDeLimiar) -> int:
        previsoes = [modelo.prever(observacao.entrada) for observacao in self._buffer_de_mudanca]
        if any(previsao is None for previsao in previsoes):
            return len(self._buffer_de_mudanca)
        return sum(
            previsao != observacao.moveu
            for previsao, observacao in zip(previsoes, self._buffer_de_mudanca)
        )

    def _reiniciar_evidencia(self) -> None:
        self._erros.clear()
        self._buffer_de_mudanca.clear()
        self._suspeita_ativa = False

    def _atualizar_modelo(self, modelo_id: int, observacao: Observacao) -> None:
        self.modelos[modelo_id].atualizar(observacao)
        self.eventos.append(Evento(self._indice, "modelo_atualizado", modelo_id))

    def _evidencias_diagnosticas(self, modelo_id: int) -> int:
        return sum(
            observacao.entrada.e_diagnostica
            for observacao in self.modelos[modelo_id].experiencias
        )


class DetectorDeErroAcumulado:
    """Comparação: detecta mudança e substitui o modelo atual, sem recuperação."""

    def __init__(self, *, tamanho_janela_erro: int = 4, limite_erro: int = 3) -> None:
        self.modelo = ModeloDeLimiar()
        self.eventos: list[Evento] = []
        self._indice = 0
        self._erros: deque[bool] = deque(maxlen=tamanho_janela_erro)
        self._buffer: deque[Observacao] = deque(maxlen=tamanho_janela_erro)
        self._limite_erro = limite_erro

    def prever(self, entrada: Entrada) -> Previsao:
        movimento = self.modelo.prever(entrada)
        return Previsao(
            movimento,
            "modelo_unico" if movimento is not None else "insuficiente",
            None,
            "insuficiente",
        )

    def observar(self, observacao: Observacao, previsao_anterior: Previsao) -> None:
        if previsao_anterior.moveu is None:
            self.modelo.atualizar(observacao)
            self._indice += 1
            return
        erro = previsao_anterior.moveu != observacao.moveu
        self._erros.append(erro)
        if erro:
            self._buffer.append(observacao)
        else:
            self.modelo.atualizar(observacao)
        if len(self._erros) == self._erros.maxlen and sum(self._erros) >= self._limite_erro:
            self.eventos.append(Evento(self._indice, "mudanca_detectada", 0))
            self.modelo = ModeloDeLimiar()
            for experiencia in self._buffer:
                self.modelo.atualizar(experiencia)
            self._erros.clear()
            self._buffer.clear()
        self._indice += 1


class FiltroBayesianoDoisEstados:
    """Referência estatística: filtro online com dois estados ocultos.

    Cada estado possui um modelo de limiar aprendido por observações atribuídas
    ao estado mais provável. A inferência usa uma matriz de transição fixa e
    probabilidades de emissão baseadas no acerto preditivo. Os estados são IDs
    internos, não os rótulos A/B do ambiente.
    """

    def __init__(self, probabilidade_de_troca: float = 0.05) -> None:
        if not 0.0 < probabilidade_de_troca < 0.5:
            raise ValueError("A probabilidade de troca deve estar entre 0 e 0,5.")
        self.modelos = {0: ModeloDeLimiar(), 1: ModeloDeLimiar()}
        self.crencas = {0: 0.5, 1: 0.5}
        self.eventos: list[Evento] = []
        self._troca = probabilidade_de_troca
        self._indice = 0
        self._estado_mais_provavel = 0

    def prever(self, entrada: Entrada) -> Previsao:
        estado = max(self.crencas, key=self.crencas.get)
        movimento = self.modelos[estado].prever(entrada)
        return Previsao(
            movimento,
            "pontuacao_bayesiana_nao_calibrada" if movimento is not None else "insuficiente",
            estado if movimento is not None else None,
            "pontuacao_bayesiana_nao_calibrada" if movimento is not None else "insuficiente",
        )

    def observar(self, observacao: Observacao, previsao_anterior: Previsao) -> None:
        priori = {
            0: self.crencas[0] * (1 - self._troca) + self.crencas[1] * self._troca,
            1: self.crencas[1] * (1 - self._troca) + self.crencas[0] * self._troca,
        }
        verossimilhancas = {}
        for estado, modelo in self.modelos.items():
            previsao = modelo.prever(observacao.entrada)
            if previsao is None:
                verossimilhancas[estado] = 0.5
            else:
                verossimilhancas[estado] = 0.9 if previsao == observacao.moveu else 0.1
        evidencia = sum(priori[estado] * verossimilhancas[estado] for estado in self.modelos)
        self.crencas = {
            estado: (priori[estado] * verossimilhancas[estado]) / evidencia
            for estado in self.modelos
        }
        novo_estado = max(self.crencas, key=self.crencas.get)
        if novo_estado != self._estado_mais_provavel:
            self.eventos.append(Evento(self._indice, "mudanca_estimada", novo_estado))
        self._estado_mais_provavel = novo_estado
        self.modelos[novo_estado].atualizar(observacao)
        self._indice += 1


class ModeloJanelaRecente:
    """Controle adaptativo sem retenção de modelos anteriores."""

    def __init__(self, tamanho_janela: int = 12) -> None:
        self.experiencias: deque[Observacao] = deque(maxlen=tamanho_janela)
        self.eventos: list[Evento] = []

    def prever(self, entrada: Entrada) -> Previsao:
        modelo = ModeloDeLimiar()
        for observacao in self.experiencias:
            modelo.atualizar(observacao)
        movimento = modelo.prever(entrada)
        return Previsao(
            movimento,
            "janela_recente" if movimento is not None else "insuficiente",
            None,
            "insuficiente",
        )

    def observar(self, observacao: Observacao, previsao_anterior: Previsao) -> None:
        self.experiencias.append(observacao)


class ModeloCongelado:
    """Controle que aprende somente durante o aquecimento inicial."""

    def __init__(self, aquecimento: int = 12) -> None:
        self.modelo = ModeloDeLimiar()
        self.eventos: list[Evento] = []
        self._aquecimento = aquecimento
        self._observacoes = 0

    def prever(self, entrada: Entrada) -> Previsao:
        movimento = self.modelo.prever(entrada)
        return Previsao(
            movimento,
            "modelo_congelado" if movimento is not None else "insuficiente",
            None,
            "insuficiente",
        )

    def observar(self, observacao: Observacao, previsao_anterior: Previsao) -> None:
        if self._observacoes < self._aquecimento:
            self.modelo.atualizar(observacao)
        self._observacoes += 1


class ReferenciaInformada:
    """Referência superior: somente ela recebe o contexto verdadeiro do avaliador."""

    def __init__(self) -> None:
        self.modelos = {"A": ModeloDeLimiar(), "B": ModeloDeLimiar()}
        self.eventos: list[Evento] = []

    def prever_com_contexto_real(self, entrada: Entrada, contexto_real: str) -> Previsao:
        movimento = self.modelos[contexto_real].prever(entrada)
        return Previsao(
            movimento,
            "referencia_informada" if movimento is not None else "insuficiente",
            contexto_real if movimento is not None else None,
            "referencia_informada" if movimento is not None else "insuficiente",
        )

    def observar_com_contexto_real(self, observacao: Observacao, contexto_real: str) -> None:
        self.modelos[contexto_real].atualizar(observacao)


@dataclass(frozen=True)
class RegistroDeAvaliacao:
    indice: int
    previsao_antes: Previsao
    observacao: Observacao
    contexto_real: str


@dataclass
class Metricas:
    acuracia_antes_da_atualizacao: float | None
    abstencoes: int
    atrasos_de_deteccao: list[int]
    falsos_alarmes: int
    recuperacoes_de_modelo: int
    acuracia_diagnostica: float | None
    acuracia_ambigua: float | None
    declaracoes_indevidas_de_contexto: int


def gerar_contextos(padrao: str, tamanho_bloco: int = TAMANHO_BLOCO) -> tuple[str, ...]:
    if padrao not in {"ABAB", "BABA"}:
        raise ValueError("O padrão deve ser ABAB ou BABA.")
    return tuple(contexto for contexto in padrao for _ in range(tamanho_bloco))


def gerar_entradas(
    quantidade: int,
    *,
    semente: int,
    fracao_diagnostica: float = 1 / 3,
) -> tuple[Entrada, ...]:
    """Gera entradas estratificadas; rótulos continuam desconhecidos ao agente."""
    if not 0.0 <= fracao_diagnostica <= 1.0:
        raise ValueError("A fração diagnóstica deve estar entre 0 e 1.")
    aleatorio = Random(semente)
    entradas = []
    for indice in range(quantidade):
        massa = aleatorio.randint(1, 10)
        if aleatorio.random() < fracao_diagnostica:
            relacao = aleatorio.uniform(1.05, 1.45)
        elif indice % 2 == 0:
            relacao = aleatorio.uniform(0.35, 0.90)
        else:
            relacao = aleatorio.uniform(1.60, 2.10)
        entradas.append(Entrada(massa=massa, forca=massa * relacao))
    return tuple(entradas)


def executar_sequencia_de_desenvolvimento(
    agente: Agente,
    *,
    padrao: str,
    semente: int,
    probabilidade_de_ruido: float = 0.0,
) -> tuple[list[RegistroDeAvaliacao], Metricas]:
    """Executa apenas sequência de desenvolvimento; não usa sementes reservadas."""
    if semente not in SEMENTES_DESENVOLVIMENTO:
        raise ValueError("Use apenas sementes de desenvolvimento nesta função.")
    contextos = gerar_contextos(padrao)
    ambiente = AmbienteOculto(
        contextos, semente=semente, probabilidade_de_ruido=probabilidade_de_ruido
    )
    entradas = gerar_entradas(len(contextos), semente=semente)
    registros: list[RegistroDeAvaliacao] = []

    for indice, entrada in enumerate(entradas):
        previsao = agente.prever(entrada)
        observacao = ambiente.observar(entrada)
        agente.observar(observacao, previsao)
        registros.append(
            RegistroDeAvaliacao(indice, previsao, observacao, contextos[indice])
        )
    return registros, calcular_metricas(registros, agente.eventos)


def calcular_metricas(registros: list[RegistroDeAvaliacao], eventos: list[Evento]) -> Metricas:
    previstos = [registro for registro in registros if registro.previsao_antes.moveu is not None]
    acuracia = (
        sum(registro.previsao_antes.moveu == registro.observacao.moveu for registro in previstos)
        / len(previstos)
        if previstos
        else None
    )

    def acuracia_por_tipo(diagnostica: bool) -> float | None:
        grupo = [
            registro
            for registro in previstos
            if registro.observacao.entrada.e_diagnostica == diagnostica
        ]
        return (
            sum(registro.previsao_antes.moveu == registro.observacao.moveu for registro in grupo)
            / len(grupo)
            if grupo
            else None
        )

    transicoes = [
        registro.indice
        for registro in registros[1:]
        if registro.contexto_real != registros[registro.indice - 1].contexto_real
    ]
    deteccoes = [evento.indice for evento in eventos if evento.tipo == "mudanca_detectada"]
    atrasos: list[int] = []
    usadas: set[int] = set()
    for posicao, transicao in enumerate(transicoes):
        fim_da_fase = (
            transicoes[posicao + 1] if posicao + 1 < len(transicoes) else len(registros)
        )
        candidatas = [
            (indice, deteccao)
            for indice, deteccao in enumerate(deteccoes)
            if indice not in usadas and transicao <= deteccao < fim_da_fase
        ]
        if candidatas:
            indice, deteccao = candidatas[0]
            usadas.add(indice)
            atrasos.append(deteccao - transicao)
    falsos = len(deteccoes) - len(usadas)
    recuperacoes = sum(evento.tipo == "modelo_recuperado" for evento in eventos)
    declaracoes_indevidas = sum(
        registro.previsao_antes.hipotese_contexto is not None
        and registro.previsao_antes.suporte_contexto == "evidencia_diagnostica_acumulada"
        and not registro.observacao.entrada.e_diagnostica
        for registro in registros
    )
    return Metricas(
        acuracia_antes_da_atualizacao=acuracia,
        abstencoes=len(registros) - len(previstos),
        atrasos_de_deteccao=atrasos,
        falsos_alarmes=falsos,
        recuperacoes_de_modelo=recuperacoes,
        acuracia_diagnostica=acuracia_por_tipo(True),
        acuracia_ambigua=acuracia_por_tipo(False),
        declaracoes_indevidas_de_contexto=declaracoes_indevidas,
    )
