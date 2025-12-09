from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import requests

from .config import GithubConfig
from .utils import horario_brasil


def _build_headers(cfg: GithubConfig) -> dict:
    return {
        "Authorization": f"token {cfg.token}",
        "Accept": "application/vnd.github.v3+json",
    }


def baixar_arquivo_github(cfg: GithubConfig, nome_arquivo: str) -> bool:
    """Baixa arquivo do GitHub se as configs estiverem completas."""
    if not cfg.token or not cfg.repository:
        logging.warning(
            "Configurações do GitHub incompletas. Não foi possível baixar %s.",
            nome_arquivo,
        )
        return False

    url = f"https://api.github.com/repos/{cfg.repository}/contents/{nome_arquivo}"
    response = requests.get(url, headers=_build_headers(cfg), timeout=30)

    if response.status_code != 200:
        logging.warning(
            "Arquivo %s não encontrado no GitHub (status %s).",
            nome_arquivo,
            response.status_code,
        )
        return False

    conteudo_base64 = response.json()["content"]
    conteudo = base64.b64decode(conteudo_base64).decode("utf-8")

    Path(nome_arquivo).write_text(conteudo, encoding="utf-8")
    logging.info("Arquivo %s baixado do GitHub.", nome_arquivo)
    return True


def fazer_upload_github(cfg: GithubConfig,
                        arquivo_local: str,
                        nome_remoto: str | None = None) -> bool:
    """Envia arquivo para o GitHub (cria ou atualiza)."""
    if not cfg.token or not cfg.repository:
        logging.warning(
            "Configurações do GitHub incompletas. Não foi possível fazer upload de %s.",
            arquivo_local,
        )
        return False

    nome_remoto = nome_remoto or arquivo_local
    path = Path(arquivo_local)
    if not path.exists():
        logging.warning("Arquivo local %s não existe.", path)
        return False

    conteudo = path.read_text(encoding="utf-8")
    conteudo_base64 = base64.b64encode(conteudo.encode("utf-8")).decode("utf-8")

    url = f"https://api.github.com/repos/{cfg.repository}/contents/{nome_remoto}"
    headers = _build_headers(cfg)

    # Verifica se existe
    r_get = requests.get(url, headers=headers, timeout=30)
    if r_get.status_code == 200:
        sha = r_get.json()["sha"]
        payload = {
            "message": f"Atualizar {nome_remoto} - {horario_brasil()}",
            "content": conteudo_base64,
            "sha": sha,
        }
    else:
        payload = {
            "message": f"Adicionar {nome_remoto} - {horario_brasil()}",
            "content": conteudo_base64,
        }

    r_put = requests.put(url, headers=headers, data=json.dumps(payload), timeout=30)
    ok = r_put.status_code in (200, 201)

    if ok:
        logging.info("Arquivo %s enviado para GitHub (%s).", nome_remoto, r_put.status_code)
    else:
        logging.error("Erro ao enviar %s para GitHub: %s", nome_remoto, r_put.text)

    return ok