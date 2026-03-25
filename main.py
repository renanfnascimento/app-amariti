import streamlit as st
import gspread
import json
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="ERP Amariti", page_icon="🚀", layout="wide")

# --- CONEXÃO COM O GOOGLE ---
try:
    credenciais_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    gc = gspread.service_account_from_dict(credenciais_dict)
    ID_DA_PLANILHA = "1HaqFImRnQgIrL-6BlnsifIyUwSVRngaUujQAsqTKOZY"
    planilha = gc.open_by_key(ID_DA_PLANILHA)
    aba_fin = planilha.worksheet("BD_Financeiro")
    
    dados = aba_fin.get_all_records()
    df = pd.DataFrame(dados)
    
    # Tratamento de Dados (Convertendo números e datas)
    if not df.empty:
        # Tenta converter a coluna Data
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        # Garante que as colunas financeiras sejam números
        cols_fin = ['Faturamento Bruto', 'Lucro Liquido', 'Margem de Contribuição']
        for col in cols_fin:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        df = df.sort_values('Data')
    
    conexao_ok = True
except Exception as e:
    conexao_ok = False
    erro = str(e)

# --- INTERFACE DO APP ---
st.title("🚀 Sistema de Gestão - Amariti")

if conexao_ok:
    st.success("🟢 Painel de Controle Ativo!")
    
    aba1, aba2, aba3 = st.tabs(["📊 Financeiro", "👗 PCP / Costureiras", "⚙️ Custos e Impostos"])

    with aba1:
        if not df.empty:
            # 1. LINHA DE MÉTRICAS (Os cards lá no topo)
            total_faturado = df['Faturamento Bruto'].sum()
            total_lucro = df['Lucro Liquido'].sum()
            ticket_medio = df['Faturamento Bruto'].mean()
            
            c1, c2, c3 = st.columns(3)
            # Formatação para Moeda Brasileira (R$)
            c1.metric("Faturamento Bruto Total", f"R$ {total_faturado:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
            c2.metric("Lucro Líquido Total", f"R$ {total_lucro:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
            c3.metric("Ticket Médio", f"R$ {ticket_medio:,.2f}".replace(",", "v").replace(".", ",").replace("v", "."))
            
            st.divider()

            # 2. GRÁFICO DE FATURAMENTO POR DIA
            st.subheader("📈 Evolução de Faturamento (Vendas por Dia)")
            df_dia = df.groupby('Data')['Faturamento Bruto'].sum().reset_index()
            fig = px.bar(df_dia, x='Data', y='Faturamento Bruto', 
                         title="Faturamento Bruto por Dia",
                         labels={'Faturamento Bruto': 'Valor (R$)', 'Data': 'Dia'},
                         color_discrete_sequence=['#00CC96'])
            st.plotly_chart(fig, use_container_width=True)

            # 3. TABELA DE DETALHES
            with st.expander("🔍 Ver Detalhes de Todos os Registros"):
                st.dataframe(df, use_container_width=True)
        else:
            st.warning("A aba 'BD_Financeiro' está vazia. Comece a vender para ver os gráficos!")

else:
    st.error(f"🔴 Erro de Conexão: {erro}")

with aba2:
    st.info("Aqui entrará o controle de produção das costureiras.")
