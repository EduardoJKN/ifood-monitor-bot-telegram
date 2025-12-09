from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Union

from .config import AppConfig
from .github_integration import fazer_upload_github
from .utils import horario_brasil


def gerar_dashboard_html(
    historico: Union[Dict[str, dict], List[dict]],
    cfg: AppConfig,
) -> str:
    """
    Gera um dashboard HTML estático com resumo do histórico de produtos.

    Parâmetros
    ----------
    historico
        Pode ser:
        - um dicionário no formato antigo: { "Seção|Produto": { ...campos... } }
        - uma lista de registros (formato novo), cada um com:
          secao, nome, preco, descricao, status_anterior, status_atual, timestamp, desapareceu
    cfg : AppConfig
        Configurações da aplicação, incluindo local de saída do HTML.

    Retorna
    -------
    str
        Caminho do arquivo HTML gerado.
    """

    # 🔁 Compatibilidade: normaliza para dict {"secao|nome": registro}
    hist_dict: Dict[str, dict] = {}

    if isinstance(historico, dict):
        # Formato antigo já vinha como dict
        hist_dict = {k: v for k, v in historico.items()}
    elif isinstance(historico, list):
        # Formato novo: lista de registros
        for reg in historico:
            chave = f"{reg.get('secao', '')}|{reg.get('nome', '')}"
            hist_dict[chave] = reg
    else:
        logging.warning(
            "Formato inesperado de historico (%s); usando dict vazio.",
            type(historico),
        )

    historico = hist_dict


    # 1) Descobrir caminho de saída
    if getattr(cfg, "dashboard_output", None):
        arquivo_dashboard = Path(cfg.dashboard_output)
    else:
        base_dir = Path(__file__).resolve().parent.parent
        arquivo_dashboard = base_dir / "index.html"

    # 2) Preparar dados de resumo

    total_registros = len(historico)
    total_on = 0
    total_off = 0
    total_desaparecidos = 0

    produtos_por_secao: Dict[str, dict] = {}
    ultima_atualizacao = None

    for _chave, info in historico.items():
        secao = info.get("secao", "Sem seção") or "Sem seção"
        status_atual = str(info.get("status_atual", "DESCONHECIDO"))

        if secao not in produtos_por_secao:
            produtos_por_secao[secao] = {
                "total": 0,
                "on": 0,
                "off": 0,
                "desapareceu": 0,
            }

        produtos_por_secao[secao]["total"] += 1

        if status_atual.upper().startswith("ON"):
            total_on += 1
            produtos_por_secao[secao]["on"] += 1
        else:
            total_off += 1
            produtos_por_secao[secao]["off"] += 1

        if info.get("desapareceu", False):
            total_desaparecidos += 1
            produtos_por_secao[secao]["desapareceu"] += 1

        ts = info.get("timestamp")
        if ts:
            # Mantemos como string mesmo, só pra exibição
            ultima_atualizacao = ts

    if ultima_atualizacao is None:
        ultima_atualizacao = str(horario_brasil())

    # 3) Montar HTML

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8" />
    <title>Monitoramento de Produtos iFood - Demo</title>
    <style>
{_estilo_css()}
    </style>
</head>
<body>
    <header>
        <h1>Monitoramento de Produtos iFood - Demo</h1>
        <p>Última atualização: {ultima_atualizacao}</p>
    </header>

    <section class="cards-resumo">
        <div class="card total">
            <h2>Total de registros no histórico</h2>
            <p class="valor">{total_registros}</p>
        </div>
        <div class="card on">
            <h2>Produtos ON</h2>
            <p class="valor">{total_on}</p>
        </div>
        <div class="card off">
            <h2>Produtos OFF</h2>
            <p class="valor">{total_off}</p>
        </div>
        <div class="card desaparecidos">
            <h2>Produtos que já desapareceram alguma vez</h2>
            <p class="valor">{total_desaparecidos}</p>
        </div>
    </section>

    <section class="secao-tabela">
        <h2>Resumo por seção</h2>
        <table>
            <thead>
                <tr>
                    <th>Seção</th>
                    <th>Total de registros</th>
                    <th>ON</th>
                    <th>OFF</th>
                    <th>Desapareceu alguma vez</th>
                </tr>
            </thead>
            <tbody>
