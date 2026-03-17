import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta
import warnings

# Silencia avisos
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
DB_NOME = "reforma.db"

def conectar_db():
    return sqlite3.connect(DB_NOME, check_same_thread=False)

def inicializar_db():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS obras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Produto TEXT,
            Custo REAL,
            Qtd_Parcelas INTEGER,
            Parcelas_Pagas INTEGER,
            Adiantamento REAL,
            Mes_Inicio TEXT
        )
    ''')
    cursor.execute("SELECT COUNT(*) FROM obras")
    if cursor.fetchone()[0] == 0:
        dados_iniciais = [
            ("Móveis", 22000.0, 6, 0, 4400.0, "2026-04"),
            ("Cabeceira", 1200.0, 10, 0, 0.0, "2026-04"),
            ("Piso", 5909.01, 10, 0, 0.0, "2026-04"),
            ("Pedreiro", 8000.0, 1, 0, 0.0, "2026-04"),
            ("Pedra", 7500.0, 10, 0, 0.0, "2026-04"),
            ("Elétrica", 0.0, 1, 0, 0.0, "2026-04"),
            ("Diversos", 100.0, 1, 0, 0.0, "2026-04")
        ]
        cursor.executemany('INSERT INTO obras (Produto, Custo, Qtd_Parcelas, Parcelas_Pagas, Adiantamento, Mes_Inicio) VALUES (?, ?, ?, ?, ?, ?)', dados_iniciais)
    conn.commit()
    conn.close()

# --- FUNÇÕES DE APOIO ---
def formata_brl(valor):
    if pd.isna(valor) or isinstance(valor, str): return valor
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def prever_fim(row):
    try:
        ini = datetime.strptime(str(row["Mes_Inicio"]), "%Y-%m")
        fim = ini + relativedelta(months=int(row["Qtd_Parcelas"]) - 1)
        return fim.strftime("%b/%y")
    except: return "---"

def estilizar_df(df):
    estilo = pd.DataFrame('', index=df.index, columns=df.columns)
    
    # Cores das Fontes
    if 'Valor Pago' in df.columns:
        estilo['Valor Pago'] = 'color: #28a745; font-weight: bold;'
    if 'Valor a Pagar' in df.columns:
        estilo['Valor a Pagar'] = 'color: #dc3545; font-weight: bold;'
    
    for i in range(len(df)):
        # Destacar linha de TOTAL (em negrito e fundo cinza claro)
        if df.iloc[i]["Produto"] == "TOTAL":
            estilo.iloc[i, :] = 'background-color: #f8f9fa; font-weight: 900; color: #000000;'
        # Destacar linhas quitadas (exceto o Total)
        elif "Valor a Pagar" in df.columns and df.iloc[i]["Valor a Pagar"] <= 0:
            if "Custo" in df.columns and df.iloc[i]["Custo"] > 0:
                estilo.iloc[i, :] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
    return estilo

# --- INÍCIO DO STREAMLIT ---
st.set_page_config(page_title="Gestão Venda e Reforma", layout="wide")
inicializar_db()

st.title("🏗️ Detalhamento da Obra")

# --- BARRA LATERAL ---
st.sidebar.header("💰 Valores Fixos")
v_venda = st.sidebar.number_input("Valor Venda", value=380000.0)
v_felipe = st.sidebar.number_input("Felipe", value=250000.0)
v_corretora = st.sidebar.number_input("Corretora", value=20000.0)
v_financiamento = st.sidebar.number_input("Financiamento", value=57323.17)

# --- CARGA E EDITOR ---
conn = conectar_db()
df_db = pd.read_sql_query("SELECT * FROM obras", conn)

df_editavel = st.data_editor(
    df_db, 
    num_rows="dynamic", 
    width='stretch', 
    hide_index=True, 
    column_config={"id": None} 
)

if not df_editavel.equals(df_db):
    df_editavel.to_sql("obras", conn, if_exists="replace", index=False)
    st.rerun()
conn.close()

# --- PROCESSAMENTO ---
df_calc = df_editavel.copy()
df_calc["Valor Parcela"] = (df_calc["Custo"] - df_calc["Adiantamento"]) / df_calc["Qtd_Parcelas"]
df_calc["Valor Pago"] = df_calc["Adiantamento"] + (df_calc["Parcelas_Pagas"] * df_calc["Valor Parcela"])
df_calc["Valor a Pagar"] = df_calc["Custo"] - df_calc["Valor Pago"]
df_calc["Última Parcela"] = df_calc.apply(prever_fim, axis=1)

# --- CRIAÇÃO DA LINHA DE TOTAL ---
linha_total = pd.DataFrame({
    'Produto': ['TOTAL'],
    'Custo': [df_calc['Custo'].sum()],
    'Qtd_Parcelas': [''],
    'Parcelas_Pagas': [''],
    'Adiantamento': [df_calc['Adiantamento'].sum()],
    'Mes_Inicio': [''],
    'Valor Parcela': [df_calc['Valor Parcela'].sum()],
    'Valor Pago': [df_calc['Valor Pago'].sum()],
    'Valor a Pagar': [df_calc['Valor a Pagar'].sum()],
    'Última Parcela': ['']
})

# Concatenar a linha de total ao dataframe de visualização
df_com_total = pd.concat([df_calc, linha_total], ignore_index=True)

# --- DASHBOARD VISUAL ---
col_t, col_g = st.columns([2.5, 1])

with col_t:
    # Remove a coluna ID
    df_visual = df_com_total.drop(columns=['id'], errors='ignore')
    
    st.dataframe(
        df_visual.style.format({
            "Custo": formata_brl, 
            "Valor Parcela": formata_brl, 
            "Valor Pago": formata_brl, 
            "Valor a Pagar": formata_brl, 
            "Adiantamento": formata_brl
        }).apply(estilizar_df, axis=None), 
        width='stretch',
        hide_index=True
    )

with col_g:
    fig = px.pie(df_calc, values='Custo', names='Produto', title="Distribuição de Gastos", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

# --- RESUMO FINANCEIRO ---
total_pago_obra = df_calc["Valor Pago"].sum()
saldo_intermediario = v_venda - v_corretora - v_felipe - v_financiamento
saldo_final = saldo_intermediario - total_pago_obra

st.divider()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Valor Venda", formata_brl(v_venda))
c2.write(f"**Saídas Fixas**\n\n :red[- {formata_brl(v_felipe + v_corretora + v_financiamento)}]")
c3.write(f"**Saldo Inter**\n\n :blue[{formata_brl(saldo_intermediario)}]")
c4.write(f"**Pago na Obra**\n\n :red[- {formata_brl(total_pago_obra)}]")
cor_f = "blue" if saldo_final >= 0 else "red"
c5.write(f"**Saldo Final**\n\n :{cor_f}[{formata_brl(saldo_final)}]")

if st.sidebar.button("🗑️ Resetar Banco"):
    if os.path.exists(DB_NOME):
        os.remove(DB_NOME)
        st.rerun()