import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from experimentos.exp_003 import (
    APRENDIZAGEM_A,
    APRENDIZAGEM_B,
    AVALIACAO_RETORNO_A,
    MemoriaPorContexto,
    Situacao,
    executar_experimento,
)


class TestExp003(unittest.TestCase):
    def test_avaliacao_do_retorno_nao_foi_experiencia(self) -> None:
        aprendizagem = set(APRENDIZAGEM_A + APRENDIZAGEM_B)

        self.assertTrue(aprendizagem.isdisjoint(AVALIACAO_RETORNO_A))

    def test_contexto_nunca_observado_nao_recebe_previsao_inventada(self) -> None:
        memoria = MemoriaPorContexto()

        with self.assertRaises(RuntimeError):
            memoria.prever(Situacao("C", 1, 1))

    def test_retencao_supera_modelo_sem_contexto_no_retorno(self) -> None:
        resultado = executar_experimento()

        self.assertEqual(resultado["contextos_retidos"], 2)
        self.assertEqual(resultado["acuracia_eva_no_retorno_a"], 1.0)
        self.assertEqual(resultado["acuracia_controle_no_retorno_a"], 0.4)
        self.assertGreater(
            resultado["acuracia_eva_no_retorno_a"],
            resultado["acuracia_controle_no_retorno_a"],
        )
