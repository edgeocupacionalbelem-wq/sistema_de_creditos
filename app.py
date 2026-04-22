from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
import json
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
DATA_FILE = os.path.join(DATA_DIR, "dashboard_data.json")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

MESES_SELECT = [
    ("1","Janeiro"),("2","Fevereiro"),("3","Março"),("4","Abril"),
    ("5","Maio"),("6","Junho"),("7","Julho"),("8","Agosto"),
    ("9","Setembro"),("10","Outubro"),("11","Novembro"),("12","Dezembro")
]

def garantir_pasta():
    os.makedirs(DATA_DIR, exist_ok=True)

def usuario_logado():
    return session.get("admin_ok") is True

def carregar_dados():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_dados(payload):
    garantir_pasta()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def filtrar_intervalo(registros, inicio_mes, inicio_ano, fim_mes, fim_ano):
    if not inicio_mes or not inicio_ano:
        return registros
    try:
        dt_inicio = datetime(int(inicio_ano), int(inicio_mes), 1)
        if fim_mes and fim_ano:
            dt_fim = datetime(int(fim_ano), int(fim_mes), 1)
        else:
            hoje = datetime.today()
            dt_fim = datetime(hoje.year, hoje.month, 1)
    except Exception:
        return registros

    saida = []
    for r in registros:
        data_ref = r.get("data_ref")
        if not data_ref:
            continue
        try:
            dt_reg = datetime.strptime(data_ref, "%Y-%m-%d")
        except Exception:
            continue
        if dt_inicio <= dt_reg <= dt_fim:
            saida.append(r)
    return saida

def resumo_global(registros):
    return {
        "total_creditos": len(registros),
        "total_empresas": len(set(r["empresa"] for r in registros)),
        "total_anos": len(set(str(r["ano"]) for r in registros)),
        "total_meses": len(set((str(r["ano"]), str(r["mes"]), int(r["mes_num"])) for r in registros)),
    }

def resumir_por_ano(registros):
    grupos_map = defaultdict(list)
    for r in registros:
        grupos_map[str(r["ano"])].append(r)
    grupos = []
    for ano, itens in sorted(grupos_map.items(), key=lambda x: x[0]):
        resumo_recibos = defaultdict(lambda: {"empresa": "", "qtd": 0})
        for i in itens:
            chave = (i["empresa"], i["recibo"])
            resumo_recibos[chave]["empresa"] = i["empresa"]
            resumo_recibos[chave]["qtd"] += 1
        linhas = [{"empresa": empresa, "recibo": recibo, "creditos": info["qtd"]}
                  for (empresa, recibo), info in sorted(resumo_recibos.items(), key=lambda x: (-x[1]["qtd"], x[0][0], x[0][1]))]
        grupos.append({"nome": ano, "total_creditos": len(itens), "total_empresas": len(set(i["empresa"] for i in itens)),
                       "linhas": linhas[:120], "total_linhas": len(linhas)})
    return grupos

def resumir_por_mes(registros):
    grupos_map = defaultdict(list)
    for r in registros:
        grupos_map[(str(r["ano"]), int(r["mes_num"]), str(r["mes"]))].append(r)
    grupos = []
    for (ano, _, mes), itens in sorted(grupos_map.items(), key=lambda x: (x[0][0], x[0][1], x[0][2])):
        resumo_recibos = defaultdict(lambda: {"empresa": "", "qtd": 0})
        for i in itens:
            chave = (i["empresa"], i["recibo"])
            resumo_recibos[chave]["empresa"] = i["empresa"]
            resumo_recibos[chave]["qtd"] += 1
        linhas = [{"empresa": empresa, "recibo": recibo, "creditos": info["qtd"]}
                  for (empresa, recibo), info in sorted(resumo_recibos.items(), key=lambda x: (-x[1]["qtd"], x[0][0], x[0][1]))]
        grupos.append({"nome": f"{mes} / {ano}", "total_creditos": len(itens), "total_empresas": len(set(i["empresa"] for i in itens)),
                       "linhas": linhas[:120], "total_linhas": len(linhas)})
    return grupos

