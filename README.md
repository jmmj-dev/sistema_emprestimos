# Sistema de Empréstimos
<img width="1097" height="901" alt="tela app cobranca-python" src="https://github.com/user-attachments/assets/7fff0f7b-c5b7-44dc-85d5-a413b7f995b1" />


<!--
  Print de tela da interface web. Depois de tirar a captura, arraste a
  imagem para dentro deste README pela edição no site do GitHub (o GitHub
  gera o link sozinho) e troque a linha abaixo pelo link gerado. Até lá,
  esta linha fica invisível na página (é um comentário HTML).

  ![Extrato geral do sistema](URL_QUE_O_GITHUB_GERAR_AQUI)
-->

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

## Cobrança via WhatsApp

O sistema gera links prontos do WhatsApp (`wa.me`) — o mesmo tipo de link
que qualquer botão "fale conosco" de site usa — já com a mensagem
preenchida para cada cliente:

- **Lembrete amigável**: parcelas pendentes que vencem nos próximos 3 dias (ou hoje)
- **Cobrança**: parcelas já atrasadas, incluindo o valor atualizado com multa e juros de mora

Não há envio automático nem integração com API paga — você clica no link,
o WhatsApp abre (web ou app) com a mensagem pronta, e você confere e aperta
enviar. Isso evita custos, cadastro em plataformas de terceiros, e o risco
de automações de navegador fazerem o WhatsApp bloquear o número.

## Funcionalidades

- Cadastro, edição e exclusão de clientes (exclusão bloqueada se o cliente já tiver empréstimos)
- Criação de empréstimos com cálculo pela Tabela Price (juros compostos) e geração automática das parcelas e vencimentos
- Cancelamento de empréstimos (bloqueado se já houver parcela paga, para preservar o histórico financeiro)
- Detalhamento de cada parcela em juros, amortização e saldo devedor
- Marcação automática de parcelas atrasadas (comparando com a data atual)
- Cálculo de multa (2%, limite do CDC) e juros de mora (1% ao mês, proporcional aos dias) sobre parcelas atrasadas
- Lembretes e cobranças prontos para envio via WhatsApp (link direto, sem API paga)
- Registro de pagamento de parcelas
- Quitação automática do empréstimo quando todas as parcelas são pagas
- Busca e filtros: clientes por nome/CPF, empréstimos por status e por cliente
- Resumo financeiro por empréstimo (total pago, pendente, atrasado, juros do contrato)
- Extrato geral (dashboard) com totais consolidados de todos os empréstimos
- Valores formatados no padrão brasileiro (R$ 1.234,56)
- Interface web navegável, sem precisar digitar comandos

## Ideias para evoluir 

- [ ] Adicionar relatório de inadimplência exportável em CSV/PDF
- [ ] Autenticação simples (login) se for usar em rede local com mais de uma pessoa
- [ ] Permitir registrar pagamento pelo valor atualizado (com multa/juros de mora) em vez do valor original da parcela
- [ ] Deixar o número de dias de aviso prévio do lembrete configurável pela tela (hoje é fixo em 3 dias)
