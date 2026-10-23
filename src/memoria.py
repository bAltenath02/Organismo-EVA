"""Memória persistente da EVA.

Este módulo cuida de continuidade e integridade dos registros. Ele não tenta
interpretar automaticamente eventos como aprendizagem ou conhecimento geral.
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


VERSAO_ESQUEMA = 1
RAIZ_DO_PROJETO = Path(__file__).resolve().parents[1]
DIRETORIO_DE_DADOS = RAIZ_DO_PROJETO / "data"


class ErroDeMemoria(RuntimeError):
    """Erro-base para problemas no estado persistente da EVA."""


class MemoriaCorrompidaErro(ErroDeMemoria):
    """O arquivo existe, mas não contém JSON que possa ser lido."""


class MemoriaInconsistenteErro(ErroDeMemoria):
    """Os arquivos existem, mas não descrevem um único estado válido."""


def agora_iso() -> str:
    return datetime.now(UTC).isoformat()


def _ler_json(caminho: Path) -> dict[str, Any]:
    try:
        with caminho.open("r", encoding="utf-8") as arquivo:
            conteudo = json.load(arquivo)
    except json.JSONDecodeError as erro:
        raise MemoriaCorrompidaErro(
            f"Não foi possível ler '{caminho}'. O arquivo não foi alterado."
        ) from erro
    except OSError as erro:
        raise ErroDeMemoria(f"Não foi possível abrir '{caminho}'.") from erro

    if not isinstance(conteudo, dict):
        raise MemoriaInconsistenteErro(
            f"'{caminho}' deve conter um objeto JSON, não {type(conteudo).__name__}."
        )
    return conteudo


def _escrever_json_atomicamente(caminho: Path, conteudo: dict[str, Any]) -> None:
    """Grava e substitui um arquivo apenas depois de terminar a escrita."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    descritor, temporario = tempfile.mkstemp(
        prefix=f".{caminho.name}.", suffix=".tmp", dir=caminho.parent
    )
    try:
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    except OSError as erro:
        raise ErroDeMemoria(f"Não foi possível gravar '{caminho}'.") from erro
    finally:
        if os.path.exists(temporario):
            os.unlink(temporario)


@dataclass
class Memoria:
    """Estado carregado da EVA e operações explícitas para modificá-lo."""

    diretorio: Path
    identidade: dict[str, Any]
    estado: dict[str, Any]
    primeira_inicializacao: bool = False

    @property
    def caminho_identidade(self) -> Path:
        return self.diretorio / "identidade_eva.json"

    @property
    def caminho_memoria(self) -> Path:
        return self.diretorio / "memoria_eva.json"

    @classmethod
    def carregar_ou_criar(cls, diretorio: Path | None = None) -> "Memoria":
        diretorio = Path(diretorio) if diretorio else DIRETORIO_DE_DADOS
        identidade_path = diretorio / "identidade_eva.json"
        memoria_path = diretorio / "memoria_eva.json"
        existe_identidade = identidade_path.exists()
        existe_memoria = memoria_path.exists()

        if not existe_identidade and not existe_memoria:
            return cls._criar_primeira_memoria(diretorio)

        if existe_identidade != existe_memoria:
            ausente = memoria_path if existe_identidade else identidade_path
            raise MemoriaInconsistenteErro(
                "O estado persistente está incompleto: "
                f"'{ausente}' está ausente. Nenhum arquivo foi substituído."
            )

        identidade = _ler_json(identidade_path)
        estado = _ler_json(memoria_path)
        memoria = cls(diretorio=diretorio, identidade=identidade, estado=estado)
        memoria._validar_estado()
        return memoria

    @classmethod
    def _criar_primeira_memoria(cls, diretorio: Path) -> "Memoria":
        identidade = {
            "versao_esquema": VERSAO_ESQUEMA,
            "organismo_id": str(uuid.uuid4()),
            "criada_em": agora_iso(),
        }
        estado = {
            "versao_esquema": VERSAO_ESQUEMA,
            "organismo_id": identidade["organismo_id"],
            "experiencias": [
                {
                    "tipo": "nascimento",
                    "ocorreu_em": agora_iso(),
                    "detalhes": {"origem": "primeira_inicializacao"},
                }
            ],
            "conhecimentos": {},
        }
        memoria = cls(
            diretorio=diretorio,
            identidade=identidade,
            estado=estado,
            primeira_inicializacao=True,
        )
        _escrever_json_atomicamente(memoria.caminho_identidade, identidade)
        _escrever_json_atomicamente(memoria.caminho_memoria, estado)
        return memoria

    def _validar_estado(self) -> None:
        campos_identidade = {"versao_esquema", "organismo_id", "criada_em"}
        campos_memoria = {
            "versao_esquema",
            "organismo_id",
            "experiencias",
            "conhecimentos",
        }
        if not campos_identidade.issubset(self.identidade):
            raise MemoriaInconsistenteErro("O arquivo de identidade não segue o esquema atual.")
        if not campos_memoria.issubset(self.estado):
            raise MemoriaInconsistenteErro("O arquivo de memória não segue o esquema atual.")
        if self.identidade["versao_esquema"] != VERSAO_ESQUEMA:
            raise MemoriaInconsistenteErro("A versão da identidade não é suportada.")
        if self.estado["versao_esquema"] != VERSAO_ESQUEMA:
            raise MemoriaInconsistenteErro("A versão da memória não é suportada.")
        if self.identidade["organismo_id"] != self.estado["organismo_id"]:
            raise MemoriaInconsistenteErro("Identidade e memória pertencem a organismos diferentes.")
        if not isinstance(self.estado["experiencias"], list):
            raise MemoriaInconsistenteErro("'experiencias' deve ser uma lista.")
        if not isinstance(self.estado["conhecimentos"], dict):
            raise MemoriaInconsistenteErro("'conhecimentos' deve ser um objeto.")

    def salvar(self) -> None:
        self._validar_estado()
        _escrever_json_atomicamente(self.caminho_memoria, self.estado)

    def registrar_evento(self, tipo: str, detalhes: dict[str, Any] | None = None) -> None:
        if not tipo.strip():
            raise ValueError("O tipo do evento não pode estar vazio.")
        self.estado["experiencias"].append(
            {
                "tipo": tipo,
                "ocorreu_em": agora_iso(),
                "detalhes": detalhes or {},
            }
        )
        self.salvar()

    def aprender(self, chave: str, valor: Any) -> None:
        """Registra um dado observado sem alegar que ele já foi generalizado."""
        if not chave.strip():
            raise ValueError("A chave do conhecimento não pode estar vazia.")
        self.estado["conhecimentos"][chave] = {
            "valor": valor,
            "atualizado_em": agora_iso(),
        }
        self.registrar_evento("registro_de_observacao", {"chave": chave})
