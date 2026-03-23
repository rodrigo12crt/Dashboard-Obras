import streamlit as st
import pandas as pd
import sqlite3
import os
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta
import warnings

# Silencia avisos de depreciação do Pandas
warnings.simplefilter(action='ignore', category=FutureWarning)

# --- CONFIGURAÇÃO DO BANCO DE DADOS ---
DB_NOME = "dados_rodrigo.db"

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

# --- FUNÇÕES DE APOIO ---
def formata_brl(valor):
    if pd.isna(valor) or isinstance(valor, str): return valor
    return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def prever_fim(row):
    try:
        if not row["Mes_Inicio"] or str(row["Mes_Inicio"]).strip() == "": return "---"
        ini = datetime.strptime(str(row["Mes_Inicio"]), "%Y-%m")
        qtd = int(row["Qtd_Parcelas"]) if int(row["Qtd_Parcelas"]) > 0 else 1
        fim = ini + relativedelta(months=qtd - 1)
        return fim.strftime("%b/%y")
    except: return "---"

# --- INÍCIO DO STREAMLIT ---
st.set_page_config(page_title="Gestão Venda & Reforma", layout="wide", page_icon="💰")
inicializar_db()

st.title("🏗️ Dashboard de Negócio e Obra")

# --- BARRA LATERAL (CALCULADORA DINÂMICA) ---
with st.sidebar:
    st.header("⚙️ Calculadora de Venda")
    
    v_venda = st.number_input("Valor de Venda Previsto", value=380000.0, step=5000.0)
    
    st.markdown("---")
    st.subheader("Custos de Transação")
    
    # Cálculo da Corretora por porcentagem ou valor fixo
    tipo_corretora = st.radio("Tipo de Comissão", ["Porcentagem", "Valor Fixo"], horizontal=True)
    if tipo_corretora == "Porcentagem":
        p_corretora = st.number_input("% Corretora", value=5.0, step=0.5)
        v_corretora = v_venda * (p_corretora / 100)
        st.caption(f"Valor calculado: {formata_brl(v_corretora)}")
    else:
        v_corretora = st.number_input("Valor Corretora", value=20000.0, step=500.0)

    st.markdown("---")
    st.subheader("Repasses e Dívidas")
    v_felipe = st.number_input("Parte do Felipe", value=250000.0, step=1000.0)
    v_financiamento = st.number_input("Saldo para Quitar Financiamento", value=57323.17, step=500.0)
    
    # Cálculo automático do Saldo Intermediário
    saldo_intermediario = v_venda - v_corretora - v_felipe - v_financiamento
    
    st.markdown("---")
    st.warning(f"**Disponível para Obra/Lucro:** \n\n {formata_brl(saldo_intermediario)}")
    
    if st.button("🗑️ Resetar Banco de Dados"):
        if os.path.exists(DB_NOME):
            os.remove(DB_NOME)
            st.rerun()

# --- CARGA E EDITOR ---
conn = conectar_db()
df_db = pd.read_sql_query("SELECT * FROM obras", conn)

with st.expander("📋 Editor de Itens e Custos", expanded=True):
    st.info("💡 Edite os valores abaixo para atualizar o investimento da reforma.")
    df_editavel = st.data_editor(
        df_db, 
        num_rows="dynamic", 
        width='stretch', 
        hide_index=True, 
        column_config={
            "id": None,
            "Produto": st.column_config.TextColumn("Item / Descrição", width="medium"),
            "Custo": st.column_config.NumberColumn("Custo Total", format="R$ %.2f"),
            "Qtd_Parcelas": st.column_config.NumberColumn("Nº Parcelas.", min_value=1, default=1),
            "Parcelas_Pagas": st.column_config.NumberColumn("Parcelas Pagas", min_value=0, default=0),
            "Adiantamento": st.column_config.NumberColumn("Entrada / Adiantamento", format="R$ %.2f"),
            "Mes_Inicio": st.column_config.TextColumn("Mês Inicial (YYYY-MM)")
        } 
    )

    if not df_editavel.equals(df_db):
        df_editavel.to_sql("obras", conn, if_exists="replace", index=False)
        conn.close()
        st.rerun()
conn.close()