def resumir_por_empresa(registros):
    grupos_map = defaultdict(list)
    for r in registros:
        grupos_map[r["empresa"]].append(r)
    grupos = []
    for empresa, itens in sorted(grupos_map.items(), key=lambda x: (-len(x[1]), x[0])):
        resumo_recibos = defaultdict(int)
        for i in itens:
            resumo_recibos[i["recibo"]] += 1
        linhas = [{"recibo": recibo, "creditos": qtd} for recibo, qtd in sorted(resumo_recibos.items(), key=lambda x: (-x[1], x[0]))]
        grupos.append({"nome": empresa, "total_creditos": len(itens), "total_anos": len(set(str(i["ano"]) for i in itens)),
                       "total_meses": len(set((str(i["ano"]), int(i["mes_num"])) for i in itens)),
                       "linhas": linhas[:120], "total_linhas": len(linhas)})
    return grupos

@app.route("/", methods=["GET"])
def index():
    visao = request.args.get("visao", "mes")
    inicio_mes = request.args.get("inicio_mes", "")
    inicio_ano = request.args.get("inicio_ano", "")
    fim_mes = request.args.get("fim_mes", "")
    fim_ano = request.args.get("fim_ano", "")
    payload = carregar_dados()
    grupos = []
    resumo = {"total_creditos": 0, "total_empresas": 0, "total_anos": 0, "total_meses": 0}
    ultima_atualizacao = None
    nome_arquivo = None
    if payload:
        registros = filtrar_intervalo(payload.get("registros", []), inicio_mes, inicio_ano, fim_mes, fim_ano)
        resumo = resumo_global(registros)
        ultima_atualizacao = payload.get("ultima_atualizacao")
        nome_arquivo = payload.get("arquivo_original")
        if visao == "ano":
            grupos = resumir_por_ano(registros)
        elif visao == "empresa":
            grupos = resumir_por_empresa(registros)
        else:
            grupos = resumir_por_mes(registros)
    return render_template("index.html", grupos=grupos, resumo=resumo, visao=visao,
                           inicio_mes=inicio_mes, inicio_ano=inicio_ano, fim_mes=fim_mes, fim_ano=fim_ano,
                           meses_select=MESES_SELECT, ultima_atualizacao=ultima_atualizacao,
                           nome_arquivo=nome_arquivo, tem_dados=payload is not None)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        senha = request.form.get("senha", "")
        if senha == ADMIN_PASSWORD:
            session["admin_ok"] = True
            flash("Login realizado com sucesso.", "success")
            return redirect(url_for("admin"))
        flash("Senha incorreta.", "error")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not usuario_logado():
        return redirect(url_for("admin_login"))

    payload = carregar_dados()
    ultima_atualizacao = payload.get("ultima_atualizacao") if payload else None
    nome_arquivo = payload.get("arquivo_original") if payload else None
    ultimo_total = len(payload.get("registros", [])) if payload else 0
    ultimo_empresas = len(set(r["empresa"] for r in payload.get("registros", []))) if payload else 0
    avisos = payload.get("avisos", []) if payload else []

    if request.method == "POST":
        arquivo = request.files.get("arquivo_json")
        if not arquivo or not arquivo.filename:
            flash("Selecione o arquivo JSON gerado localmente.", "error")
            return redirect(url_for("admin"))

        try:
            conteudo = arquivo.read().decode("utf-8")
            novo_payload = json.loads(conteudo)

            if not isinstance(novo_payload, dict) or "registros" not in novo_payload:
                flash("JSON inválido. Gere o arquivo novamente pelo processador local.", "error")
                return redirect(url_for("admin"))

            salvar_dados(novo_payload)
            flash("JSON publicado com sucesso. O painel público já está usando essa base.", "success")
            return redirect(url_for("admin"))
        except Exception as e:
            flash(f"Erro ao publicar o JSON: {e}", "error")
            return redirect(url_for("admin"))

    return render_template("admin.html", ultima_atualizacao=ultima_atualizacao, nome_arquivo=nome_arquivo,
                           ultimo_total=ultimo_total, ultimo_empresas=ultimo_empresas, avisos=avisos)

if __name__ == "__main__":
    garantir_pasta()
    app.run(debug=True)
