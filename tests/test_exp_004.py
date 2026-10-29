import sys
import unittest
from dataclasses import fields
from inspect import signature
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from experimentos.exp_004 import (
    AmbienteOculto,
    ComparadorDeModelos,
    Entrada,
    FiltroBayesianoDoisEstados,
    LIMIARES_REAIS,
    Observacao,
    ModeloDeLimiar,
    SEMENTES_AVALIACAO_FINAL_RESERVADAS,
    SEMENTES_DESENVOLVIMENTO,
    executar_sequencia_de_desenvolvimento,
    gerar_contextos,
    gerar_entradas,
)


def passo(agente: ComparadorDeModelos, relacao: float, moveu: bool) -> None:
    entrada = Entrada(massa=10, forca=10 * relacao)
    previsao = agente.prever(entrada)
    agente.observar(Observacao(entrada, moveu), previsao)


def agente_com_dois_modelos() -> ComparadorDeModelos:
    agente = ComparadorDeModelos()
    primeiro = agente.modelos[0]
    primeiro.atualizar(Observacao(Entrada(10, 5), False))
    primeiro.atualizar(Observacao(Entrada(10, 10), True))
    segundo = ModeloDeLimiar()
    segundo.atualizar(Observacao(Entrada(10, 12), False))
    segundo.atualizar(Observacao(Entrada(10, 13), False))
    segundo.atualizar(Observacao(Entrada(10, 16), True))
    agente.modelos[1] = segundo
    return agente