# --- PROCESSAMENTO SEGURO ---
df_calc = df_editavel.copy()
if not df_calc.empty:
    df_calc["Custo"] = pd.to_numeric(df_calc["Custo"], errors='coerce').fillna(0.0)
    df_calc["Adiantamento"] = pd.to_numeric(df_calc["Adiantamento"], errors='coerce').fillna(0.0)
    df_calc["Qtd_Parcelas"] = pd.to_numeric(df_calc["Qtd_Parcelas"], errors='coerce').fillna(1).replace(0, 1)
    df_calc["Parcelas_Pagas"] = pd.to_numeric(df_calc["Parcelas_Pagas"], errors='coerce').fillna(0)

    df_calc["Valor Parcela"] = (df_calc["Custo"] - df_calc["Adiantamento"]) / df_calc["Qtd_Parcelas"]
    df_calc["Valor Pago"] = df_calc["Adiantamento"] + (df_calc["Parcelas_Pagas"] * df_calc["Valor Parcela"])
    df_calc["Valor a Pagar"] = df_calc["Custo"] - df_calc["Valor Pago"]
    df_calc["Última Parcela"] = df_calc.apply(prever_fim, axis=1)

    total_obra = df_calc["Custo"].sum()
    total_pago_obra = df_calc["Valor Pago"].sum()
    total_pendente_obra = df_calc["Valor a Pagar"].sum()
    perc_pago = (total_pago_obra / total_obra) if total_obra > 0 else 0

    # --- PROGRESSO ---
    cp1, cp2 = st.columns([3, 1])
    with cp1:
        st.write(f"**Progresso Financeiro da Obra:** {perc_pago:.1%}")
        st.progress(perc_pago)
    with cp2:
        datas_validas = df_calc[df_calc["Última Parcela"] != "---"]["Última Parcela"]
        st.write(f"**Fim das parcelas:** `{datas_validas.max() if not datas_validas.empty else 'N/A'}`")

    st.markdown("---")

    # --- MÉTRICAS DE NEGÓCIO ---
    saldo_final = saldo_intermediario - total_obra 

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Venda (Bruto)", formata_brl(v_venda))
    m2.metric("Saldo Intermediário", formata_brl(saldo_intermediario), help="Venda - Corretora - Felipe - Financiamento")
    m3.metric("Investimento na Obra", formata_brl(total_obra), delta=f"-{formata_brl(total_obra)}", delta_color="inverse")
    m4.metric("LUCRO FINAL", formata_brl(saldo_final), delta=f"{(saldo_final/v_venda*100):.1f}% margem" if v_venda > 0 else None)

    st.markdown("---")

    # --- VISUALIZAÇÃO ---
    col_t, col_g = st.columns([2.3, 1])
    with col_t:
        st.subheader("📋 Resumo de Pagamentos")
        linha_total = pd.DataFrame({
            'Produto': ['✨ TOTAL GERAL'], 'Custo': [total_obra], 'Adiantamento': [df_calc['Adiantamento'].sum()],
            'Valor Pago': [total_pago_obra], 'Valor a Pagar': [total_pendente_obra], 'Última Parcela': ['---']
        })
        df_visual = pd.concat([df_calc[['Produto', 'Custo', 'Adiantamento', 'Valor Pago', 'Valor a Pagar', 'Última Parcela']], linha_total], ignore_index=True)
        st.dataframe(df_visual.style.apply(lambda x: ['font-weight: bold; background-color: #f1f3f6' if x.Produto == '✨ TOTAL GERAL' else '' for _ in x], axis=1).format({"Custo": formata_brl, "Adiantamento": formata_brl, "Valor Pago": formata_brl, "Valor a Pagar": formata_brl}), use_container_width=True, hide_index=True)

    with col_g:
        st.subheader("📊 Gráficos")
        tab1, tab2 = st.tabs(["Distribuição", "Status"])
        with tab1:
            fig_p = px.pie(df_calc[df_calc["Custo"] > 0], values='Custo', names='Produto', hole=0.5)
            st.plotly_chart(fig_p, use_container_width=True)
        with tab2:
            fig_b = px.bar(x=['Pago', 'Pendente'], y=[total_pago_obra, total_pendente_obra], color=['Pago', 'Pendente'], color_discrete_map={'Pago':'#28a745', 'Pendente':'#dc3545'})
            st.plotly_chart(fig_b, use_container_width=True)

else:
    st.warning("Adicione itens para calcular o lucro.")