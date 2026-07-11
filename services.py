"""
services.py
-----------
Aqui mora o "cérebro" do sistema: as regras de negócio. É a camada mais
importante para você estudar, porque é onde a matemática financeira e as
decisões (o que é atraso? como calcular a parcela?) acontecem.

Nenhuma linha de SQL aparece aqui — quem fala com o banco é o
repositories.py. services.py só usa as funções que ele expõe.
"""

from datetime import date
from calendar import monthrange
import re
from urllib.parse import quote

import repositories as repo
from models import Cliente, Emprestimo, Parcela, StatusEmprestimo, StatusParcela
from utils import formatar_moeda


# ---------- Clientes ----------

def cadastrar_cliente(nome: str, cpf: str, telefone: str = "", email: str = "") -> Cliente:
    if not nome.strip():
        raise ValueError("Nome não pode ser vazio.")
    if not cpf.strip():
        raise ValueError("CPF não pode ser vazio.")
    cliente = Cliente(nome=nome.strip(), cpf=cpf.strip(), telefone=telefone, email=email)
    return repo.salvar_cliente(cliente)


def atualizar_cliente(cliente_id: int, nome: str, cpf: str,
                       telefone: str = "", email: str = "") -> Cliente:
    if not nome.strip():
        raise ValueError("Nome não pode ser vazio.")
    if not cpf.strip():
        raise ValueError("CPF não pode ser vazio.")
    if repo.buscar_cliente_por_id(cliente_id) is None:
        raise ValueError(f"Cliente com id {cliente_id} não encontrado.")

    cliente = Cliente(id=cliente_id, nome=nome.strip(), cpf=cpf.strip(),
                       telefone=telefone, email=email)
    repo.atualizar_cliente(cliente)
    return cliente


def excluir_cliente(cliente_id: int) -> None:
    if repo.buscar_cliente_por_id(cliente_id) is None:
        raise ValueError(f"Cliente com id {cliente_id} não encontrado.")
    # Não deixamos excluir um cliente que já tem empréstimos, para não
    # deixar "empréstimos órfãos" no banco (sem dono) nem apagar histórico
    # financeiro sem querer. A pessoa precisa lidar com os empréstimos
    # primeiro (ex: cancelar os que estiverem em aberto).
    if repo.listar_emprestimos(cliente_id):
        raise ValueError(
            "Este cliente possui empréstimos cadastrados e não pode ser excluído. "
            "Cancele ou quite os empréstimos dele antes de excluir o cadastro."
        )
    repo.excluir_cliente(cliente_id)


# ---------- Cálculo financeiro: Tabela Price ----------
#
# A Tabela Price (também chamada de "Sistema Francês de Amortização") é o
# método que a maioria dos bancos usa de verdade. A diferença central para
# juros simples é: os juros de cada parcela incidem sobre o SALDO DEVEDOR
# restante, não sobre o valor original emprestado. Como o saldo diminui a
# cada parcela paga, o valor de juros também diminui mês a mês — mesmo a
# parcela sendo sempre igual.
#
# Fórmula da parcela fixa (PMT = "payment"):
#
#            PV * i
#   PMT = ----------------
#          1 - (1 + i)^-n
#
#   PV = valor principal (emprestado)
#   i  = taxa de juros mensal (ex: 0.05 para 5%)
#   n  = número de parcelas
#
# Cada parcela então se divide em duas partes:
#   juros        = saldo_devedor_atual * i        (o "aluguel do dinheiro")
#   amortização  = valor_da_parcela - juros         (o que realmente abate a dívida)
#   novo_saldo   = saldo_devedor_atual - amortização
#
# Por isso, no início do contrato, a maior parte da parcela é juros; perto
# do fim, a maior parte é amortização — mesmo o valor da parcela nunca
# mudando. Isso é exatamente o que aparece no extrato de um financiamento
# bancário real.

def somar_meses(data_base: date, meses: int) -> date:
    """
    Soma 'meses' à data_base, sem depender de bibliotecas externas.
    Ex: 31/01/2026 + 1 mês = 28/02/2026 (fevereiro não tem dia 31, então
    usamos o último dia válido do mês de destino).
    """
    mes_total = data_base.month - 1 + meses
    ano = data_base.year + mes_total // 12
    mes = mes_total % 12 + 1
    ultimo_dia_do_mes = monthrange(ano, mes)[1]
    dia = min(data_base.day, ultimo_dia_do_mes)
    return date(ano, mes, dia)


def calcular_parcela_price(valor_principal: float, taxa_juros_mensal: float,
                            numero_parcelas: int) -> float:
    if taxa_juros_mensal == 0:
        # Sem juros, é só dividir o valor igualmente (evita divisão por
        # zero na fórmula, já que (1+0)^-n sempre resulta em 1).
        return round(valor_principal / numero_parcelas, 2)

    i = taxa_juros_mensal
    fator = 1 - (1 + i) ** (-numero_parcelas)
    pmt = valor_principal * i / fator
    return round(pmt, 2)


