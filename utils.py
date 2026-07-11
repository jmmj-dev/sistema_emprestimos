"""
utils.py
--------
Funções pequenas e reaproveitáveis que não pertencem a nenhuma camada
específica (não são regra de negócio, nem acesso a banco, nem tela).

Centralizar a formatação de moeda aqui evita ter a mesma lógica copiada
em main.py (CLI) e em app.py (web) — se um dia você quiser mudar o
formato, só mexe em um lugar.
"""


def formatar_moeda(valor: float) -> str:
    """
    Formata um número no padrão brasileiro de moeda: milhar com ponto,
    decimal com vírgula. Ex: 1234.5 -> "R$ 1.234,50"

    O Python formata números no padrão americano por padrão (1,234.50).
    O truque abaixo pega esse formato e troca os símbolos de lugar:
      1) formata como "1,234.50" (padrão do Python)
      2) troca "," por um marcador temporário "X"
      3) troca "." por ","
      4) troca "X" pelo "."
    Isso evita trocar tudo de uma vez e acabar virando bagunça.
    """
    texto = f"{valor:,.2f}"
    texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"
