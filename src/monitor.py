from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from .config import AppConfig, load_config
from .dashboard_html import gerar_dashboard_html
from .github_integration import baixar_arquivo_github, fazer_upload_github
from .models import Produto, ResultadoMonitoramento
from .relatorio_excel import gerar_relatorio_excel
from .state import (
    atualizar_historico,
    carregar_estado_anterior,
    carregar_historico,
    salvar_estado_atual,
)
from .telegram_client import enviar_alerta_telegram
from .utils import horario_brasil, setup_logging


def carregar_produtos_csv(cfg: AppConfig) -> list[dict]:
    """Carrega os produtos a partir do CSV configurado."""
    logger = logging.getLogger(__name__)

    try:
        # Caminho do CSV configurado
        df = pd.read_csv(cfg.data_path)

        # Normaliza nomes de colunas para minúsculo e sem espaços extras
        df.columns = [c.strip().lower() for c in df.columns]

        # Mapeia nomes antigos para o padrão novo
        if "produto" in df.columns and "nome" not in df.columns:
            df = df.rename(columns={"produto": "nome"})

        if "seção" in df.columns and "secao" not in df.columns:
            df = df.rename(columns={"seção": "secao"})

        colunas_esperadas = {"secao", "nome", "preco", "descricao", "status"}
        faltando = colunas_esperadas - set(df.columns)

        if faltando:
            raise ValueError(f"Colunas obrigatórias ausentes no CSV: {faltando}")

        produtos: list[dict] = []
        for _, row in df.iterrows():
            produtos.append(
                {
                    "secao": row["secao"],
                    "nome": row["nome"],
                    "preco": row["preco"],
                    "descricao": row.get("descricao", ""),
                    "status": row["status"],
                }
            )

        logger.info("CSV carregado com %d produtos.", len(produtos))
        return produtos

    except Exception as e:
        logger.exception("Erro ao ler CSV de produtos: %s", e)
        raise


def comparar_com_estado_anterior(
    produtos_atual: list[dict],
    estado_anterior: dict,
    timestamp_atual: str,
):
    """
    Compara o estado atual (lista de dicts) com o estado anterior (dict carregado do JSON).

    - produtos_atual: lista de dicts com chaves: secao, nome, preco, descricao, status
    - estado_anterior: dict no formato { "Seção|Produto": { ...info... } }
    """

    # Mapa do estado atual: "Secao|Nome" -> dict do produto
    atuais = {
        f"{p['secao']}|{p['nome']}": p
        for p in produtos_atual
    }

    produtos_off: list[dict] = []
    produtos_desaparecidos: list[dict] = []

    # 1) Produtos OFF no estado atual (status != "ON")
    for chave, p in atuais.items():
        if str(p.get("status", "")).upper() != "ON":
            produtos_off.append(
                {
                    "secao": p["secao"],
                    "nome": p["nome"],
                    "preco": p.get("preco", ""),
                    "descricao": p.get("descricao", ""),
                    "status": p.get("status", "DESCONHECIDO"),
                }
            )

    # 2) Produtos que existiam antes e não existem mais no CSV atual → "desaparecidos"
    for chave, info in estado_anterior.items():
        if chave not in atuais:
            secao, nome = chave.split("|", 1)
            produtos_desaparecidos.append(
                {
                    "secao": secao,
                    "nome": nome,
                    "preco": info.get("Preço", "N/A"),
                    "descricao": info.get("Descrição", ""),
                    "status": "OFF (Desapareceu)",
                    "ultima_verificacao": info.get("Última verificação", timestamp_atual),
                }
            )

    return produtos_off, produtos_desaparecidos


def monitorar(cfg: AppConfig) -> ResultadoMonitoramento:
    """Pipeline completo de monitoramento a partir do CSV."""
    inicio = horario_brasil()
    logging.info("Iniciando monitoramento (CSV) em %s", inicio)
    timestamp_atual = inicio.strftime("%Y-%m-%d %H:%M:%S")

    # Tenta baixar estado / histórico antigos do GitHub
    baixar_arquivo_github(cfg.github, cfg.estado_path)
    baixar_arquivo_github(cfg.github, cfg.historico_path)

    estado_anterior = carregar_estado_anterior(cfg.estado_path)

    produtos_atual = carregar_produtos_csv(cfg)

    produtos_off, produtos_desaparecidos = comparar_com_estado_anterior(
        produtos_atual,
        estado_anterior,
        timestamp_atual,
    )

    if produtos_desaparecidos:
        logging.warning(
            "%s produtos desapareceram desde a última execução.",
            len(produtos_desaparecidos),
        )
    else:
        logging.info("Nenhum produto desapareceu em relação ao estado anterior.")

    # Salvar novo estado
    salvar_estado_atual(cfg.estado_path, produtos_atual)
    fazer_upload_github(cfg.github, cfg.estado_path, cfg.estado_path)

    # Atualizar histórico
    historico = carregar_historico(cfg.historico_path)
    historico = atualizar_historico(
        cfg.historico_path, historico, produtos_atual, produtos_desaparecidos
    )
    fazer_upload_github(cfg.github, cfg.historico_path, cfg.historico_path)

    # Dashboard + Excel
    gerar_dashboard_html(historico, cfg)
    gerar_relatorio_excel(produtos_atual, produtos_desaparecidos, cfg.excel_output)
    fazer_upload_github(cfg.github, cfg.excel_output, cfg.excel_output)

    total_produtos = len(produtos_atual)
    total_off = len(produtos_off) + len(produtos_desaparecidos)
    total_ativos = total_produtos - total_off

    # Mensagem
    if total_off > 0:
        msg = f"Total de {total_off} produtos com problemas (OFF ou desaparecidos)."
    else:
        msg = "✅ Todos os produtos estão ON e nenhum desapareceu!"

    enviar_alerta_telegram(
        cfg,
        msg,
        produtos_off,
        produtos_desaparecidos,
        total_ativos,
        produtos_atual + produtos_desaparecidos,
    )

    resultado = ResultadoMonitoramento(
        total_produtos=total_produtos,
        produtos_off=produtos_off,
        produtos_desaparecidos=produtos_desaparecidos,
        total_produtos_ativos=total_ativos,
        timestamp=timestamp_atual,
    )

    logging.info("Monitoramento concluído: %s", resultado.model_dump())
    return resultado


def main() -> None:
    cfg = load_config()
    setup_logging(cfg.log_path)

    parser = argparse.ArgumentParser(
        description="Monitoramento de produtos iFood (demo com CSV)."
    )
    parser.add_argument(
        "--modo",
        choices=["monitorar"],
        default="monitorar",
        help="Ação a executar (por enquanto só 'monitorar').",
    )

    args = parser.parse_args()

    if args.modo == "monitorar":
        monitorar(cfg)


if __name__ == "__main__":
    main()