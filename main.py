"""
main.py
-------
Ponto de entrada do sistema. É o único arquivo que "conversa" com o usuário
via terminal (input/print). Toda a lógica pesada fica em services.py — aqui
só montamos o menu e mostramos os resultados formatados.

Para rodar: python main.py
"""

from datetime import date, datetime

import repositories as repo
import services
from database import inicializar_banco
from models import StatusParcela


def ler_float(mensagem: str) -> float:
    while True:
        try:
            return float(input(mensagem).replace(",", "."))
        except ValueError:
            print("  Valor inválido. Digite um número (ex: 1500.50).")


def ler_int(mensagem: str) -> int:
    while True:
        try:
            return int(input(mensagem))
        except ValueError:
            print("  Valor inválido. Digite um número inteiro.")


def ler_data(mensagem: str) -> date:
    texto = input(mensagem).strip()
    if not texto:
        return date.today()
    try:
        return datetime.strptime(texto, "%d/%m/%Y").date()
    except ValueError:
        print("  Data inválida, usando hoje.")
        return date.today()


# ---------- Telas ----------

def menu_cadastrar_cliente():
    print("\n--- Cadastrar Cliente ---")
    nome = input("Nome: ")
    cpf = input("CPF: ")
    telefone = input("Telefone (opcional): ")
    email = input("Email (opcional): ")
    try:
        cliente = services.cadastrar_cliente(nome, cpf, telefone, email)
        print(f"  Cliente cadastrado com sucesso! ID: {cliente.id}")
    except ValueError as e:
        print(f"  Erro: {e}")


def menu_listar_clientes():
    print("\n--- Clientes cadastrados ---")
    clientes = repo.listar_clientes()
    if not clientes:
        print("  Nenhum cliente cadastrado ainda.")
        return
    for c in clientes:
        print(f"  [{c.id}] {c.nome} - CPF: {c.cpf} - Tel: {c.telefone}")


def menu_criar_emprestimo():
    print("\n--- Novo Empréstimo ---")
    menu_listar_clientes()
    cliente_id = ler_int("ID do cliente: ")
    valor = ler_float("Valor do empréstimo (R$): ")
    taxa = ler_float("Taxa de juros mensal (ex: 0.05 para 5%): ")
    parcelas = ler_int("Número de parcelas: ")
    data_txt = ler_data("Data do empréstimo (dd/mm/aaaa, ENTER para hoje): ")
    try:
        emp = services.criar_emprestimo(cliente_id, valor, taxa, parcelas, data_txt)
        print(f"\n  Empréstimo criado! ID: {emp.id} (Tabela Price)")
        print(f"  Valor de cada parcela: R$ {emp.parcelas[0].valor:.2f}")
        print(f"  {'Parcela':<10}{'Vencimento':<14}{'Juros':<12}{'Amortização':<14}{'Saldo devedor':<14}")
        for p in emp.parcelas:
            print(f"  {p.numero:<10}{p.data_vencimento.strftime('%d/%m/%Y'):<14}"
                  f"R$ {p.juros:<9.2f}R$ {p.amortizacao:<11.2f}R$ {p.saldo_devedor:<11.2f}")
    except ValueError as e:
        print(f"  Erro: {e}")


def menu_listar_emprestimos():
    print("\n--- Empréstimos ---")
    emprestimos = repo.listar_emprestimos()
    if not emprestimos:
        print("  Nenhum empréstimo cadastrado ainda.")
        return
    for emp in emprestimos:
        cliente = repo.buscar_cliente_por_id(emp.cliente_id)
        resumo = services.resumo_emprestimo(emp)
        print(f"\n  [{emp.id}] Cliente: {cliente.nome} | Status: {emp.status.value}")
        print(f"      Principal: R$ {emp.valor_principal:.2f} | Taxa: {emp.taxa_juros_mensal*100:.1f}%/mês | "
              f"{emp.numero_parcelas}x")
        print(f"      Total do contrato: R$ {resumo['valor_total_contrato']:.2f} | "
              f"Pago: R$ {resumo['total_pago']:.2f} | Pendente: R$ {resumo['total_pendente']:.2f} | "
              f"Atrasado: R$ {resumo['total_atrasado']:.2f}")


def menu_ver_parcelas():
    print("\n--- Ver parcelas de um empréstimo ---")
    menu_listar_emprestimos()
    emprestimo_id = ler_int("\nID do empréstimo: ")
    parcelas = repo.listar_parcelas_do_emprestimo(emprestimo_id)
    if not parcelas:
        print("  Empréstimo não encontrado ou sem parcelas.")
        return
    icones = {StatusParcela.PENDENTE: "🕓", StatusParcela.PAGA: "✅", StatusParcela.ATRASADA: "⚠️ "}
    for p in parcelas:
        pago_em = f" (pago em {p.data_pagamento.strftime('%d/%m/%Y')})" if p.data_pagamento else ""
        print(f"  {icones.get(p.status, '')} [{p.id}] Parcela {p.numero}: R$ {p.valor:.2f} "
              f"(juros R$ {p.juros:.2f} + amort. R$ {p.amortizacao:.2f}) - "
              f"vence {p.data_vencimento.strftime('%d/%m/%Y')} - status: {p.status.value}{pago_em}")


def menu_registrar_pagamento():
    print("\n--- Registrar Pagamento de Parcela ---")
    parcela_id = ler_int("ID da parcela: ")
    try:
        services.registrar_pagamento_parcela(parcela_id)
        print("  Pagamento registrado com sucesso!")
    except Exception as e:
        print(f"  Erro: {e}")


def exibir_menu():
    print("\n" + "=" * 40)
    print("  SISTEMA DE EMPRÉSTIMOS")
    print("=" * 40)
    print("  1. Cadastrar cliente")
    print("  2. Listar clientes")
    print("  3. Criar empréstimo")
    print("  4. Listar empréstimos")
    print("  5. Ver parcelas de um empréstimo")
    print("  6. Registrar pagamento de parcela")
    print("  0. Sair")


def main():
    inicializar_banco()
    atualizadas = services.atualizar_parcelas_atrasadas()
    if atualizadas:
        print(f"Aviso: {atualizadas} parcela(s) passaram para o status ATRASADA.")

    acoes = {
        "1": menu_cadastrar_cliente,
        "2": menu_listar_clientes,
        "3": menu_criar_emprestimo,
        "4": menu_listar_emprestimos,
        "5": menu_ver_parcelas,
        "6": menu_registrar_pagamento,
    }

    while True:
        exibir_menu()
        opcao = input("Escolha uma opção: ").strip()
        if opcao == "0":
            print("Até mais!")
            break
        acao = acoes.get(opcao)
        if acao:
            acao()
        else:
            print("  Opção inválida.")


if __name__ == "__main__":
    main()
