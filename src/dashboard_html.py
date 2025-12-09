from __future__ import annotations

import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from .config import AppConfig
from .github_integration import fazer_upload_github
from .utils import horario_brasil


def _norm_status(value: Any) -> str:
    """Normaliza o status para comparação (string maiúscula)."""
    return str(value or "").strip().upper()


def gerar_dashboard_html(historico: Iterable[dict], cfg: AppConfig) -> str:
    """
    Gera o dashboard HTML a partir do histórico (lista de dicts) e,
    se configurado, faz upload para o GitHub.
    """

    # Garante que temos uma lista
    historico = list(historico or [])

    # Caminho do arquivo HTML de saída
    if hasattr(cfg, "dashboard_output"):
        arquivo_dashboard = Path(cfg.dashboard_output)
    else:
        base_dir = Path(__file__).resolve().parent.parent
        arquivo_dashboard = base_dir / "index.html"

    if not historico:
        ultima_atualizacao = str(horario_brasil())
        total_registros = total_on = total_off = total_desapareceram = 0
        on_por_secao: dict[str, int] = {}
        off_por_secao: dict[str, int] = {}
        desapareceu_por_secao: dict[str, int] = {}
    else:
        # -----------------------------
        # Agregações
        # -----------------------------
        total_registros = len(historico)

        # Última execução (maior timestamp)
        try:
            ultimo_ts = max(str(r.get("timestamp", "")) for r in historico)
        except ValueError:
            ultimo_ts = ""

        ultima_atualizacao = ultimo_ts or str(horario_brasil())

        # Registros da última execução, apenas tipo "ATUAL"
        registros_ultimo = [
            r
            for r in historico
            if str(r.get("timestamp", "")) == ultimo_ts
            and _norm_status(r.get("tipo")) == "ATUAL"
        ]

        # Se por algum motivo não achar, cai pro histórico todo
        if not registros_ultimo:
            registros_ultimo = [
                r for r in historico if _norm_status(r.get("tipo")) == "ATUAL"
            ]

        total_on = 0
        total_off = 0

        on_por_secao: dict[str, int] = defaultdict(int)
        off_por_secao: dict[str, int] = defaultdict(int)

        # Agregação por seção na última execução
        for r in registros_ultimo:
            secao = r.get("secao") or r.get("Seção") or "Desconhecida"

            status = (
                _norm_status(r.get("status"))
                or _norm_status(r.get("Status"))
            )

            if status == "ON":
                total_on += 1
                on_por_secao[secao] += 1
            else:
                total_off += 1
                off_por_secao[secao] += 1

        # Produtos que já desapareceram alguma vez (qualquer execução)
        desaparecidos_uma_vez: set[tuple[str, str]] = set()
        for r in historico:
            tipo = _norm_status(r.get("tipo"))
            if "DESAPARECIDO" in tipo or "DESAPARECEU" in tipo:
                secao = r.get("secao") or r.get("Seção") or ""
                nome = r.get("nome") or r.get("Produto") or ""
                desaparecidos_uma_vez.add((secao, nome))

        total_desapareceram = len(desaparecidos_uma_vez)

        desapareceu_por_secao: dict[str, int] = defaultdict(int)
        for secao, _ in desaparecidos_uma_vez:
            if secao:
                desapareceu_por_secao[secao] += 1

    # -----------------------------
    # Monta tabela de "Resumo por seção"
    # -----------------------------
    secoes = sorted(
        set(on_por_secao.keys())
        | set(off_por_secao.keys())
        | set(desapareceu_por_secao.keys())
    )

    linhas_tabela = ""
    for secao in secoes:
        total_secao = on_por_secao.get(secao, 0) + off_por_secao.get(secao, 0)
        linhas_tabela += f"""
            <tr>
                <td>{secao}</td>
                <td>{total_secao}</td>
                <td>{on_por_secao.get(secao, 0)}</td>
                <td>{off_por_secao.get(secao, 0)}</td>
                <td>{desapareceu_por_secao.get(secao, 0)}</td>
            </tr>
        """

    # -----------------------------
    # HTML (layout dark bonitinho)
    # -----------------------------
    html = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8" />
    <title>Monitoramento de Produtos iFood - Demo</title>
    <style>
        :root {{
            --bg: #050816;
            --bg-card: #0b1020;
            --bg-card-alt: #111827;
            --accent: #22c55e;
            --accent-red: #ef4444;
            --accent-yellow: #eab308;
            --text-main: #f9fafb;
            --text-muted: #9ca3af;
            --border-subtle: #1f2937;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            padding: 0;
            font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            background: radial-gradient(circle at top, #111827 0, #020617 40%, #000 80%);
            color: var(--text-main);
        }}

        .page {{
            max-width: 1200px;
            margin: 32px auto;
            padding: 0 16px 32px;
        }}

        h1 {{
            font-size: 28px;
            margin: 0 0 4px;
        }}

        .subtitle {{
            font-size: 14px;
            color: var(--text-muted);
        }}

        .cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin: 24px 0;
        }}

        .card {{
            background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-alt) 100%);
            border-radius: 14px;
            padding: 16px 18px;
            border: 1px solid var(--border-subtle);
            box-shadow: 0 18px 35px rgba(15,23,42,0.7);
        }}

        .card-label {{
            font-size: 13px;
            color: var(--text-muted);
            margin-bottom: 4px;
        }}

        .card-value {{
            font-size: 26px;
            font-weight: 600;
        }}

        .card-value.on {{
            color: var(--accent);
        }}

        .card-value.off {{
            color: var(--accent-red);
        }}

        .card-value.warn {{
            color: var(--accent-yellow);
        }}

        .table-wrapper {{
            margin-top: 24px;
            background: rgba(15,23,42,0.9);
            border-radius: 14px;
            border: 1px solid var(--border-subtle);
            overflow: hidden;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
        }}

        thead {{
            background: rgba(15,23,42,0.95);
        }}

        th, td {{
            padding: 10px 14px;
            text-align: left;
            font-size: 13px;
        }}

        th {{
            font-weight: 500;
            color: var(--text-muted);
            border-bottom: 1px solid #1f2937;
        }}

        tbody tr:nth-child(even) {{
            background: rgba(15,23,42,0.85);
        }}

        tbody tr:nth-child(odd) {{
            background: rgba(15,23,42,0.7);
        }}

        tbody td:nth-child(3) {{
            color: var(--accent);
        }}

        tbody td:nth-child(4) {{
            color: var(--accent-red);
        }}

        .footer {{
            margin-top: 16px;
            font-size: 12px;
            color: var(--text-muted);
        }}
    </style>
