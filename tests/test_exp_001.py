import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from experimentos.exp_001 import (
    AMOSTRAS_DE_APRENDIZAGEM,
    AMOSTRAS_DE_AVALIACAO,
    AprendizDeLimiar,
    Situacao,
    executar_experimento,
)


class TestExp001(unittest.TestCase):
    def test_avaliacao_nao_reutiliza_casos_de_aprendizagem(self) -> None:
        self.assertTrue(
            set(AMOSTRAS_DE_APRENDIZAGEM).isdisjoint(AMOSTRAS_DE_AVALIACAO)
        )

    def test_aprendiz_nao_preve_sem_evidencias_dos_dois_resultados(self) -> None:
        aprendiz = AprendizDeLimiar()
        aprendiz.observar(Situacao(massa=1, forca=1), True)

        with self.assertRaises(RuntimeError):
            aprendiz.prever(Situacao(massa=2, forca=1))

    def test_eva_supera_memorizador_em_casos_ineditos(self) -> None:
        resultado = executar_experimento()

        self.assertEqual(resultado["acuracia_eva"], 1.0)
        self.assertEqual(resultado["acuracia_baseline"], 0.5)
        self.assertGreater(resultado["acuracia_eva"], resultado["acuracia_baseline"])