def gerar_parcelas(valor_principal: float, taxa_juros_mensal: float,
                    numero_parcelas: int, data_emprestimo: date) -> list[Parcela]:
    valor_parcela = calcular_parcela_price(valor_principal, taxa_juros_mensal, numero_parcelas)
    parcelas = []
    saldo_devedor = valor_principal

    for n in range(1, numero_parcelas + 1):
        juros_parcela = round(saldo_devedor * taxa_juros_mensal, 2)

        if n == numero_parcelas:
            # Na última parcela, forçamos a amortização a fechar exatamente
            # o saldo devedor. Isso evita que sobre ou falte 1 ou 2
            # centavos de "resíduo" no fim do contrato por causa de
            # arredondamentos acumulados ao longo das parcelas.
            amortizacao = round(saldo_devedor, 2)
            valor_desta_parcela = round(amortizacao + juros_parcela, 2)
        else:
            amortizacao = round(valor_parcela - juros_parcela, 2)
            valor_desta_parcela = valor_parcela

        saldo_devedor = round(saldo_devedor - amortizacao, 2)

        # somar_meses avança "meses de verdade" (ex: 31/jan + 1 mês =
        # 28 ou 29/fev), diferente de timedelta(days=30) que acumularia
        # erro mês a mês.
        vencimento = somar_meses(data_emprestimo, n)

        parcelas.append(Parcela(
            emprestimo_id=0,  # preenchido depois de salvar o empréstimo (tem que ter o id)
            numero=n,
            valor=valor_desta_parcela,
            juros=juros_parcela,
            amortizacao=amortizacao,
            saldo_devedor=max(saldo_devedor, 0.0),
            data_vencimento=vencimento,
        ))
    return parcelas


# ---------- Empréstimos ----------

def criar_emprestimo(cliente_id: int, valor_principal: float, taxa_juros_mensal: float,
                      numero_parcelas: int, data_emprestimo: date = None) -> Emprestimo:
    if valor_principal <= 0:
        raise ValueError("Valor do empréstimo deve ser maior que zero.")
    if numero_parcelas <= 0:
        raise ValueError("Número de parcelas deve ser maior que zero.")
    if taxa_juros_mensal < 0:
        raise ValueError("Taxa de juros não pode ser negativa.")
    if repo.buscar_cliente_por_id(cliente_id) is None:
        raise ValueError(f"Cliente com id {cliente_id} não encontrado.")

    data_emprestimo = data_emprestimo or date.today()

    emprestimo = Emprestimo(
        cliente_id=cliente_id,
        valor_principal=valor_principal,
        taxa_juros_mensal=taxa_juros_mensal,
        numero_parcelas=numero_parcelas,
        data_emprestimo=data_emprestimo,
    )
    emprestimo.parcelas = gerar_parcelas(valor_principal, taxa_juros_mensal,
                                          numero_parcelas, data_emprestimo)
    return repo.salvar_emprestimo(emprestimo)


def registrar_pagamento_parcela(parcela_id: int, data_pagamento: date = None) -> None:
    data_pagamento = data_pagamento or date.today()
    repo.atualizar_status_parcela(parcela_id, StatusParcela.PAGA, data_pagamento)
    _verificar_quitacao_automatica(parcela_id)


def _verificar_quitacao_automatica(parcela_id: int) -> None:
    """Se todas as parcelas de um empréstimo estão pagas, marca o empréstimo como quitado."""
    conn_emprestimos = repo.listar_emprestimos()
    for emp in conn_emprestimos:
        ids_parcelas = [p.id for p in emp.parcelas]
        if parcela_id in ids_parcelas:
            todas_pagas = all(p.status == StatusParcela.PAGA for p in emp.parcelas)
            if todas_pagas:
                repo.atualizar_status_emprestimo(emp.id, StatusEmprestimo.QUITADO)
            return


def atualizar_parcelas_atrasadas() -> int:
    """
    Percorre todas as parcelas pendentes e marca como ATRASADA as que já
    passaram da data de vencimento. Retorna quantas foram atualizadas.
    Ideal rodar isso toda vez que o sistema abre.
    """
    hoje = date.today()
    total_atualizadas = 0
    for emp in repo.listar_emprestimos():
        for parcela in emp.parcelas:
            if parcela.status == StatusParcela.PENDENTE and parcela.data_vencimento < hoje:
                repo.atualizar_status_parcela(parcela.id, StatusParcela.ATRASADA)
                total_atualizadas += 1
    return total_atualizadas


