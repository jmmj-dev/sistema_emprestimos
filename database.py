"""
database.py
-----------
Responsável só por duas coisas: abrir conexão com o banco SQLite e garantir
que as tabelas existam. Nenhuma regra de negócio deve morar aqui.

SQLite guarda tudo em um único arquivo (.db) na sua máquina, ideal para um
projeto que "roda só localmente" como você pediu — nada de servidor de banco
de dados separado.
"""

import sqlite3
from pathlib import Path

# Path(__file__).parent = pasta onde este arquivo está.
# Assim o banco sempre fica dentro do projeto, não importa de onde você
# executa o comando python.
DB_DIR = Path(__file__).parent / "data"
DB_PATH = DB_DIR / "emprestimos.db"


def get_connection() -> sqlite3.Connection:
    """
    Abre (ou cria) o arquivo do banco e devolve uma conexão.

    row_factory = sqlite3.Row permite acessar colunas pelo nome
    (linha["nome"]) em vez de só pelo índice (linha[0]), o que deixa o
    código muito mais legível.
    """
    DB_DIR.mkdir(exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # PRAGMA foreign_keys = ON: sem isso, o SQLite ignora as regras de
    # integridade referencial (ex: não deixar apagar um cliente que tem
    # empréstimo vinculado) mesmo que estejam declaradas na tabela.
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def inicializar_banco() -> None:
    """Cria as tabelas caso ainda não existam. Seguro rodar várias vezes."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cpf TEXT NOT NULL UNIQUE,
            telefone TEXT,
            email TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS emprestimos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            valor_principal REAL NOT NULL,
            taxa_juros_mensal REAL NOT NULL,
            numero_parcelas INTEGER NOT NULL,
            data_emprestimo TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'aberto',
            FOREIGN KEY (cliente_id) REFERENCES clientes (id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parcelas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emprestimo_id INTEGER NOT NULL,
            numero INTEGER NOT NULL,
            valor REAL NOT NULL,
            data_vencimento TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pendente',
            data_pagamento TEXT,
            juros REAL NOT NULL DEFAULT 0,
            amortizacao REAL NOT NULL DEFAULT 0,
            saldo_devedor REAL NOT NULL DEFAULT 0,
            FOREIGN KEY (emprestimo_id) REFERENCES emprestimos (id)
        )
    """)

    # Migração: se o banco já existia de uma versão anterior (antes da
    # Tabela Price), as colunas novas podem não existir ainda. ALTER TABLE
    # ADD COLUMN é seguro rodar mesmo em bancos já em uso, sem perder dados.
    colunas_existentes = {linha["name"] for linha in cursor.execute("PRAGMA table_info(parcelas)")}
    for coluna in ("juros", "amortizacao", "saldo_devedor"):
        if coluna not in colunas_existentes:
            cursor.execute(f"ALTER TABLE parcelas ADD COLUMN {coluna} REAL NOT NULL DEFAULT 0")

    conn.commit()
    conn.close()
