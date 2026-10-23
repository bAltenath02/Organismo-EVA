import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from memoria import Memoria, MemoriaCorrompidaErro, MemoriaInconsistenteErro


class TestMemoria(unittest.TestCase):
    def setUp(self) -> None:
        self.diretorio = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def test_primeira_inicializacao_cria_identidade_e_evento(self) -> None:
        memoria = Memoria.carregar_ou_criar(self.diretorio)

        self.assertTrue(memoria.primeira_inicializacao)
        self.assertTrue((self.diretorio / "identidade_eva.json").exists())
        self.assertTrue((self.diretorio / "memoria_eva.json").exists())
        self.assertEqual(memoria.estado["experiencias"][0]["tipo"], "nascimento")

    def test_reinicio_recupera_observacao_e_identidade(self) -> None:
        primeira = Memoria.carregar_ou_criar(self.diretorio)
        organismo_id = primeira.identidade["organismo_id"]
        primeira.aprender("cachorro", "Thor")

        reiniciada = Memoria.carregar_ou_criar(self.diretorio)

        self.assertFalse(reiniciada.primeira_inicializacao)
        self.assertEqual(reiniciada.identidade["organismo_id"], organismo_id)
        self.assertEqual(reiniciada.estado["conhecimentos"]["cachorro"]["valor"], "Thor")

    def test_json_vazio_e_valido_mas_estado_incompleto_nao_e_apagado(self) -> None:
        memoria = Memoria.carregar_ou_criar(self.diretorio)
        memoria.caminho_memoria.write_text("{}", encoding="utf-8")

        with self.assertRaises(MemoriaInconsistenteErro):
            Memoria.carregar_ou_criar(self.diretorio)

        self.assertEqual(memoria.caminho_memoria.read_text(encoding="utf-8"), "{}")

    def test_json_invalido_nao_e_substituido(self) -> None:
        memoria = Memoria.carregar_ou_criar(self.diretorio)
        conteudo_invalido = "{ isto não é JSON"
        memoria.caminho_memoria.write_text(conteudo_invalido, encoding="utf-8")

        with self.assertRaises(MemoriaCorrompidaErro):
            Memoria.carregar_ou_criar(self.diretorio)

        self.assertEqual(
            memoria.caminho_memoria.read_text(encoding="utf-8"), conteudo_invalido
        )

    def test_ausencia_posterior_da_memoria_e_erro(self) -> None:
        memoria = Memoria.carregar_ou_criar(self.diretorio)
        memoria.caminho_memoria.unlink()

        with self.assertRaises(MemoriaInconsistenteErro):
            Memoria.carregar_ou_criar(self.diretorio)

    def test_estado_vazio_no_esquema_atual_e_valido(self) -> None:
        memoria = Memoria.carregar_ou_criar(self.diretorio)
        memoria.estado["experiencias"] = []
        memoria.estado["conhecimentos"] = {}
        memoria.salvar()

        recarregada = Memoria.carregar_ou_criar(self.diretorio)

        self.assertEqual(recarregada.estado["experiencias"], [])
        self.assertEqual(recarregada.estado["conhecimentos"], {})
