import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio import atualizar_dados, gerar_dados


class TestObservatorio(unittest.TestCase):
    def test_painel_usa_resultados_reais_dos_experimentos(self) -> None:
        dados = gerar_dados()

        self.assertEqual(dados["experimentos"]["exp001"]["metricas"][0][1], "100%")
        self.assertEqual(dados["experimentos"]["exp002"]["metricas"][2][1], "100%")
        self.assertEqual(dados["experimentos"]["exp003"]["metricas"][1][1], "100%")

    def test_atualizacao_cria_json_que_o_navegador_pode_ler(self) -> None:
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = atualizar_dados(Path(diretorio) / "dados.json")

            self.assertTrue(caminho.exists())
            self.assertIn('"EXP-001"', caminho.read_text(encoding="utf-8"))
