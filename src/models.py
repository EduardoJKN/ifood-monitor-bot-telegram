from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel


# Tipos possíveis de status no monitoramento
StatusType = Literal["ON", "OFF", "OFF (Desapareceu)"]


class Produto(BaseModel):
    """
    Produto do cardápio iFood (versão demo a partir do CSV).

    IMPORTANTE:
    - Aqui usamos os mesmos nomes de chave que o código usa nos dicts:
      secao, nome, preco, descricao, status.
    """

    secao: str
    nome: str
    preco: str
    descricao: Optional[str] = None
    status: StatusType


class ResultadoMonitoramento(BaseModel):
    """
    Resumo da execução do monitoramento.

    Pydantic converte automaticamente as listas de dicts em listas
    de Produto quando instanciarmos essa classe.
    """

    total_produtos: int
    produtos_off: List[Produto]
    produtos_desaparecidos: List[Produto]
    total_produtos_ativos: int
    timestamp: str