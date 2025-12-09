from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path


def horario_brasil() -> dt.datetime:
    """Retorna o horário atual no fuso horário de Brasília (UTC-3)."""
    return dt.datetime.utcnow() - dt.timedelta(hours=3)


def setup_logging(log_path: str) -> None:
    """Configura logging padrão para arquivo + console."""
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )