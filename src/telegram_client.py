from __future__ import annotations

import logging
from typing import Any, Dict, List

import requests

from .config import AppConfig
from .utils import horario_brasil


logger = logging.getLogger(__name__)


def _montar_resumo_status_por_secao(produtos: List[Dict[str, Any]]) -> str:

    from collections import defaultdict

    stats = defaultdict(lambda: {"on": 0, "off": 0, "desap": 0})

    for p in produtos:
        secao = str(p.get("secao", "(sem seção)")).strip()
        status_raw = str(p.get("status", "")).upper()

        if status_raw == "ON":
            stats[secao]["on"] += 1
        else:
            stats[secao]["off"] += 1
            if "DESAPARECEU" in status_raw:
                stats[secao]["desap"] += 1

    if not stats:
        return "(sem dados de seção)"

    linhas = ["📊 Status por Seção:"]
    for secao in sorted(stats.keys()):
        s = stats[secao]
        linhas.append(
            f"- {secao}: 🟢 {s['on']} ON | 🔴 {s['off']} OFF (inclui {s['desap']} desaparecidos)"
        )

    return "\n".join(linhas)


def enviar_alerta_telegram(
    cfg: AppConfig,
    mensagem_resumo: str,
    produtos_off: List[Dict[str, Any]],
    produtos_desaparecidos: List[Dict[str, Any]],
    total_ativos: int,
    produtos_completos: List[Dict[str, Any]],
) -> None:

    token = cfg.telegram.token if cfg.telegram else ""
    chat_id = cfg.telegram.chat_id if cfg.telegram else ""

    if not token or not chat_id:
        logger.warning(
            "TELEGRAM_TOKEN ou TELEGRAM_CHAT_ID não configurados. Pulando envio."
        )
        return

    base_url = f"https://api.telegram.org/bot{token}/sendMessage"

    agora = horario_brasil()
    data_str = agora.strftime("%d/%m/%Y %H:%M:%S")

    total_off = len(produtos_off) + len(produtos_desaparecidos)

    # ===== Cabeçalho =====
    linhas_msg: List[str] = []
    linhas_msg.append("🚨 ALERTA: Monitoramento de Produtos iFood (Demo CSV) 🚨\n")
    linhas_msg.append(f"Data/Hora: {data_str}\n")
    linhas_msg.append(f"✅ Produtos ativos no cardápio (ON): {total_ativos}\n")

    # ===== Lista de produtos OFF / desaparecidos =====
    if total_off > 0:
        linhas_msg.append(
            f"⚠️ {total_off} produtos com problemas (OFF ou desaparecidos):"
        )
        destaque = produtos_off + produtos_desaparecidos
        max_listar = 10

        for p in destaque[:max_listar]:
            secao = p.get("secao", "(sem seção)")
            nome = p.get("nome", "(sem nome)")
            preco = p.get("preco", "N/A")
            linhas_msg.append(f"- {secao} – {nome} – Preço: {preco}")

        if len(destaque) > max_listar:
            linhas_msg.append(f"... e mais {len(destaque) - max_listar} produtos\n")
        else:
            linhas_msg.append("")
    else:
        linhas_msg.append("✅ Nenhum produto OFF ou desaparecido.\n")

    # ===== Status por seção =====
    linhas_msg.append(_montar_resumo_status_por_secao(produtos_completos))
    linhas_msg.append("")

    # ===== Rodapé =====
    linhas_msg.append(
        f"Total de {total_off} produtos com problemas (OFF ou desaparecidos). "
        "Verifique o relatório completo."
    )

    # Link opcional do dashboard (HTML local / GitHub Pages)
    if getattr(cfg, "dashboard_output", None):
        linhas_msg.append("\n🔗 Dashboard HTML disponível no repositório.")

    mensagem_final = "\n".join(linhas_msg)

    payload = {
        "chat_id": chat_id,
        "text": mensagem_final,
        "parse_mode": "Markdown",
    }

    # ===== Envio com retries =====
    import time
    import requests

    tentativas = 3
    for tentativa in range(1, tentativas + 1):
        try:
            resp = requests.post(base_url, json=payload, timeout=20)
            if resp.status_code == 200:
                logger.info("Alerta enviado ao Telegram (tentativa %d).", tentativa)
                break
            else:
                logger.error(
                    "Erro ao enviar alerta para Telegram (tentativa %d): %s",
                    tentativa,
                    resp.text,
                )
        except requests.exceptions.ReadTimeout:
            logger.warning(
                "Timeout ao enviar alerta para Telegram (tentativa %d).",
                tentativa,
            )
        except Exception as e:
            logger.exception(
                "Erro ao chamar API do Telegram na tentativa %d: %s",
                tentativa,
                e,
            )

        if tentativa < tentativas:
            time.sleep(5)