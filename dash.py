import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime
from dateutil.relativedelta import relativedelta
import warnings 

ARQUIVO_DADOS = "dados_reforma.csv"

# Silencia o aviso de FutureWarning para o terminal ficar limpo
warnings.simplefilter(action='ignore', category=FutureWarning)

# Função para formatar moeda brasileira R$ 4.400,00
def formata_brl(valor):
    if pd.isna(valor): return "R$ 0,00"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def criar_dados_iniciais():
    data = {
        "Produto": ["Móveis", "Cabeceira", "Piso", "Pedreiro", "Pedra", "Elétrica", "Diversos"],
        "Custo R$": [22000.0, 1200.0, 5909.01, 8000.0, 7500.0, 0.0, 100.0],
        "Qtd Parcelas": [6, 10, 10, 1, 10, 1, 1],
        "Parcelas Pagas": [0, 0, 0, 0, 0, 0, 0],
        "Adiantamento": [4400.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        "Mês Início": ["2026-04", "2026-04", "2026-04", "2026-04", "2026-04", "2026-04", "2026-04"]
    }
    return pd.DataFrame(data)

st.set_page_config(page_title="Gestão de Venda e Reforma", layout="wide")

if os.path.exists(ARQUIVO_DADOS):
    if 'df_obras' not in st.session_state:
        st.session_state.df_obras = pd.read_csv(ARQUIVO_DADOS)
else:
    st.session_state.df_obras = criar_dados_iniciais()

st.title("🏗️ Dashboard de Venda e Reforma")

# --- BARRA LATERAL ---
st.sidebar.header("💰 Valores da Transação")
v_venda = st.sidebar.number_input("Valor Venda", value=380000.0)
v_felipe = st.sidebar.number_input("Felipe", value=250000.0)
v_corretora = st.sidebar.number_input("Corretora", value=20000.0)
v_financiamento = st.sidebar.number_input("Financiamento", value=57323.17)

# --- EDITOR DA OBRA ---
st.subheader("🛠️ Detalhamento da Obra")
df_editavel = st.data_editor(st.session_state.df_obras, num_rows="dynamic", width='stretch')

if not df_editavel.equals(st.session_state.df_obras):
    st.session_state.df_obras = df_editavel
    df_editavel.to_csv(ARQUIVO_DADOS, index=False)
    st.rerun()

# --- CÁLCULOS ---
df_calc = df_editavel.copy()
df_calc["Valor Parcela"] = (df_calc["Custo R$"] - df_calc["Adiantamento"]) / df_calc["Qtd Parcelas"]
df_calc["Valor Pago"] = df_calc["Adiantamento"] + (df_calc["Parcelas Pagas"] * df_calc["Valor Parcela"])
df_calc["Valor a Pagar"] = df_calc["Custo R$"] - df_calc["Valor Pago"]

# Previsão de Término
def prever_fim(row):
    try:
        ini = datetime.strptime(row["Mês Início"], "%Y-%m")
        fim = ini + relativedelta(months=int(row["Qtd Parcelas"]) - 1)
        return fim.strftime("%b/%y")
    except: return "---"
df_calc["Última Parcela"] = df_calc.apply(prever_fim, axis=1)

# --- ESTILIZAÇÃO DE FONTES E CORES ---
def estilizar_df(df):
    # Criar DataFrame de estilos (vazio por padrão)
    estilo = pd.DataFrame('', index=df.index, columns=df.columns)
    
    # Aplicar cores nas fontes das colunas específicas
    estilo['Valor Pago'] = 'color: #28a745; font-weight: bold;'
    estilo['Valor a Pagar'] = 'color: #dc3545; font-weight: bold;'
    
    # Aplicar destaque de linha para itens quitados
    for i in range(len(df)):
        if df.iloc[i]["Valor a Pagar"] <= 0 and df.iloc[i]["Custo R$"] > 0:
            estilo.iloc[i, :] = 'background-color: #d4edda; color: #155724; font-weight: bold;'
            
    return estilo

# --- EXIBIÇÃO ---
col_t, col_g = st.columns([2, 1])

with col_t:
    st.dataframe(
        df_calc.style.format({
            "Custo R$": formata_brl, 
            "Valor Parcela": formata_brl, 
            "Valor Pago": formata_brl, 
            "Valor a Pagar": formata_brl, 
            "Adiantamento": formata_brl
        }).apply(estilizar_df, axis=None), 
        width='stretch'
    )

with col_g:
    fig = px.pie(df_calc, values='Custo R$', names='Produto', title="Distribuição de Gastos", hole=0.4)
    st.plotly_chart(fig, theme="streamlit")

# --- RESUMO FINANCEIRO ---
total_pago_obra = df_calc["Valor Pago"].sum()
saldo_intermediario = v_venda - v_corretora - v_felipe - v_financiamento
saldo_final = saldo_intermediario - total_pago_obra

st.divider()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Valor Venda", formata_brl(v_venda))
c2.write(f"**Saídas (Felipe + Corretora + Financiamento)**\n\n :red[- {formata_brl(v_felipe + v_corretora + v_financiamento)}]")
c3.write(f"**Saldo Intermediário**\n\n :blue[{formata_brl(saldo_intermediario)}]")
c4.write(f"**Pago na Obra**\n\n :red[- {formata_brl(total_pago_obra)}]")
cor_f = "blue" if saldo_final >= 0 else "red"
c5.write(f"**Saldo Final**\n\n :{cor_f}[{formata_brl(saldo_final)}]")

if st.sidebar.button("🗑️ Resetar Tudo"):
    if os.path.exists(ARQUIVO_DADOS): os.remove(ARQUIVO_DADOS)
    st.rerun()