def cancelar_emprestimo(emprestimo_id: int) -> None:
    """
    Cancela um empréstimo. Só permitimos cancelar se nenhuma parcela já
    tiver sido paga — depois que existe dinheiro pago de verdade, cancelar
    o contrato inteiro deixaria o histórico financeiro inconsistente
    (dinheiro recebido "sumiria" sem explicação nos relatórios).
    """
    emprestimos = {e.id: e for e in repo.listar_emprestimos()}
    emprestimo = emprestimos.get(emprestimo_id)
    if emprestimo is None:
        raise ValueError(f"Empréstimo com id {emprestimo_id} não encontrado.")
    if emprestimo.status != StatusEmprestimo.ABERTO:
        raise ValueError(f"Este empréstimo já está '{emprestimo.status.value}' e não pode ser cancelado.")
    if any(p.status == StatusParcela.PAGA for p in emprestimo.parcelas):
        raise ValueError("Não é possível cancelar: este empréstimo já tem parcela(s) paga(s).")
    repo.atualizar_status_emprestimo(emprestimo_id, StatusEmprestimo.CANCELADO)


def filtrar_emprestimos(status: str = "", busca: str = "") -> list[Emprestimo]:
    """
    Filtra empréstimos por status (aberto/quitado/cancelado) e/ou por texto
    de busca (nome ou CPF do cliente). Feito em Python sobre a lista
    completa em vez de SQL — para um sistema local de pequeno porte como
    este, a diferença de performance é irrelevante, e fica bem mais simples
    de ler e reaproveitar tanto na CLI quanto na web.
    """
    emprestimos = repo.listar_emprestimos()
    clientes_por_id = {c.id: c for c in repo.listar_clientes()}

    if status:
        emprestimos = [e for e in emprestimos if e.status.value == status]

    if busca:
        busca = busca.strip().lower()
        emprestimos = [
            e for e in emprestimos
            if busca in clientes_por_id[e.cliente_id].nome.lower()
            or busca in clientes_por_id[e.cliente_id].cpf.lower()
        ]

    return emprestimos


# ---------- Multa e juros de mora (parcelas atrasadas) ----------
#
# Regras usadas aqui, baseadas no que é comum e permitido em contratos no
# Brasil (o Código de Defesa do Consumidor limita a multa por atraso a 2%
# do valor da parcela):
#
#   multa      = 2% do valor da parcela, cobrada uma única vez
#   juros_mora = 1% ao mês (proporcional aos dias de atraso) sobre o valor
#                da parcela
#
# Esses valores não são gravados no banco — são calculados "na hora", porque
# mudam a cada dia que passa. Guardar um valor de juros de mora do dia
# anterior no banco significaria ele ficar desatualizado assim que a data
# virasse.

MULTA_ATRASO_PERCENTUAL = 0.02       # 2% (limite do CDC), cobrada uma vez
JUROS_MORA_AO_MES = 0.01             # 1% ao mês, proporcional aos dias


def calcular_encargos_atraso(parcela: Parcela, hoje: date = None) -> dict:
    hoje = hoje or date.today()

    if parcela.status != StatusParcela.ATRASADA:
        return {"dias_atraso": 0, "multa": 0.0, "juros_mora": 0.0, "valor_atualizado": parcela.valor}

    dias_atraso = max((hoje - parcela.data_vencimento).days, 0)
    multa = round(parcela.valor * MULTA_ATRASO_PERCENTUAL, 2)
    juros_mora_ao_dia = JUROS_MORA_AO_MES / 30
    juros_mora = round(parcela.valor * juros_mora_ao_dia * dias_atraso, 2)
    valor_atualizado = round(parcela.valor + multa + juros_mora, 2)

    return {
        "dias_atraso": dias_atraso,
        "multa": multa,
        "juros_mora": juros_mora,
        "valor_atualizado": valor_atualizado,
    }


def resumo_emprestimo(emprestimo: Emprestimo) -> dict:
    """Calcula totais úteis para exibir na tela: total pago, total em aberto, etc."""
    total_pago = sum(p.valor for p in emprestimo.parcelas if p.status == StatusParcela.PAGA)
    total_pendente = sum(p.valor for p in emprestimo.parcelas
                          if p.status in (StatusParcela.PENDENTE, StatusParcela.ATRASADA))
    total_atrasado = sum(p.valor for p in emprestimo.parcelas if p.status == StatusParcela.ATRASADA)
    valor_total_contrato = sum(p.valor for p in emprestimo.parcelas)
    total_juros = sum(p.juros for p in emprestimo.parcelas)
    return {
        "valor_total_contrato": round(valor_total_contrato, 2),
        "total_pago": round(total_pago, 2),
        "total_pendente": round(total_pendente, 2),
        "total_atrasado": round(total_atrasado, 2),
        "total_juros": round(total_juros, 2),
    }


