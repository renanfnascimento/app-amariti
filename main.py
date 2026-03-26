import streamlit as st
import gspread
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

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
    
    # Tratamento de Dados
    if not df.empty:
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        # Colunas de Dinheiro
        cols_fin = [
            'Faturamento Bruto', 
            'Lucro Liquido', 
            'Margem de Contribuição', 
            'Custos Venda (Produto+Taxa+Frete)', 
            'Custo Fixo Rateado',
            'Custo ADS'
        ]
        
        for col in cols_fin:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                df[col] = df[col] / 100
        
        df = df.sort_values('Data')
    
    conexao_ok = True
except Exception as e:
    conexao_ok = False
    erro = str(e)

# --- INTERFACE DO APP ---
st.title("🚀 Sistema de Gestão - Amariti")

def formata_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

if conexao_ok:
    aba1, aba2, aba3 = st.tabs(["📊 Financeiro", "👗 PCP / Costureiras", "⚙️ Custos e Impostos"])

    with aba1:
        if not df.empty:
            # 1. LINHA DE MÉTRICAS (Totais do Mês/Período)
            total_faturado = df['Faturamento Bruto'].sum()
            total_lucro = df['Lucro Liquido'].sum()
            margem_percentual = (total_lucro / total_faturado) * 100 if total_faturado > 0 else 0
            
            c1, c2, c3 = st.columns(3)
            c1.metric("Faturamento Bruto", formata_moeda(total_faturado))
            c2.metric("Lucro Líquido", formata_moeda(total_lucro))
            c3.metric("Margem de Lucro (%)", f"{margem_percentual:.1f}%")
            
            st.divider()

            # --- O SEGREDO DO FECHAMENTO DIÁRIO ---
            st.subheader("🗓️ Fechamento Diário (Lucro x Faturamento)")
            
            # Agrupando tudo por dia para bater com o seu manual
            df_dia = df.groupby('Data').agg({
                'Faturamento Bruto': 'sum',
                'Lucro Liquido': 'sum',
                'Custos Venda (Produto+Taxa+Frete)': 'sum',
                'Custo Fixo Rateado': 'sum'
            }).reset_index()
            
            # Criando um gráfico duplo: Barras para faturamento, Linha para Lucro
            fig = go.Figure()
            fig.add_trace(go.Bar(x=df_dia['Data'], y=df_dia['Faturamento Bruto'], name='Faturamento Bruto', marker_color='#A0B2C6'))
            fig.add_trace(go.Scatter(x=df_dia['Data'], y=df_dia['Lucro Liquido'], name='Lucro Líquido', mode='lines+markers+text',
                                     text=df_dia['Lucro Liquido'].apply(lambda x: f"R$ {x:,.0f}".replace(',','.')),
                                     textposition="top center", marker_color='#00CC96', line=dict(width=3)))
            
            fig.update_layout(title="Comparativo Faturamento vs. Lucro por Dia", hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)

            # Tabela Resumo do Fechamento Diário
            st.write("### 📋 Resumo por Dia (Bata os valores aqui)")
            df_dia_tabela = df_dia.copy()
            df_dia_tabela['Data'] = df_dia_tabela['Data'].dt.strftime('%d/%m/%Y')
            
            # Formatando as colunas para R$
            for col in ['Faturamento Bruto', 'Custos Venda (Produto+Taxa+Frete)', 'Custo Fixo Rateado', 'Lucro Liquido']:
                df_dia_tabela[col] = df_dia_tabela[col].apply(formata_moeda)
                
            st.dataframe(df_dia_tabela, use_container_width=True, hide_index=True)

            # 3. TABELA DE DETALHES GERAIS
            with st.expander("🔍 Ver Detalhes de Cada Pedido Individual"):
                df_mostrar = df.copy()
                df_mostrar['Data'] = df_mostrar['Data'].dt.strftime('%d/%m/%Y')
                for col in cols_fin:
                    if col in df_mostrar.columns:
                        df_mostrar[col] = df_mostrar[col].apply(formata_moeda)
                st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
                
        else:
            st.warning("Nenhum dado financeiro encontrado ainda.")

else:
    st.error(f"🔴 Erro de Conexão: {erro}")

with aba2:
    st.info("Aqui entrará o controle de produção das costureiras.")

with aba3:
    st.info("Aqui você poderá cadastrar os custos fixos e impostos.")