class TestExp004(unittest.TestCase):
    def test_observacao_nao_contem_rotulo_de_contexto(self) -> None:
        self.assertEqual([campo.name for campo in fields(Observacao)], ["entrada", "moveu"])

    def test_interface_do_agente_nao_recebe_contexto_oculto(self) -> None:
        self.assertEqual(
            list(signature(ComparadorDeModelos.prever).parameters), ["self", "entrada"]
        )
        self.assertEqual(
            list(signature(ComparadorDeModelos.observar).parameters),
            ["self", "observacao", "previsao_anterior"],
        )

    def test_ambiente_oculto_e_reproduzivel_com_mesma_semente(self) -> None:
        entradas = gerar_entradas(8, semente=SEMENTES_DESENVOLVIMENTO[0])
        contextos = gerar_contextos("ABAB", tamanho_bloco=2)
        primeiro = AmbienteOculto(contextos, semente=99, probabilidade_de_ruido=0.25)
        segundo = AmbienteOculto(contextos, semente=99, probabilidade_de_ruido=0.25)

        resultados_1 = [primeiro.observar(entrada).moveu for entrada in entradas]
        resultados_2 = [segundo.observar(entrada).moveu for entrada in entradas]

        self.assertEqual(resultados_1, resultados_2)

    def test_gerador_permite_condicao_sem_evidencia_diagnostica(self) -> None:
        entradas = gerar_entradas(20, semente=SEMENTES_DESENVOLVIMENTO[0], fracao_diagnostica=0.0)

        self.assertFalse(any(entrada.e_diagnostica for entrada in entradas))

    def test_previsao_e_registrada_antes_da_observacao(self) -> None:
        agente = ComparadorDeModelos()
        registros, metricas = executar_sequencia_de_desenvolvimento(
            agente, padrao="ABAB", semente=SEMENTES_DESENVOLVIMENTO[0]
        )

        self.assertIsNone(registros[0].previsao_antes.moveu)
        self.assertGreater(metricas.abstencoes, 0)
        self.assertEqual(len(registros), 4 * 40)

    def test_modelo_anterior_e_recuperado_sem_rotulo_de_contexto(self) -> None:
        agente = ComparadorDeModelos()
        passo(agente, 0.5, False)
        passo(agente, 1.0, True)

        for _ in range(4):
            passo(agente, 1.2, False)
        passo(agente, 1.6, True)

        for _ in range(4):
            passo(agente, 1.1, True)

        self.assertTrue(any(evento.tipo == "novo_modelo" for evento in agente.eventos))
        self.assertTrue(any(evento.tipo == "modelo_recuperado" for evento in agente.eventos))
        recuperacao = next(i for i, evento in enumerate(agente.eventos) if evento.tipo == "modelo_recuperado")
        atualizacao = next(
            i
            for i, evento in enumerate(agente.eventos[recuperacao + 1 :], start=recuperacao + 1)
            if evento.tipo == "modelo_atualizado" and evento.modelo_id == 0
        )
        self.assertLess(recuperacao, atualizacao)

    def test_concordancia_sem_evidencia_anterior_nao_declara_contexto(self) -> None:
        agente = agente_com_dois_modelos()

        previsao = agente.prever(Entrada(10, 5))

        self.assertFalse(previsao.moveu)
        self.assertEqual(previsao.suporte_resultado, "concordante_entre_modelos")
        self.assertIsNone(previsao.hipotese_contexto)
        self.assertEqual(previsao.suporte_contexto, "insuficiente")

    def test_concordancia_preserva_hipotese_ja_sustentada(self) -> None:
        agente = ComparadorDeModelos()
        passo(agente, 0.5, False)
        passo(agente, 1.0, True)
        for _ in range(4):
            passo(agente, 1.2, False)
        passo(agente, 1.6, True)
        for _ in range(4):
            passo(agente, 1.1, True)

        previsao = agente.prever(Entrada(10, 5))

        self.assertFalse(previsao.moveu)
        self.assertEqual(previsao.hipotese_contexto, 0)
        self.assertEqual(previsao.suporte_contexto, "historico_sustentado")

    def test_divergencia_sem_evidencia_suficiente_permanece_incerta(self) -> None:
        agente = agente_com_dois_modelos()

        previsao = agente.prever(Entrada(10, 11))

        self.assertTrue(previsao.moveu)
        self.assertEqual(previsao.suporte_resultado, "modelos_divergentes")
        self.assertIsNone(previsao.hipotese_contexto)
        self.assertEqual(previsao.suporte_contexto, "insuficiente")

    def test_evidencia_diagnostica_favorece_modelo_sem_rotulo_externo(self) -> None:
        agente = agente_com_dois_modelos()
        agente.modelo_ativo = 1

        previsao = agente.prever(Entrada(10, 12))

        self.assertFalse(previsao.moveu)
        self.assertEqual(previsao.hipotese_contexto, 1)
        self.assertEqual(previsao.suporte_contexto, "evidencia_diagnostica_acumulada")

    def test_sequencia_totalmente_ambigua_nao_identifica_contexto(self) -> None:
        agente = agente_com_dois_modelos()
        previsoes = []
        for _ in range(8):
            entrada = Entrada(10, 5)
            previsao = agente.prever(entrada)
            previsoes.append(previsao)
            agente.observar(Observacao(entrada, False), previsao)

        self.assertTrue(all(previsao.hipotese_contexto is None for previsao in previsoes))
        self.assertFalse(
            any(
                evento.tipo
                in {"suspeita_de_mudanca", "mudanca_detectada", "modelo_recuperado"}
                for evento in agente.eventos
            )
        )

    def test_sementes_finais_nao_se_confundem_com_desenvolvimento(self) -> None:
        self.assertTrue(set(SEMENTES_DESENVOLVIMENTO).isdisjoint(SEMENTES_AVALIACAO_FINAL_RESERVADAS))

    def test_limiares_reais_nao_sao_argumento_do_agente(self) -> None:
        agente = ComparadorDeModelos()

        self.assertEqual(len(agente.modelos[0].experiencias), 0)
        self.assertEqual(LIMIARES_REAIS, {"A": 1.0, "B": 1.5})

    def test_filtro_bayesiano_comeca_sem_modelo_pronto(self) -> None:
        filtro = FiltroBayesianoDoisEstados()
        entrada = Entrada(massa=2, forca=2)

        previsao = filtro.prever(entrada)
        filtro.observar(Observacao(entrada, True), previsao)

        self.assertIsNone(previsao.moveu)
        self.assertEqual(sum(filtro.crencas.values()), 1.0)
        self.assertEqual(sum(len(modelo.experiencias) for modelo in filtro.modelos.values()), 1)