"""

    # Linhas da tabela por seção
    for secao, info_secao in sorted(produtos_por_secao.items(), key=lambda x: x[0]):
        html += f"""                <tr>
                    <td>{secao}</td>
                    <td>{info_secao['total']}</td>
                    <td>{info_secao['on']}</td>
                    <td>{info_secao['off']}</td>
                    <td>{info_secao['desapareceu']}</td>
                </tr>
"""

    html += """            </tbody>
        </table>
    </section>

    <footer>
        <p>Gerado automaticamente pelo monitor de produtos iFood (demo em CSV).</p>
    </footer>
</body>
</html>
"""

    
    # 4) Salvar
    arquivo_dashboard.parent.mkdir(parents=True, exist_ok=True)
    arquivo_dashboard.write_text(html, encoding="utf-8")

    logging.info("Dashboard HTML gerado em %s", arquivo_dashboard)

    # Upload opcional – se as configs de GitHub estiverem ok,
    # essa função só loga warning se não estiverem.
    fazer_upload_github(cfg.github, str(arquivo_dashboard), arquivo_dashboard.name)

    return str(arquivo_dashboard)

    import webbrowser

    # depois de salvar o arquivo e antes do return:
    webbrowser.open(arquivo_dashboard.as_uri())



def _estilo_css() -> str:
    """CSS básico para o dashboard HTML."""
    return """
    :root {
        --bg: #0f172a;
        --bg-card: #111827;
        --border: #1f2937;
        --text: #e5e7eb;
        --muted: #9ca3af;
        --on: #22c55e;
        --off: #ef4444;
        --warn: #f97316;
        --accent: #38bdf8;
    }

    * {
        box-sizing: border-box;
    }

    body {
        margin: 0;
        padding: 24px;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: radial-gradient(circle at top, #1f2937 0, #020617 55%, #000 100%);
        color: var(--text);
    }

    header {
        margin-bottom: 24px;
    }

    header h1 {
        margin: 0 0 4px 0;
        font-size: 24px;
        font-weight: 600;
    }

    header p {
        margin: 0;
        color: var(--muted);
        font-size: 14px;
    }

    .cards-resumo {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 16px;
        margin-bottom: 32px;
    }

    .card {
        padding: 16px 18px;
        border-radius: 16px;
        background: linear-gradient(145deg, #020617, #020617);
        border: 1px solid var(--border);
        box-shadow: 0 18px 50px rgba(0,0,0,0.6);
    }

    .card h2 {
        margin: 0 0 8px 0;
        font-size: 14px;
        font-weight: 500;
        color: var(--muted);
    }

    .card .valor {
        margin: 0;
        font-size: 26px;
        font-weight: 600;
    }

    .card.on .valor {
        color: var(--on);
    }

    .card.off .valor {
        color: var(--off);
    }

    .card.desaparecidos .valor {
        color: var(--warn);
    }

    .secao-tabela h2 {
        margin: 0 0 12px 0;
        font-size: 18px;
        font-weight: 600;
    }

    table {
        width: 100%;
        border-collapse: collapse;
        border-radius: 16px;
        overflow: hidden;
        background-color: rgba(15,23,42,0.8);
        border: 1px solid var(--border);
    }

    thead {
        background: linear-gradient(90deg, rgba(56,189,248,0.16), rgba(56,189,248,0.02));
    }

    th, td {
        padding: 10px 12px;
        font-size: 14px;
        text-align: left;
    }

    th {
        font-weight: 500;
        color: var(--muted);
        border-bottom: 1px solid var(--border);
    }

    tbody tr:nth-child(odd) {
        background-color: rgba(15,23,42,0.9);
    }

    tbody tr:nth-child(even) {
        background-color: rgba(17,24,39,0.9);
    }

    tbody tr:hover {
        background: radial-gradient(circle at left, rgba(56,189,248,0.18), transparent);
    }

    footer {
        margin-top: 24px;
        font-size: 12px;
        color: var(--muted);
    }

    @media (max-width: 900px) {
        .cards-resumo {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 600px) {
        .cards-resumo {
            grid-template-columns: 1fr;
        }

        body {
            padding: 16px;
        }
    }
    """