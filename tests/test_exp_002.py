import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from experimentos.exp_002 import (
    APRENDIZAGEM_APOS_MUDANCA,
    APRENDIZAGEM_FASE_1,
    AVALIACAO_APOS_MUDANCA,
    AVALIACAO_FASE_1,
    ModeloDeLimiarRecente,
    Situacao,
    executar_experimento,
)


class TestExp002(unittest.TestCase):
    def test_avaliacoes_sao_separadas_das_experiencias(self) -> None:
        aprendizagem = set(APRENDIZAGEM_FASE_1 + APRENDIZAGEM_APOS_MUDANCA)

        self.assertTrue(aprendizagem.isdisjoint(AVALIACAO_FASE_1))
        self.assertTrue(aprendizagem.isdisjoint(AVALIACAO_APOS_MUDANCA))

    def test_modelo_exige_evidencia_dos_dois_resultados(self) -> None:
        modelo = ModeloDeLimiarRecente()
        modelo.observar(Situacao(1, 1), True)

        with self.assertRaises(RuntimeError):
            modelo.prever(Situacao(2, 2))

    def test_adaptacao_recupera_desempenho_apos_mudanca(self) -> None:
        resultado = executar_experimento()

        self.assertEqual(resultado["acuracia_inicial"], 1.0)
        self.assertEqual(
            resultado["acuracia_apos_mudanca_antes_de_novas_experiencias"], 0.5
        )
        self.assertEqual(resultado["acuracia_apos_adaptacao"], 1.0)
        self.assertEqual(resultado["acuracia_modelo_congelado_apos_mudanca"], 0.5)
