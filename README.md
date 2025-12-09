# Monitoramento de Produtos iFood (Demo CSV)

Script de monitoramento de produtos de um restaurante no iFood, adaptado para usar
um **arquivo CSV de demonstração** em vez de acessar o site real (mantendo a lógica de
alertas e histórico do projeto original que eu usei no trabalho).

O objetivo é **acompanhar quais produtos estão ON/OFF** por seção, gerar relatórios e
enviar um **alerta detalhado no Telegram** para o gerente.

---

## 🧠 Visão geral

- Lê um arquivo `produtos_ifood_demo.csv` com as colunas:
  - `Secao`
  - `Produto`
  - `Preço`
  - `Descrição`
  - `Status` (ON / OFF)
- Compara com o estado anterior salvo em `estado_produtos.json`
- Marca:
  - produtos que ficaram **OFF**
  - produtos que **sumiram** do cardápio
- Atualiza o `historico_status.json` com cada execução
- Gera:
  - `index.html` com um resumo em HTML
  - `produtos_ifood.xlsx` com um relatório detalhado
- Envia um **alerta formatado no Telegram** (modo demo) com:
  - total de produtos ON
  - lista de produtos OFF
  - contagem de ON/OFF por seção

---

## 🏗 Arquitetura do projeto

```text
Cumbuca_IFood_T1-Sem Selenium/
├─ dados/
│  └─ produtos_ifood_demo.csv        # Fonte de dados de demonstração
├─ src/
│  ├─ config.py                      # Carrega configurações e paths
│  ├─ monitor.py                     # Pipeline principal (entrypoint)
│  ├─ models.py                      # Modelos Pydantic (Produto, ResultadoMonitoramento)
│  ├─ state.py                       # Leitura/gravação de estado e histórico (JSON)
│  ├─ dashboard_html.py              # Geração do dashboard HTML
│  ├─ relatorio_excel.py             # Geração do relatório Excel
│  ├─ telegram_client.py             # Envio de alerta formatado para o Telegram
│  ├─ github_integration.py          # Funções auxiliares para GitHub (opcional)
│  └─ utils.py                       # Logging, horário Brasil, helpers gerais
├─ estado_produtos.json              # Estado atual (gerado em runtime)
├─ historico_status.json             # Histórico de execuções (gerado em runtime)
├─ index.html                        # Dashboard HTML (gerado em runtime)
├─ produtos_ifood.xlsx               # Relatório Excel (gerado em runtime)
├─ requirements.txt                  # Dependências Python
└─ README.md