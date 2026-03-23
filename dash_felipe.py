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

# --- CONFIGURAÇÃO ---
DB_NOME = "dados_felipe.db"

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
    conn.commit()
    conn.close()

# --- UTILITÁRIOS ---
def formata_brl(valor):
    if pd.isna(valor) or isinstance(valor, str) or valor is None: 
        return valor
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def prever_fim(row):
    try:
        ini = datetime.strptime(str(row["Mes_Inicio"]), "%Y-%m")
        qtd = int(row["Qtd_Parcelas"]) if int(row["Qtd_Parcelas"]) > 0 else 1
        fim = ini + relativedelta(months=qtd - 1)
        return fim.strftime("%b/%y")
    except: 
        return "---"

# --- INTERFACE ---
st.set_page_config(page_title="Gestão de Reforma", layout="wide", page_icon="🏗️")
inicializar_db()

# CSS Customizado para melhorar o visual
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1f77b4; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🏗️ Gestão Financeira de Reforma")
st.markdown("---")

# --- CARGA DE DADOS ---
conn = conectar_db()
df_db = pd.read_sql_query("SELECT * FROM obras", conn)

# --- SEÇÃO 1: EDITOR DE DADOS ---
with st.expander("📋 Editor de Itens e Custos", expanded=True):
    st.info("💡 Clique duas vezes em uma célula para editar ou use a última linha para adicionar novos itens.")
    df_editavel = st.data_editor(
        df_db, 
        num_rows="dynamic", 
        width='stretch', 
        hide_index=True, 
        column_config={
            "id": None,
            "Produto": st.column_config.TextColumn("Descrição do Item", width="medium"),
            "Custo": st.column_config.NumberColumn("Custo Total (R$)", format="%.2f"),
            "Qtd_Parcelas": st.column_config.NumberColumn("Qtd_Parcelas", min_value=1, default=1),
            "Parcelas_Pagas": st.column_config.NumberColumn("Parcelas Pagas", min_value=0, default=0),
            "Adiantamento": st.column_config.NumberColumn("Entrada (R$)", format="%.2f"),
            "Mes_Inicio": st.column_config.TextColumn("Início (AAAA-MM)")
        } 
    )

    if not df_editavel.equals(df_db):
        df_editavel.to_sql("obras", conn, if_exists="replace", index=False)
        conn.close()
        st.rerun()
conn.close()

# --- PROCESSAMENTO ---
if not df_editavel.empty:
    df_calc = df_editavel.copy()
    df_calc["Custo"] = pd.to_numeric(df_calc["Custo"]).fillna(0.0)
    df_calc["Adiantamento"] = pd.to_numeric(df_calc["Adiantamento"]).fillna(0.0)
    df_calc["Qtd_Parcelas"] = pd.to_numeric(df_calc["Qtd_Parcelas"]).fillna(1).replace(0, 1)
    df_calc["Parcelas_Pagas"] = pd.to_numeric(df_calc["Parcelas_Pagas"]).fillna(0)

    df_calc["Valor Parcela"] = (df_calc["Custo"] - df_calc["Adiantamento"]) / df_calc["Qtd_Parcelas"]
    df_calc["Valor Pago"] = df_calc["Adiantamento"] + (df_calc["Parcelas_Pagas"] * df_calc["Valor Parcela"])
    df_calc["Valor a Pagar"] = df_calc["Custo"] - df_calc["Valor Pago"]
    df_calc["Fim"] = df_calc.apply(prever_fim, axis=1)

    # --- MÉTRICAS GERAIS (KPIs) ---
    c1, c2, c3, c4 = st.columns(4)
    total_custo = df_calc["Custo"].sum()
    total_pago = df_calc["Valor Pago"].sum()
    total_pendente = df_calc["Valor a Pagar"].sum()
    progresso = (total_pago / total_custo) if total_custo > 0 else 0

    c1.metric("Investimento Total", formata_brl(total_custo))
    c2.metric("Total Pago", formata_brl(total_pago), delta=f"{progresso:.1%}", delta_color="normal")
    c3.metric("Saldo Devedor", formata_brl(total_pendente), delta_color="inverse")
    
    with c4:
        st.write("**Progresso Quitação**")
        st.progress(progresso)
        st.write(f"{progresso:.1%} concluído")

    st.markdown("---")

    # --- SEÇÃO 2: VISUALIZAÇÃO ---
    col_t, col_g = st.columns([1.8, 1])

    with col_t:
        st.subheader("📋 Detalhamento Financeiro")
        
        # Criação da linha de total para exibição
        linha_total = pd.DataFrame({
            'Produto': ['✨ TOTAL GERAL'],
            'Custo': [total_custo],
            'Adiantamento': [df_calc['Adiantamento'].sum()],
            'Valor Parcela': [df_calc['Valor Parcela'].sum()],
            'Valor Pago': [total_pago],
            'Valor a Pagar': [total_pendente],
            'Fim': ['---']
        })

        df_visual = pd.concat([df_calc[['Produto', 'Custo', 'Adiantamento', 'Valor Parcela', 'Valor Pago', 'Valor a Pagar', 'Fim']], linha_total], ignore_index=True)
        
        # Estilização
        def highlight_total(s):
            return ['font-weight: bold; background-color: #f0f2f6' if s.Produto == '✨ TOTAL GERAL' else '' for _ in s]

        st.dataframe(
            df_visual.style.apply(highlight_total, axis=1).format({
                "Custo": formata_brl, 
                "Adiantamento": formata_brl,
                "Valor Parcela": formata_brl, 
                "Valor Pago": formata_brl, 
                "Valor a Pagar": formata_brl
            }),
            use_container_width=True,
            hide_index=True
        )

    with col_g:
        st.subheader("📊 Gráficos")
        tab1, tab2 = st.tabs(["Distribuição", "Pagas vs Pendentes"])
        
        with tab1:
            fig_pie = px.pie(df_calc, values='Custo', names='Produto', hole=0.5, color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with tab2:
            resumo = pd.DataFrame({
                'Status': ['Pago', 'Pendente'],
                'Valor': [total_pago, total_pendente]
            })
            fig_bar = px.bar(resumo, x='Status', y='Valor', color='Status', color_discrete_map={'Pago':'#28a745', 'Pendente':'#dc3545'})
            st.plotly_chart(fig_bar, use_container_width=True)

else:
    st.warning("Adicione itens no editor acima para gerar o dashboard.")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Opções")
    if st.button("🗑️ Resetar Todo o Banco"):
        if os.path.exists(DB_NOME):
            os.remove(DB_NOME)
            st.rerun()
    st.markdown("---")
    st.caption("v2.0 - Dashboard Gestão de Reforma")