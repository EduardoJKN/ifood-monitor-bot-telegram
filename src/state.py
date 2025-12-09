from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .utils import horario_brasil


# -------------------------------
# ESTADO ATUAL (estado_produtos.json)
# -------------------------------

def carregar_estado_anterior(path: str | Path) -> dict[str, dict]:
    """
    Carrega o estado anterior dos produtos a partir de um JSON.

    Formato esperado:
    {
      "Seção|Produto": {
        "Seção": "...",
        "Produto": "...",
        "Preço": "...",
        "Descrição": "...",
        "Status": "...",
        "Última verificação": "..."
      },
      ...
    }
    """
    p = Path(path)

    if not p.exists():
        logging.warning("Nenhum estado anterior encontrado. Esta parece ser a primeira execução.")
        return {}

    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            logging.warning(
                "Estado anterior não está no formato esperado (dict). "
                "Um novo estado vazio será criado."
            )
            return {}

        logging.info("Estado anterior carregado com %d produtos", len(data))
        return data

    except Exception as e:
        logging.exception("Erro ao carregar estado anterior: %s", e)
        return {}


def salvar_estado_atual(path: str | Path, produtos_atual: list[dict]) -> None:
    """
    Salva o estado atual dos produtos em JSON, a partir da lista de dicts
    (cada dict com chaves: secao, nome, preco, descricao, status).
    """
    p = Path(path)

    try:
        novo_estado: dict[str, dict[str, Any]] = {}
        ts = str(horario_brasil())

        for prod in produtos_atual:
            chave = f"{prod.get('secao', '')}|{prod.get('nome', '')}"

            novo_estado[chave] = {
                "Seção": prod.get("secao", ""),
                "Produto": prod.get("nome", ""),
                "Preço": prod.get("preco", ""),
                "Descrição": prod.get("descricao", ""),
                "Status": prod.get("status", ""),
                "Última verificação": ts,
            }

        with p.open("w", encoding="utf-8") as f:
            json.dump(novo_estado, f, ensure_ascii=False, indent=2)

        logging.info(
            "Estado atual salvo com %d produtos em %s",
            len(novo_estado),
            p,
        )

    except Exception as e:
        logging.exception("Erro ao salvar estado atual: %s", e)


# -------------------------------
# HISTÓRICO (historico_status.json)
# -------------------------------

def carregar_historico(path: str | Path) -> list[dict]:
    """
    Carrega o histórico de produtos.

    Formato novo desejado: uma LISTA de dicts:
    [
      {
        "timestamp": "...",
        "secao": "...",
        "nome": "...",
        "preco": "...",
        "descricao": "...",
        "status": "...",
        "tipo": "ATUAL" ou "DESAPARECIDO"
      },
      ...
    ]

    Também trata formatos antigos (dict) e converte para lista.
    """
    p = Path(path)

    if not p.exists():
        logging.warning("Nenhum histórico encontrado. Um novo será criado.")
        return []

    try:
        with p.open(encoding="utf-8") as f:
            data = json.load(f)

        # Caso já esteja no formato novo (lista)
        if isinstance(data, list):
            logging.info("Histórico carregado com %d registros.", len(data))
            return data

        # Caso antigo: dict
        if isinstance(data, dict):
            # Se tiver chave "registros", usa isso
            if "registros" in data and isinstance(data["registros"], list):
                registros = data["registros"]
            else:
                # Caso seja um dict de chave -> registro
                registros = list(data.values())

            logging.info(
                "Histórico carregado em formato dict e convertido para lista (%d registros).",
                len(registros),
            )
            return registros

        logging.warning(
            "Histórico não está em um formato reconhecido. Um novo será criado."
        )
        return []

    except Exception as e:
        logging.exception("Erro ao carregar histórico: %s", e)
        return []


def salvar_historico(path: str | Path, historico: list[dict]) -> None:
    """
    Salva o histórico sempre como uma LISTA de registros.
    """
    p = Path(path)

    try:
        with p.open("w", encoding="utf-8") as f:
            json.dump(historico, f, ensure_ascii=False, indent=2)

        logging.info(
            "Histórico salvo com %d registros em %s",
            len(historico),
            p,
        )

    except Exception as e:
        logging.exception("Erro ao salvar histórico: %s", e)


def atualizar_historico(
    path: str | Path,
    historico: list[dict] | dict,
    produtos_atual: list[dict],
    produtos_desaparecidos: list[dict],
) -> list[dict]:
    """
    Atualiza o histórico com:
      - todos os produtos do estado atual
      - os produtos que desapareceram

    Garante que o histórico será uma lista, mesmo que venha em formato antigo (dict).
    """
    ts = str(horario_brasil())

    # 🔒 Garantia de que historico é uma lista
    if isinstance(historico, dict):
        logging.warning(
            "Histórico lido como dict. Convertendo valores para lista."
        )
        historico_lista: list[dict] = list(historico.values())
    elif isinstance(historico, list):
        historico_lista = historico
    else:
        logging.warning(
            "Tipo inesperado de histórico (%s). Recriando como lista vazia.",
            type(historico).__name__,
        )
        historico_lista = []

    # Registros do estado atual
    for p in produtos_atual:
        historico_lista.append(
            {
                "timestamp": ts,
                "secao": p.get("secao", ""),
                "nome": p.get("nome", ""),
                "preco": p.get("preco", ""),
                "descricao": p.get("descricao", ""),
                "status": p.get("status", ""),
                "tipo": "ATUAL",
            }
        )

    # Registros de produtos desaparecidos
    for p in produtos_desaparecidos:
        historico_lista.append(
            {
                "timestamp": ts,
                "secao": p.get("secao", ""),
                "nome": p.get("nome", ""),
                "preco": p.get("preco", ""),
                "descricao": p.get("descricao", ""),
                "status": p.get("status", "OFF (Desapareceu)"),
                "tipo": "DESAPARECIDO",
            }
        )

    salvar_historico(path, historico_lista)

    logging.info(
        "Histórico atualizado com %d registros em %s",
        len(historico_lista),
        path,
    )

    return historico_lista