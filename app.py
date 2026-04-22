from flask import Flask, render_template, request, redirect, url_for, session, flash
import pandas as pd
import io
import re
import os
import json
from collections import defaultdict
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave")
app.config["MAX_CONTENT_LENGTH"] = 30 * 1024 * 1024

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "dashboard_data.json")
UPLOAD_FILE = os.path.join(DATA_DIR, "ultima_planilha.xlsx")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

MESES_ORDEM = {
    "JAN": 1, "JANEIRO": 1, "FEV": 2, "FEVEREIRO": 2, "MAR": 3, "MARCO": 3, "MARÇO": 3,
    "ABR": 4, "ABRIL": 4, "MAI": 5, "MAIO": 5, "JUN": 6, "JUNHO": 6, "JUL": 7, "JULHO": 7,
    "AGO": 8, "AGOSTO": 8, "SET": 9, "SETEMBRO": 9, "OUT": 10, "OUTUBRO": 10,
    "NOV": 11, "NOVEMBRO": 11, "DEZ": 12, "DEZEMBRO": 12
}
MESES_SELECT = [("1","Janeiro"),("2","Fevereiro"),("3","Março"),("4","Abril"),("5","Maio"),("6","Junho"),
                ("7","Julho"),("8","Agosto"),("9","Setembro"),("10","Outubro"),("11","Novembro"),("12","Dezembro")]

def garantir_pasta_dados():
    os.makedirs(DATA_DIR, exist_ok=True)

def usuario_logado():
    return session.get("admin_ok") is True

def detectar_coluna_obs(df):
    for col in df.columns:
        serie = df[col].astype(str).str.upper().str.strip()
        if ((serie == "NÃO REALIZADO") | (serie == "NAO REALIZADO")).any():
            return col
    return None

def encontrar_coluna(df, candidatos):
    mapa = {str(c).strip().upper(): c for c in df.columns}
    for nome in candidatos:
        if nome in mapa:
            return mapa[nome]
    return None

def extrair_empresa(valor):
    if pd.isna(valor):
        return "SEM EMPRESA"
    texto = str(valor).strip()
    if not texto:
        return "SEM EMPRESA"
    for sep in [" - ", "•"]:
        if sep in texto:
            return texto.split(sep)[0].strip()
    return texto

def formatar_data(valor):
    if pd.isna(valor) or valor == "":
        return "-"
    try:
        dt = pd.to_datetime(valor, errors="coerce", dayfirst=True)
        if pd.notna(dt):
            return dt.strftime("%d/%m/%Y")
    except Exception:
        pass
    return str(valor).strip()

def extrair_ano_mes(nome_aba):
    texto = str(nome_aba).upper()
    ano_match = re.search(r"(20\d{2})", texto)
    ano = int(ano_match.group(1)) if ano_match else None
    mes_num = None
    for nome, num in MESES_ORDEM.items():
        if nome in texto:
            mes_num = num
            break
    return ano, mes_num, str(nome_aba)

def data_referencia_registro(ano, mes_num):
    if ano and mes_num:
        return datetime(ano, mes_num, 1)
    if ano:
        return datetime(ano, 1, 1)
    return None

def processar_planilha(stream):
    registros, avisos = [], []
    with pd.ExcelFile(stream, engine="openpyxl") as xls:
        for aba in xls.sheet_names:
            try:
                df = pd.read_excel(xls, sheet_name=aba)
            except Exception as e:
                avisos.append(f"A aba '{aba}' não pôde ser lida: {e}")
                continue
            if df.empty:
                continue
            col_obs = detectar_coluna_obs(df)
            if col_obs is None:
                continue
            col_empresa = encontrar_coluna(df, ["SETOR", "EMPRESA", "CLIENTE", "DEPOSITANTE"])
            col_func = encontrar_coluna(df, ["FUNCIONÁRIO", "FUNCIONARIO", "NOME", "COLABORADOR"])
            col_exame = encontrar_coluna(df, ["TIPO DE EXAME", "TIPO", "EXAME"])
            col_data = encontrar_coluna(df, ["DATA", "DT EXAME", "DATA EXAME"])
            col_recibo = df.columns[2] if len(df.columns) > 2 else None
            serie_obs = df[col_obs].astype(str).str.upper().str.strip()
            filtrado = df[(serie_obs == "NÃO REALIZADO") | (serie_obs == "NAO REALIZADO")]
            if filtrado.empty:
                continue
            ano, mes_num, mes_nome = extrair_ano_mes(aba)
            data_ref = data_referencia_registro(ano, mes_num)
            for _, row in filtrado.iterrows():
                registros.append({
                    "ano": ano if ano else "Sem ano",
                    "mes": mes_nome,
                    "mes_num": mes_num if mes_num else 99,
                    "empresa": extrair_empresa(row[col_empresa]) if col_empresa else "SEM EMPRESA",
                    "funcionario": str(row[col_func]).strip() if col_func and pd.notna(row[col_func]) else "-",
                    "exame": str(row[col_exame]).strip() if col_exame and pd.notna(row[col_exame]) else "-",
                    "data": formatar_data(row[col_data]) if col_data else "-",
                    "recibo": str(row[col_recibo]).strip() if col_recibo and pd.notna(row[col_recibo]) else "-",
                    "data_ref": data_ref.strftime("%Y-%m-%d") if data_ref else None
                })
    registros.sort(key=lambda x: ((x["ano"] if isinstance(x["ano"], int) else 0), x["mes_num"], x["empresa"], x["recibo"]))
    return registros, avisos

def salvar_dados(payload):
    garantir_pasta_dados()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def carregar_dados():
    if not os.path.exists(DATA_FILE):
        return None
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

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
        arquivo = request.files.get("arquivo")
        if not arquivo or not arquivo.filename:
            flash("Selecione uma planilha para atualizar a base.", "error")
            return redirect(url_for("admin"))
        try:
            garantir_pasta_dados()
            conteudo = arquivo.read()
            with open(UPLOAD_FILE, "wb") as f:
                f.write(conteudo)
            registros, avisos_proc = processar_planilha(io.BytesIO(conteudo))
            salvar_dados({
                "arquivo_original": secure_filename(arquivo.filename),
                "ultima_atualizacao": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "avisos": avisos_proc,
                "registros": registros
            })
            flash("Base atualizada com sucesso. Agora todos verão esses dados sem reenviar a planilha.", "success")
            return redirect(url_for("admin"))
        except Exception as e:
            flash(f"Erro ao atualizar a base: {e}", "error")
            return redirect(url_for("admin"))
    return render_template("admin.html", ultima_atualizacao=ultima_atualizacao, nome_arquivo=nome_arquivo,
                           ultimo_total=ultimo_total, ultimo_empresas=ultimo_empresas, avisos=avisos)

if __name__ == "__main__":
    garantir_pasta_dados()
    app.run(debug=True)
