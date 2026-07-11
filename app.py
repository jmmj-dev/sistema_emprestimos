"""
app.py
------
Camada web. Note que este arquivo NÃO sabe nada sobre SQL, nem faz cálculo
de juros — ele só chama services.py (a mesma camada de regras de negócio
que o main.py de terminal usa) e decide o que mostrar em cada página.

Isso prova o valor de ter separado o projeto em camadas desde o início:
para ganhar uma versão web inteira, não precisamos tocar em database.py,
models.py, repositories.py nem services.py.

Para rodar: python app.py
Depois acesse http://127.0.0.1:5000 no navegador.
"""

from datetime import date, datetime

from flask import Flask, render_template, request, redirect, url_for, flash

import repositories as repo
import services
from database import inicializar_banco
from models import Cliente, StatusParcela

app = Flask(__name__)
app.secret_key = "chave-de-desenvolvimento-troque-em-producao"

inicializar_banco()


@app.before_request
def atualizar_atrasos():
    # Roda antes de cada requisição: garante que o status de atraso das
    # parcelas está sempre em dia, sem precisar de um processo separado.
    services.atualizar_parcelas_atrasadas()


# ---------- Dashboard ----------

@app.route("/")
def dashboard():
    emprestimos = repo.listar_emprestimos()
    total_emprestado = sum(e.valor_principal for e in emprestimos)
    total_a_receber = 0.0
    total_atrasado = 0.0
    total_recebido = 0.0
    for emp in emprestimos:
        resumo = services.resumo_emprestimo(emp)
        total_a_receber += resumo["total_pendente"]
        total_atrasado += resumo["total_atrasado"]
        total_recebido += resumo["total_pago"]

    emprestimos_recentes = sorted(emprestimos, key=lambda e: e.data_emprestimo, reverse=True)[:5]
    clientes_por_id = {c.id: c for c in repo.listar_clientes()}

    return render_template(
        "dashboard.html",
        total_emprestado=total_emprestado,
        total_a_receber=total_a_receber,
        total_atrasado=total_atrasado,
        total_recebido=total_recebido,
        total_clientes=len(repo.listar_clientes()),
        total_emprestimos=len(emprestimos),
        emprestimos_recentes=emprestimos_recentes,
        clientes_por_id=clientes_por_id,
    )


# ---------- Clientes ----------

@app.route("/clientes")
def listar_clientes():
    busca = request.args.get("q", "").strip()
    clientes = repo.listar_clientes()
    if busca:
        busca_lower = busca.lower()
        clientes = [c for c in clientes if busca_lower in c.nome.lower() or busca_lower in c.cpf.lower()]
    return render_template("clientes.html", clientes=clientes, busca=busca)


@app.route("/clientes/novo", methods=["GET", "POST"])
def novo_cliente():
    if request.method == "POST":
        try:
            services.cadastrar_cliente(
                nome=request.form["nome"],
                cpf=request.form["cpf"],
                telefone=request.form.get("telefone", ""),
                email=request.form.get("email", ""),
            )
            flash("Cliente cadastrado com sucesso.", "sucesso")
            return redirect(url_for("listar_clientes"))
        except ValueError as e:
            flash(str(e), "erro")
    return render_template("novo_cliente.html")


@app.route("/clientes/<int:cliente_id>/editar", methods=["GET", "POST"])
def editar_cliente(cliente_id):
    cliente = repo.buscar_cliente_por_id(cliente_id)
    if cliente is None:
        flash("Cliente não encontrado.", "erro")
        return redirect(url_for("listar_clientes"))

    if request.method == "POST":
        try:
            services.atualizar_cliente(
                cliente_id=cliente_id,
                nome=request.form["nome"],
                cpf=request.form["cpf"],
                telefone=request.form.get("telefone", ""),
                email=request.form.get("email", ""),
            )
            flash("Cliente atualizado com sucesso.", "sucesso")
            return redirect(url_for("listar_clientes"))
        except ValueError as e:
            flash(str(e), "erro")
            cliente = Cliente(id=cliente_id, nome=request.form["nome"], cpf=request.form["cpf"],
                               telefone=request.form.get("telefone", ""), email=request.form.get("email", ""))

    return render_template("editar_cliente.html", cliente=cliente)


