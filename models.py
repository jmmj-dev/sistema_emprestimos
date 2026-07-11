"""
models.py
---------
Aqui definimos "o que é" cada coisa no nosso sistema, sem nenhuma lógica de
banco de dados ou regra de negócio junto. Isso é proposital: separar "o que
os dados são" de "como eu salvo/calculo eles" deixa o código muito mais fácil
de entender e testar.

Usamos @dataclass, um recurso do Python que gera automaticamente o __init__,
__repr__ etc. para classes que são basicamente "sacos de dados".
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class StatusParcela(str, Enum):
    """
    Enum = um conjunto fixo de valores possíveis. Usar Enum em vez de string
    solta ("pendente", "pago" digitados à mão em vários lugares) evita erros
    de digitação e deixa claro quais são os únicos valores válidos.
    """
    PENDENTE = "pendente"
    PAGA = "paga"
    ATRASADA = "atrasada"


class StatusEmprestimo(str, Enum):
    ABERTO = "aberto"
    QUITADO = "quitado"
    CANCELADO = "cancelado"


@dataclass
class Cliente:
    nome: str
    cpf: str
    telefone: str = ""
    email: str = ""
    id: Optional[int] = None  # None até ser salvo no banco (o banco gera o id)


@dataclass
class Parcela:
    emprestimo_id: int
    numero: int              # 1ª parcela, 2ª parcela, etc.
    valor: float
    data_vencimento: date
    juros: float = 0.0           # parte da parcela que é juros sobre o saldo devedor
    amortizacao: float = 0.0     # parte da parcela que reduz o valor emprestado
    saldo_devedor: float = 0.0   # quanto ainda falta pagar de principal após esta parcela
    status: StatusParcela = StatusParcela.PENDENTE
    data_pagamento: Optional[date] = None
    id: Optional[int] = None


@dataclass
class Emprestimo:
    cliente_id: int
    valor_principal: float       # valor emprestado, sem juros
    taxa_juros_mensal: float     # ex: 0.05 significa 5% ao mês
    numero_parcelas: int
    data_emprestimo: date
    status: StatusEmprestimo = StatusEmprestimo.ABERTO
    id: Optional[int] = None
    parcelas: list = field(default_factory=list)  # lista de objetos Parcela