</head>
<body>
    <div class="page">
        <header>
            <h1>Monitoramento de Produtos iFood - Demo</h1>
            <div class="subtitle">
                Última atualização: {ultima_atualizacao}
            </div>
        </header>

        <section class="cards">
            <div class="card">
                <div class="card-label">Total de registros no histórico</div>
                <div class="card-value warn">{total_registros}</div>
            </div>
            <div class="card">
                <div class="card-label">Produtos ON (última execução)</div>
                <div class="card-value on">{total_on}</div>
            </div>
            <div class="card">
                <div class="card-label">Produtos OFF (última execução)</div>
                <div class="card-value off">{total_off}</div>
            </div>
            <div class="card">
                <div class="card-label">Produtos que já desapareceram alguma vez</div>
                <div class="card-value warn">{total_desapareceram}</div>
            </div>
        </section>

        <section class="table-wrapper">
            <table>
                <thead>
                    <tr>
                        <th>Seção</th>
                        <th>Total de registros (última execução)</th>
                        <th>ON</th>
                        <th>OFF</th>
                        <th>Desapareceu alguma vez</th>
                    </tr>
                </thead>
                <tbody>
                    {linhas_tabela}
                </tbody>
            </table>
        </section>

        <div class="footer">
            Dashboard gerado automaticamente pelo script
            <code>python -m src.monitor --modo monitorar</code>.
        </div>
    </div>
</body>
</html>
"""

    try:
        arquivo_dashboard.parent.mkdir(parents=True, exist_ok=True)
        with arquivo_dashboard.open("w", encoding="utf-8") as f:
            f.write(html)

        logging.info("Dashboard HTML gerado em %s", arquivo_dashboard)

        # Upload para GitHub (se configurado)
        fazer_upload_github(cfg.github, str(arquivo_dashboard), arquivo_dashboard.name)

    except Exception as e:
        logging.exception("Erro ao gerar dashboard HTML: %s", e)

    return str(arquivo_dashboard)
