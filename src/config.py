from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GithubConfig:
    token: str
    repository: str
    actor: str


@dataclass
class TelegramConfig:
    token: str
    chat_id: str


@dataclass
class AppConfig:
    project_root: Path

    # Caminho do CSV de entrada (demo)
    data_path: Path

    # Arquivos de estado / histórico em JSON
    estado_path: Path
    historico_path: Path

    # Saídas
    dashboard_output: Path
    excel_output: Path
    log_path: Path

    # Integrações
    github: GithubConfig
    telegram: TelegramConfig


def load_config() -> AppConfig:
    """
    Monta a configuração padrão do projeto, usando:
    - caminhos relativos à raiz do repo
    - variáveis de ambiente (quando existirem)
    - e defaults amigáveis para rodar localmente
    """
    # raiz do projeto = pasta que contém `src/`
    project_root = Path(__file__).resolve().parent.parent

    # pasta de dados (onde está o produtos_ifood_demo.csv)
    data_dir = project_root / "dados"
    data_dir.mkdir(parents=True, exist_ok=True)

    data_path = data_dir / "produtos_ifood_demo.csv"

    # arquivos de estado / histórico
    estado_path = project_root / "estado_produtos.json"
    historico_path = project_root / "historico_status.json"

    # saídas
    dashboard_output = project_root / "index.html"
    excel_output = project_root / "produtos_ifood.xlsx"
    log_path = project_root / "monitoramento_log.txt"

    # === GitHub ===
    github_token = os.getenv("GITHUB_TOKEN", "")
    github_repo = os.getenv("GITHUB_REPOSITORY", "")
    github_actor = os.getenv("GITHUB_ACTOR", "")

    github_cfg = GithubConfig(
        token=github_token,
        repository=github_repo,
        actor=github_actor,
    )

    # === Telegram ===
    # Usa env se existir, SENÃO cai no token/chat_id que você usava antes
    telegram_token = os.getenv(
        "TELEGRAM_TOKEN",
        "7538392371:AAH3-eZcq7wrf3Uycv9zPq1PjlSvWfLtYlc",  # teu token original
    )
    telegram_chat_id = os.getenv(
        "TELEGRAM_CHAT_ID",
        "-1002593932783",  # teu chat id original
    )

    telegram_cfg = TelegramConfig(
        token=telegram_token,
        chat_id=telegram_chat_id,
    )

    return AppConfig(
        project_root=project_root,
        data_path=data_path,
        estado_path=estado_path,
        historico_path=historico_path,
        dashboard_output=dashboard_output,
        excel_output=excel_output,
        log_path=log_path,
        github=github_cfg,
        telegram=telegram_cfg,
    )
