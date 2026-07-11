# Sistema de Empréstimos

Sistema local para gerenciar clientes, empréstimos, parcelas, juros e
vencimentos. Tem **duas interfaces** que reaproveitam exatamente a mesma
lógica de negócio: uma no terminal e outra na web.

## Como rodar — versão terminal (CLI)

```bash
python main.py
```

Não precisa instalar nada — usa só a biblioteca padrão do Python (`sqlite3`,
`datetime`, `dataclasses`, `enum`).

## Como rodar — versão web

```bash
pip install flask
python app.py
```

Depois acesse **http://127.0.0.1:5000** no navegador.

Em ambos os casos, o banco de dados é criado automaticamente em
`data/emprestimos.db` na primeira execução, e é o **mesmo arquivo** —
você pode cadastrar um cliente pelo terminal e ver ele aparecer na web,
e vice-versa.

## Arquitetura

O projeto é dividido em camadas, cada uma com uma responsabilidade única:

```
main.py / app.py   → Interfaces com o usuário (terminal e web)
services.py          → Regras de negócio (cálculo de juros, validações)
repositories.py      → Acesso ao banco de dados (SQL)
models.py            → Estruturas de dados (Cliente, Emprestimo, Parcela)
database.py           → Conexão e criação das tabelas
```

Essa separação (conhecida como arquitetura em camadas) é o que permitiu
adicionar a versão web **sem alterar uma linha sequer** de `database.py`,
`models.py`, `repositories.py` ou `services.py`. O `app.py` só chama as
mesmas funções que o `main.py` já chamava — a diferença é só como o
resultado é mostrado (HTML em vez de texto no terminal).

Se um dia você quiser trocar SQLite por PostgreSQL, só mexe em
`repositories.py`. O resto do sistema nem percebe a troca.

## Cálculo de juros: Tabela Price

Usa o Sistema Francês de Amortização (Tabela Price) — o mesmo método usado
por bancos em financiamentos e empréstimos reais. A parcela tem valor fixo,
mas a composição entre juros e amortização muda a cada mês:

```
PMT = PV × i / (1 − (1 + i)⁻ⁿ)
```
- `PV` = valor principal emprestado
- `i` = taxa de juros mensal (ex: 0.05 para 5%)
- `n` = número de parcelas

A cada parcela:
```
juros       = saldo_devedor_atual × i
amortização = valor_da_parcela − juros
novo_saldo  = saldo_devedor_atual − amortização
```

No início do contrato, a maior parte da parcela é juros. Perto do fim, a
maior parte é amortização — mesmo o valor da parcela nunca mudando. O
sistema guarda esse detalhamento (juros, amortização e saldo devedor) por
parcela, exatamente como um extrato bancário real mostra.

## Funcionalidades

- Cadastro de clientes
- Criação de empréstimos com cálculo pela Tabela Price (juros compostos) e geração automática das parcelas e vencimentos
- Detalhamento de cada parcela em juros, amortização e saldo devedor
- Marcação automática de parcelas atrasadas (comparando com a data atual)
- Registro de pagamento de parcelas
- Quitação automática do empréstimo quando todas as parcelas são pagas
- Resumo financeiro por empréstimo (total pago, pendente, atrasado, juros do contrato)
- Extrato geral (dashboard) com totais consolidados de todos os empréstimos
- Interface web navegável, sem precisar digitar comandos

## Ideias para evoluir (ótimo para continuar aprendendo)

- [ ] Adicionar testes automatizados com `pytest`
- [ ] Adicionar relatório de inadimplência exportável em CSV/PDF
- [ ] Multa e juros de mora sobre parcelas atrasadas
- [ ] Autenticação simples (login) se for usar em rede local com mais de uma pessoa
- [ ] Edição/exclusão de clientes e empréstimos
- [ ] Busca e filtros na listagem de empréstimos (por status, por cliente)
