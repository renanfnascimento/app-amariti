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
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        # Colunas de Dinheiro da Amariti
        cols_fin = [
            'Faturamento Bruto', 
            'Lucro Liquido', 
            'Margem de Contribuição', 
            'Custos Venda (Produto+Taxa+Frete)', 
            'Custo Fixo Rateado'
        ]
        
        for col in cols_fin:
            if col in df.columns:
                # Transforma em número e DIVIDE POR 100 para colocar a vírgula no lugar certo!
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                df[col] = df[col] / 100
        
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
            
            # Função para formatar o dinheiro no padrão R$ Brasileiro
            def formata_moeda(valor):
                return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Faturamento Bruto Total", formata_moeda(total_faturado))
            c2.metric("Lucro Líquido Total", formata_moeda(total_lucro))
            c3.metric("Ticket Médio", formata_moeda(ticket_medio))
            
            st.divider()

            # 2. GRÁFICO DE FATURAMENTO POR DIA
            st.subheader("📈 Evolução de Faturamento (Vendas por Dia)")
            df_dia = df.groupby('Data')['Faturamento Bruto'].sum().reset_index()
            fig = px.bar(df_dia, x='Data', y='Faturamento Bruto', 
                         title="Faturamento Bruto por Dia",
                         labels={'Faturamento Bruto': 'Valor (R$)', 'Data': 'Data da Venda'},
                         text_auto='.2f', # Mostra o valor em cima da barra
                         color_discrete_sequence=['#00CC96'])
            st.plotly_chart(fig, use_container_width=True)

            # 3. TABELA DE DETALHES
            with st.expander("🔍 Ver Detalhes de Todos os Registros"):
                # Formata a tabela para ficar bonita
                df_mostrar = df.copy()
                # Transforma a data de volta pro formato Brasileiro na hora de exibir
                df_mostrar['Data'] = df_mostrar['Data'].dt.strftime('%d/%m/%Y')
                st.dataframe(df_mostrar, use_container_width=True)
        else:
            st.warning("A aba 'BD_Financeiro' está vazia. Comece a vender para ver os gráficos!")

else:
    st.error(f"🔴 Erro de Conexão: {erro}")

with aba2:
    st.info("Aqui entrará o controle de produção das costureiras.")

with aba3:
    st.info("Aqui você poderá cadastrar os custos fixos e impostos.")
