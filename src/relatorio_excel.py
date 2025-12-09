from __future__ import annotations
import pandas as pd
from pathlib import Path

def gerar_relatorio_excel(produtos_atual, produtos_desaparecidos, output_path):
    # sheet 1 – todos os produtos
    df1 = pd.DataFrame([
        {
            "Seção": p["secao"],
            "Nome": p["nome"],
            "Preço": p.get("preco", ""),
            "Status": p.get("status", ""),
        }
        for p in produtos_atual
    ])

    # sheet 2 – desaparecidos
    df2 = pd.DataFrame([
        {
            "Seção": p["secao"],
            "Nome": p["nome"],
            "Preço": p.get("preco", ""),
            "Status": "DESAPARECIDO",
        }
        for p in produtos_desaparecidos
    ])

    output = Path(output_path)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df1.to_excel(writer, sheet_name="Produtos Atual", index=False)
        df2.to_excel(writer, sheet_name="Produtos Desaparecidos", index=False)
