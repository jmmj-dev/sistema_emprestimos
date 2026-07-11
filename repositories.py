"""
repositories.py
----------------
"Repository" é um padrão de projeto: cada função aqui sabe conversar com o
banco de dados (SQL) e traduzir isso para os objetos do models.py, e
vice-versa. Nenhuma regra de negócio (cálculo de juros, validação) mora
aqui — só "salvar", "buscar", "atualizar".

Por que separar isso da lógica de negócio (services.py)? Porque se um dia
você trocar SQLite por PostgreSQL, só este arquivo muda. O resto do sistema
nem percebe a troca.
"""

from datetime import date
from typing import Optional

from database import get_connection
from models import Cliente, Emprestimo, Parcela, StatusEmprestimo, StatusParcela


# ---------- Clientes ----------

def salvar_cliente(cliente: Cliente) -> Cliente:
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO clientes (nome, cpf, telefone, email) VALUES (?, ?, ?, ?)",
        (cliente.nome, cliente.cpf, cliente.telefone, cliente.email),
    )
    conn.commit()
    cliente.id = cursor.lastrowid
    conn.close()
    return cliente


def listar_clientes() -> list[Cliente]:
    conn = get_connection()
    linhas = conn.execute("SELECT * FROM clientes ORDER BY nome").fetchall()
    conn.close()
    return [
        Cliente(id=l["id"], nome=l["nome"], cpf=l["cpf"],
                telefone=l["telefone"] or "", email=l["email"] or "")
        for l in linhas
    ]


def buscar_cliente_por_id(cliente_id: int) -> Optional[Cliente]:
    conn = get_connection()
    l = conn.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,)).fetchone()
    conn.close()
    if l is None:
        return None
    return Cliente(id=l["id"], nome=l["nome"], cpf=l["cpf"],
                    telefone=l["telefone"] or "", email=l["email"] or "")


def atualizar_cliente(cliente: Cliente) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE clientes SET nome = ?, cpf = ?, telefone = ?, email = ? WHERE id = ?",
        (cliente.nome, cliente.cpf, cliente.telefone, cliente.email, cliente.id),
    )
    conn.commit()
    conn.close()


def excluir_cliente(cliente_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM clientes WHERE id = ?", (cliente_id,))
    conn.commit()
    conn.close()


# ---------- Empréstimos ----------

def salvar_emprestimo(emprestimo: Emprestimo) -> Emprestimo:
    """
    Salva o empréstimo E todas as suas parcelas numa única transação.
    Se algo falhar no meio, nada é gravado (evita "empréstimo sem parcela").
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO emprestimos
               (cliente_id, valor_principal, taxa_juros_mensal,
                numero_parcelas, data_emprestimo, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (emprestimo.cliente_id, emprestimo.valor_principal,
             emprestimo.taxa_juros_mensal, emprestimo.numero_parcelas,
             emprestimo.data_emprestimo.isoformat(), emprestimo.status.value),
        )
        emprestimo.id = cursor.lastrowid

        for parcela in emprestimo.parcelas:
            parcela.emprestimo_id = emprestimo.id
            p_cursor = conn.execute(
                """INSERT INTO parcelas
                   (emprestimo_id, numero, valor, data_vencimento, status,
                    juros, amortizacao, saldo_devedor)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (parcela.emprestimo_id, parcela.numero, parcela.valor,
                 parcela.data_vencimento.isoformat(), parcela.status.value,
                 parcela.juros, parcela.amortizacao, parcela.saldo_devedor),
            )
            parcela.id = p_cursor.lastrowid

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    return emprestimo


def _linha_para_parcela(l) -> Parcela:
    return Parcela(
        id=l["id"],
        emprestimo_id=l["emprestimo_id"],
        numero=l["numero"],
        valor=l["valor"],
        data_vencimento=date.fromisoformat(l["data_vencimento"]),
        status=StatusParcela(l["status"]),
        data_pagamento=date.fromisoformat(l["data_pagamento"]) if l["data_pagamento"] else None,
        juros=l["juros"],
        amortizacao=l["amortizacao"],
        saldo_devedor=l["saldo_devedor"],
    )


def listar_parcelas_do_emprestimo(emprestimo_id: int) -> list[Parcela]:
    conn = get_connection()
    linhas = conn.execute(
        "SELECT * FROM parcelas WHERE emprestimo_id = ? ORDER BY numero",
        (emprestimo_id,),
    ).fetchall()
    conn.close()
    return [_linha_para_parcela(l) for l in linhas]


def listar_emprestimos(cliente_id: Optional[int] = None) -> list[Emprestimo]:
    conn = get_connection()
    if cliente_id is not None:
        linhas = conn.execute(
            "SELECT * FROM emprestimos WHERE cliente_id = ? ORDER BY data_emprestimo DESC",
            (cliente_id,),
        ).fetchall()
    else:
        linhas = conn.execute(
            "SELECT * FROM emprestimos ORDER BY data_emprestimo DESC"
        ).fetchall()
    conn.close()

    emprestimos = []
    for l in linhas:
        emp = Emprestimo(
            id=l["id"],
            cliente_id=l["cliente_id"],
            valor_principal=l["valor_principal"],
            taxa_juros_mensal=l["taxa_juros_mensal"],
            numero_parcelas=l["numero_parcelas"],
            data_emprestimo=date.fromisoformat(l["data_emprestimo"]),
            status=StatusEmprestimo(l["status"]),
        )
        emp.parcelas = listar_parcelas_do_emprestimo(emp.id)
        emprestimos.append(emp)
    return emprestimos


def atualizar_status_parcela(parcela_id: int, status: StatusParcela,
                              data_pagamento: Optional[date] = None) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE parcelas SET status = ?, data_pagamento = ? WHERE id = ?",
        (status.value, data_pagamento.isoformat() if data_pagamento else None, parcela_id),
    )
    conn.commit()
    conn.close()


def atualizar_status_emprestimo(emprestimo_id: int, status: StatusEmprestimo) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE emprestimos SET status = ? WHERE id = ?",
        (status.value, emprestimo_id),
    )
    conn.commit()
    conn.close()