# ---------- Cobrança via WhatsApp ----------
#
# A ideia aqui não é enviar mensagem sozinho (isso exigiria uma API paga
# tipo Twilio, ou automações de navegador instáveis que podem até fazer o
# WhatsApp bloquear o número por comportamento suspeito). Em vez disso,
# geramos um link "wa.me" — o mesmo link que o botão "Enviar mensagem" de
# qualquer site usa — já com o número do cliente e a mensagem prontos.
# Você só clica, confere, e aperta enviar. Zero custo, zero cadastro.

DIAS_AVISO_PREVIO_PADRAO = 3  # a partir de quantos dias antes do vencimento já avisamos o cliente


def _formatar_telefone_whatsapp(telefone: str) -> str:
    """
    Limpa o telefone (tira parênteses, traço, espaço) e garante o código
    do país (55 = Brasil) na frente, que é o formato que o link do
    WhatsApp exige. Ex: "(31) 99999-0000" -> "5531999990000"
    """
    apenas_digitos = re.sub(r"\D", "", telefone or "")
    if not apenas_digitos:
        return ""
    if not apenas_digitos.startswith("55"):
        apenas_digitos = "55" + apenas_digitos
    return apenas_digitos


def gerar_link_whatsapp(telefone: str, mensagem: str) -> str:
    """Monta o link wa.me pronto para abrir o WhatsApp com a mensagem preenchida."""
    numero = _formatar_telefone_whatsapp(telefone)
    if not numero:
        return ""
    return f"https://wa.me/{numero}?text={quote(mensagem)}"


def montar_mensagem_lembrete(cliente: Cliente, emprestimo: Emprestimo, parcela: Parcela) -> str:
    primeiro_nome = cliente.nome.split()[0]
    dias = (parcela.data_vencimento - date.today()).days
    quando = "vence hoje" if dias == 0 else f"vence em {dias} dia(s)"
    return (
        f"Olá, {primeiro_nome}! 😊 Passando para lembrar que a parcela "
        f"{parcela.numero}/{emprestimo.numero_parcelas} do seu empréstimo {quando} "
        f"({parcela.data_vencimento.strftime('%d/%m/%Y')}), no valor de "
        f"{formatar_moeda(parcela.valor)}. Qualquer dúvida, é só chamar!"
    )


def montar_mensagem_atraso(cliente: Cliente, emprestimo: Emprestimo, parcela: Parcela) -> str:
    primeiro_nome = cliente.nome.split()[0]
    encargos = calcular_encargos_atraso(parcela)
    return (
        f"Olá, {primeiro_nome}. A parcela {parcela.numero}/{emprestimo.numero_parcelas} "
        f"do seu empréstimo venceu em {parcela.data_vencimento.strftime('%d/%m/%Y')} "
        f"({encargos['dias_atraso']} dia(s) de atraso). Valor original: "
        f"{formatar_moeda(parcela.valor)}. Com a multa e os juros de mora, o valor "
        f"atualizado é {formatar_moeda(encargos['valor_atualizado'])}. Poderia regularizar "
        f"assim que possível? Qualquer dúvida, estou à disposição."
    )


def listar_cobrancas(dias_aviso_previo: int = DIAS_AVISO_PREVIO_PADRAO) -> list[dict]:
    """
    Monta a lista de parcelas que precisam de contato: lembrete amigável
    para quem vence nos próximos `dias_aviso_previo` dias (ou hoje), e
    cobrança para quem já está atrasado. Cada item já vem com a mensagem
    e o link do WhatsApp prontos para uso na tela (CLI ou web).
    """
    hoje = date.today()
    clientes_por_id = {c.id: c for c in repo.listar_clientes()}
    cobrancas = []

    for emprestimo in repo.listar_emprestimos():
        if emprestimo.status != StatusEmprestimo.ABERTO:
            continue
        cliente = clientes_por_id.get(emprestimo.cliente_id)
        if cliente is None:
            continue

        for parcela in emprestimo.parcelas:
            if parcela.status == StatusParcela.ATRASADA:
                tipo = "atraso"
                mensagem = montar_mensagem_atraso(cliente, emprestimo, parcela)
            elif parcela.status == StatusParcela.PENDENTE:
                dias_para_vencer = (parcela.data_vencimento - hoje).days
                if not (0 <= dias_para_vencer <= dias_aviso_previo):
                    continue
                tipo = "lembrete"
                mensagem = montar_mensagem_lembrete(cliente, emprestimo, parcela)
            else:
                continue

            cobrancas.append({
                "cliente": cliente,
                "emprestimo": emprestimo,
                "parcela": parcela,
                "tipo": tipo,
                "mensagem": mensagem,
                "link_whatsapp": gerar_link_whatsapp(cliente.telefone, mensagem),
            })

    # Atrasados primeiro (mais urgente), depois por data de vencimento mais próxima
    cobrancas.sort(key=lambda c: (c["tipo"] != "atraso", c["parcela"].data_vencimento))
    return cobrancas
