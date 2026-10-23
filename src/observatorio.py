"""Servidor local do Observatório EVA.

O painel não inventa métricas: a cada pedido pelos dados, executa novamente os
relatórios determinísticos dos experimentos e entrega seus resultados ao navegador.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
import webbrowser
from datetime import UTC, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from experimentos.exp_001 import executar_experimento as executar_exp_001
from experimentos.exp_002 import executar_experimento as executar_exp_002


RAIZ_DO_PROJETO = Path(__file__).resolve().parents[1]
DIRETORIO_DO_OBSERVATORIO = RAIZ_DO_PROJETO / "observatorio"
NOME_DO_ARQUIVO_DE_DADOS = "dados_experimentos.json"


def _percentual(valor: float) -> str:
    return f"{valor:.0%}"


def gerar_dados() -> dict[str, object]:
    """Executa os experimentos e transforma seus resultados para o painel."""
    exp_001 = executar_exp_001()
    exp_002 = executar_exp_002()

    return {
        "gerado_em": datetime.now(UTC).isoformat(),
        "experimentos": {
            "exp001": {
                "id": exp_001["experimento"],
                "titulo": "Generalização em situações inéditas",
                "pergunta": (
                    "Depois de observar alguns objetos, a EVA consegue prever "
                    "combinações de massa e força que nunca encontrou?"
                ),
                "metricas": [
                    ["EVA", _percentual(exp_001["acuracia_eva"]), "bom"],
                    [
                        "Baseline de memorização",
                        _percentual(exp_001["acuracia_baseline"]),
                        "alerta",
                    ],
                    ["Casos inéditos", str(exp_001["amostras_de_avaliacao"]), ""],
                ],
                "barras": [
                    ["EVA", exp_001["acuracia_eva"]],
                    ["Memorizador", exp_001["acuracia_baseline"]],
                ],
                "colunas": [
                    "Massa",
                    "Força",
                    "Resultado real",
                    "Previsão EVA",
                    "Memorizador",
                ],
                "linhas": [
                    [
                        caso["massa"],
                        caso["forca"],
                        caso["resultado_real"],
                        caso["previsao_eva"],
                        caso["previsao_baseline"],
                    ]
                    for caso in exp_001["avaliacao"]
                ],
                "limitacao": (
                    "A relação força/massa foi uma escolha de projeto. Este "
                    "resultado mostra generalização neste ambiente, não "
                    "inteligência geral."
                ),
                "proximo": "Testar retenção quando novas tarefas aparecem.",
            },
            "exp002": {
                "id": exp_002["experimento"],
                "titulo": "Adaptação quando o ambiente muda",
                "pergunta": (
                    "Depois de aprender uma relação, a EVA revisa suas "
                    "previsões quando a regra muda sem aviso?"
                ),
                "metricas": [
                    ["Antes da mudança", _percentual(exp_002["acuracia_inicial"]), "bom"],
                    [
                        "Logo após a mudança",
                        _percentual(
                            exp_002["acuracia_apos_mudanca_antes_de_novas_experiencias"]
                        ),
                        "alerta",
                    ],
                    [
                        "Após adaptação",
                        _percentual(exp_002["acuracia_apos_adaptacao"]),
                        "bom",
                    ],
                ],
                "barras": [
                    ["Antes", exp_002["acuracia_inicial"]],
                    [
                        "Sem evidência nova",
                        exp_002["acuracia_apos_mudanca_antes_de_novas_experiencias"],
                    ],
                    ["Após adaptação", exp_002["acuracia_apos_adaptacao"]],
                ],
                "colunas": [
                    "Massa",
                    "Força",
                    "Resultado real",
                    "Modelo adaptativo",
                    "Modelo congelado",
                ],
                "linhas": [
                    [
                        caso["massa"],
                        caso["forca"],
                        caso["resultado_real"],
                        caso["previsao_adaptativa"],
                        caso["previsao_congelada"],
                    ]
                    for caso in exp_002["avaliacao_apos_mudanca"]
                ],
                "limitacao": (
                    "A adaptação usa uma janela de experiências recentes. Ela "
                    "ainda pode descartar evidências úteis de condições antigas."
                ),
                "proximo": "Separar memória de longo prazo, contexto atual e detecção de mudança.",
            },
        },
    }


def atualizar_dados(caminho: Path | None = None) -> Path:
    """Atualiza o JSON do painel por substituição atômica."""
    caminho = caminho or DIRETORIO_DO_OBSERVATORIO / NOME_DO_ARQUIVO_DE_DADOS
    caminho.parent.mkdir(parents=True, exist_ok=True)
    descritor, temporario = tempfile.mkstemp(
        prefix=f".{caminho.name}.", suffix=".tmp", dir=caminho.parent
    )
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            json.dump(gerar_dados(), arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
        os.replace(temporario, caminho)
    finally:
        if os.path.exists(temporario):
            os.unlink(temporario)
    return caminho


class ManipuladorDoObservatorio(SimpleHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802 - método exigido pela biblioteca padrão
        if urlsplit(self.path).path == f"/{NOME_DO_ARQUIVO_DE_DADOS}":
            atualizar_dados(Path(self.directory) / NOME_DO_ARQUIVO_DE_DADOS)
        super().do_GET()


def iniciar_servidor(porta: int, abrir_navegador: bool) -> None:
    atualizar_dados()
    manipulador = lambda *args, **kwargs: ManipuladorDoObservatorio(
        *args, directory=str(DIRETORIO_DO_OBSERVATORIO), **kwargs
    )
    servidor = ThreadingHTTPServer(("127.0.0.1", porta), manipulador)
    url = f"http://127.0.0.1:{porta}"
    print(f"Observatório EVA disponível em {url}")
    print("Pressione Ctrl+C para encerrar o servidor.")
    if abrir_navegador:
        webbrowser.open(url)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nObservatório EVA encerrado.")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description="Abre o Observatório EVA local.")
    argumentos.add_argument("--porta", type=int, default=8000)
    argumentos.add_argument("--sem-abrir", action="store_true")
    opcoes = argumentos.parse_args()
    iniciar_servidor(opcoes.porta, abrir_navegador=not opcoes.sem_abrir)