@app.route("/clientes/<int:cliente_id>/excluir", methods=["POST"])
def excluir_cliente(cliente_id):
    try:
        services.excluir_cliente(cliente_id)
        flash("Cliente excluído com sucesso.", "sucesso")
    except ValueError as e:
        flash(str(e), "erro")
    return redirect(url_for("listar_clientes"))


# ---------- Empréstimos ----------

@app.route("/emprestimos")
def listar_emprestimos():
    status = request.args.get("status", "")
    busca = request.args.get("q", "").strip()
    emprestimos = services.filtrar_emprestimos(status=status, busca=busca)
    emprestimos.sort(key=lambda e: e.data_emprestimo, reverse=True)
    clientes_por_id = {c.id: c for c in repo.listar_clientes()}
    resumos = {e.id: services.resumo_emprestimo(e) for e in emprestimos}
    return render_template(
        "emprestimos.html",
        emprestimos=emprestimos,
        clientes_por_id=clientes_por_id,
        resumos=resumos,
        status_selecionado=status,
        busca=busca,
    )


@app.route("/emprestimos/novo", methods=["GET", "POST"])
def novo_emprestimo():
    clientes = repo.listar_clientes()
    if request.method == "POST":
        try:
            data_txt = request.form.get("data_emprestimo", "").strip()
            data_emp = datetime.strptime(data_txt, "%Y-%m-%d").date() if data_txt else date.today()
            emp = services.criar_emprestimo(
                cliente_id=int(request.form["cliente_id"]),
                valor_principal=float(request.form["valor_principal"]),
                taxa_juros_mensal=float(request.form["taxa_juros_mensal"]) / 100,
                numero_parcelas=int(request.form["numero_parcelas"]),
                data_emprestimo=data_emp,
            )
            flash("Empréstimo criado com sucesso.", "sucesso")
            return redirect(url_for("detalhe_emprestimo", emprestimo_id=emp.id))
        except ValueError as e:
            flash(str(e), "erro")
    return render_template("novo_emprestimo.html", clientes=clientes, hoje=date.today().isoformat())


@app.route("/emprestimos/<int:emprestimo_id>")
def detalhe_emprestimo(emprestimo_id):
    emprestimos = {e.id: e for e in repo.listar_emprestimos()}
    emprestimo = emprestimos.get(emprestimo_id)
    if emprestimo is None:
        flash("Empréstimo não encontrado.", "erro")
        return redirect(url_for("listar_emprestimos"))
    cliente = repo.buscar_cliente_por_id(emprestimo.cliente_id)
    resumo = services.resumo_emprestimo(emprestimo)
    encargos_por_parcela = {p.id: services.calcular_encargos_atraso(p) for p in emprestimo.parcelas}
    pode_cancelar = (
        emprestimo.status.value == "aberto"
        and not any(p.status.value == "paga" for p in emprestimo.parcelas)
    )
    return render_template(
        "emprestimo_detalhe.html",
        emprestimo=emprestimo,
        cliente=cliente,
        resumo=resumo,
        hoje=date.today(),
        encargos_por_parcela=encargos_por_parcela,
        pode_cancelar=pode_cancelar,
    )


@app.route("/emprestimos/<int:emprestimo_id>/cancelar", methods=["POST"])
def cancelar_emprestimo(emprestimo_id):
    try:
        services.cancelar_emprestimo(emprestimo_id)
        flash("Empréstimo cancelado.", "sucesso")
    except ValueError as e:
        flash(str(e), "erro")
    return redirect(url_for("detalhe_emprestimo", emprestimo_id=emprestimo_id))


@app.route("/parcelas/<int:parcela_id>/pagar", methods=["POST"])
def pagar_parcela(parcela_id):
    emprestimo_id = request.form.get("emprestimo_id")
    try:
        services.registrar_pagamento_parcela(parcela_id)
        flash("Pagamento registrado.", "sucesso")
    except Exception as e:
        flash(f"Erro ao registrar pagamento: {e}", "erro")
    return redirect(url_for("detalhe_emprestimo", emprestimo_id=emprestimo_id))


if __name__ == "__main__":
    app.run(debug=True)
