"""
main.py
-------
Ponto de entrada do sistema. É o único arquivo que "conversa" com o usuário
via terminal (input/print). Toda a lógica pesada fica em services.py — aqui
só montamos o menu e mostramos os resultados formatados.

Para rodar: python main.py
"""

from datetime import date, datetime
import webbrowser

import repositories as repo
import services
from database import inicializar_banco
from models import StatusParcela
from utils import formatar_moeda


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


def menu_editar_cliente():
    print("\n--- Editar Cliente ---")
    menu_listar_clientes()
    cliente_id = ler_int("ID do cliente a editar: ")
    cliente = repo.buscar_cliente_por_id(cliente_id)
    if cliente is None:
        print("  Cliente não encontrado.")
        return
    print(f"  Deixe em branco para manter o valor atual entre parênteses.")
    nome = input(f"Nome ({cliente.nome}): ").strip() or cliente.nome
    cpf = input(f"CPF ({cliente.cpf}): ").strip() or cliente.cpf
    telefone = input(f"Telefone ({cliente.telefone}): ").strip() or cliente.telefone
    email = input(f"Email ({cliente.email}): ").strip() or cliente.email
    try:
        services.atualizar_cliente(cliente_id, nome, cpf, telefone, email)
        print("  Cliente atualizado com sucesso!")
    except ValueError as e:
        print(f"  Erro: {e}")


def menu_excluir_cliente():
    print("\n--- Excluir Cliente ---")
    menu_listar_clientes()
    cliente_id = ler_int("ID do cliente a excluir: ")
    confirmacao = input("Tem certeza? Isso não pode ser desfeito (s/N): ").strip().lower()
    if confirmacao != "s":
        print("  Cancelado.")
        return
    try:
        services.excluir_cliente(cliente_id)
        print("  Cliente excluído com sucesso!")
    except ValueError as e:
        print(f"  Erro: {e}")


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
        print(f"  Valor de cada parcela: {formatar_moeda(emp.parcelas[0].valor)}")
        print(f"  {'Parcela':<10}{'Vencimento':<14}{'Juros':<16}{'Amortização':<18}{'Saldo devedor':<16}")
        for p in emp.parcelas:
            print(f"  {p.numero:<10}{p.data_vencimento.strftime('%d/%m/%Y'):<14}"
                  f"{formatar_moeda(p.juros):<16}{formatar_moeda(p.amortizacao):<18}{formatar_moeda(p.saldo_devedor):<16}")
    except ValueError as e:
        print(f"  Erro: {e}")


def _imprimir_emprestimos(emprestimos):
    if not emprestimos:
        print("  Nenhum empréstimo encontrado.")
        return
    for emp in emprestimos:
        cliente = repo.buscar_cliente_por_id(emp.cliente_id)
        resumo = services.resumo_emprestimo(emp)
        print(f"\n  [{emp.id}] Cliente: {cliente.nome} | Status: {emp.status.value}")
        print(f"      Principal: {formatar_moeda(emp.valor_principal)} | Taxa: {emp.taxa_juros_mensal*100:.1f}%/mês | "
              f"{emp.numero_parcelas}x")
        print(f"      Total do contrato: {formatar_moeda(resumo['valor_total_contrato'])} | "
              f"Pago: {formatar_moeda(resumo['total_pago'])} | Pendente: {formatar_moeda(resumo['total_pendente'])} | "
              f"Atrasado: {formatar_moeda(resumo['total_atrasado'])}")


def menu_listar_emprestimos():
    print("\n--- Empréstimos ---")
    print("  Filtrar por status? [1] Todos [2] Aberto [3] Quitado [4] Cancelado")
    escolha = input("  Opção (ENTER para todos): ").strip()
    status_map = {"2": "aberto", "3": "quitado", "4": "cancelado"}
    status = status_map.get(escolha, "")
    _imprimir_emprestimos(services.filtrar_emprestimos(status=status))


def menu_cancelar_emprestimo():
    print("\n--- Cancelar Empréstimo ---")
    _imprimir_emprestimos(repo.listar_emprestimos())
    emprestimo_id = ler_int("\nID do empréstimo a cancelar: ")
    confirmacao = input("Tem certeza? Isso não pode ser desfeito (s/N): ").strip().lower()
    if confirmacao != "s":
        print("  Cancelado.")
        return
    try:
        services.cancelar_emprestimo(emprestimo_id)
        print("  Empréstimo cancelado com sucesso!")
    except ValueError as e:
        print(f"  Erro: {e}")


def menu_ver_parcelas():
    print("\n--- Ver parcelas de um empréstimo ---")
    _imprimir_emprestimos(repo.listar_emprestimos())
    emprestimo_id = ler_int("\nID do empréstimo: ")
    parcelas = repo.listar_parcelas_do_emprestimo(emprestimo_id)
    if not parcelas:
        print("  Empréstimo não encontrado ou sem parcelas.")
        return
    icones = {StatusParcela.PENDENTE: "🕓", StatusParcela.PAGA: "✅", StatusParcela.ATRASADA: "⚠️ "}
    for p in parcelas:
        pago_em = f" (pago em {p.data_pagamento.strftime('%d/%m/%Y')})" if p.data_pagamento else ""
        print(f"  {icones.get(p.status, '')} [{p.id}] Parcela {p.numero}: {formatar_moeda(p.valor)} "
              f"(juros {formatar_moeda(p.juros)} + amort. {formatar_moeda(p.amortizacao)}) - "
              f"vence {p.data_vencimento.strftime('%d/%m/%Y')} - status: {p.status.value}{pago_em}")
        if p.status == StatusParcela.ATRASADA:
            encargos = services.calcular_encargos_atraso(p)
            print(f"        {encargos['dias_atraso']} dia(s) de atraso - multa {formatar_moeda(encargos['multa'])} "
                  f"+ juros de mora {formatar_moeda(encargos['juros_mora'])} = "
                  f"valor atualizado {formatar_moeda(encargos['valor_atualizado'])}")


def menu_registrar_pagamento():
    print("\n--- Registrar Pagamento de Parcela ---")
    parcela_id = ler_int("ID da parcela: ")
    try:
        services.registrar_pagamento_parcela(parcela_id)
        print("  Pagamento registrado com sucesso!")
    except Exception as e:
        print(f"  Erro: {e}")


def menu_cobrancas():
    print("\n--- Cobranças (WhatsApp) ---")
    cobrancas = services.listar_cobrancas()
    if not cobrancas:
        print("  Nenhuma cobrança pendente no momento — todas as parcelas estão em dia.")
        return

    for i, c in enumerate(cobrancas, start=1):
        rotulo = "ATRASADO" if c["tipo"] == "atraso" else "lembrete"
        tel = c["cliente"].telefone or "(sem telefone cadastrado)"
        print(f"  [{i}] {rotulo:<9} {c['cliente'].nome} - {tel} - "
              f"parcela {c['parcela'].numero}/{c['emprestimo'].numero_parcelas} - "
              f"vence {c['parcela'].data_vencimento.strftime('%d/%m/%Y')}")

    escolha = input("\nDigite o número para abrir o WhatsApp com a mensagem pronta (ENTER para voltar): ").strip()
    if not escolha.isdigit():
        return
    indice = int(escolha) - 1
    if not (0 <= indice < len(cobrancas)):
        print("  Opção inválida.")
        return

    c = cobrancas[indice]
    print(f"\n  Mensagem:\n  {c['mensagem']}\n")
    if not c["link_whatsapp"]:
        print("  Este cliente não tem telefone cadastrado — edite o cadastro dele para adicionar um.")
        return
    webbrowser.open(c["link_whatsapp"])
    print("  Abrindo o WhatsApp no navegador...")


def exibir_menu():
    print("\n" + "=" * 40)
    print("  SISTEMA DE EMPRÉSTIMOS")
    print("=" * 40)
    print("  1. Cadastrar cliente")
    print("  2. Listar clientes")
    print("  3. Editar cliente")
    print("  4. Excluir cliente")
    print("  5. Criar empréstimo")
    print("  6. Listar empréstimos")
    print("  7. Cancelar empréstimo")
    print("  8. Ver parcelas de um empréstimo")
    print("  9. Registrar pagamento de parcela")
    print("  10. Cobranças (WhatsApp)")
    print("  0. Sair")


def main():
    inicializar_banco()
    atualizadas = services.atualizar_parcelas_atrasadas()
    if atualizadas:
        print(f"Aviso: {atualizadas} parcela(s) passaram para o status ATRASADA.")

    acoes = {
        "1": menu_cadastrar_cliente,
        "2": menu_listar_clientes,
        "3": menu_editar_cliente,
        "4": menu_excluir_cliente,
        "5": menu_criar_emprestimo,
        "6": menu_listar_emprestimos,
        "7": menu_cancelar_emprestimo,
        "8": menu_ver_parcelas,
        "9": menu_registrar_pagamento,
        "10": menu_cobrancas,
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
