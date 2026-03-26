import streamlit as st
import gspread
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página - layout="wide" para usar a tela toda
st.set_page_config(page_title="ERP Amariti", page_icon="🚀", layout="wide")

# --- CSS MÁGICO PARA TIRAR A CARA DE EXCEL ---
st.markdown("""
<style>
    /* Estilo dos Cartões de Métricas (Faturamento, Lucro, etc) */
    div[data-testid="stMetric"] {
        background-color: #1E2130;
        border-radius: 10px;
        padding: 15px 20px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.2);
        border-left: 5px solid #00CC96;
    }
    div[data-testid="stMetricValue"] {
        color: #00CC96;
        font-size: 28px !important;
        font-weight: 800;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 16px !important;
        color: #A0B2C6;
        font-weight: 500;
    }
    /* Ocultar barra lateral se estiver vazia e dar respiro na tela */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM O GOOGLE ---
try:
    credenciais_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    gc = gspread.service_account_from_dict(credenciais_dict)
    ID_DA_PLANILHA = "1HaqFImRnQgIrL-6BlnsifIyUwSVRngaUujQAsqTKOZY"
    planilha = gc.open_by_key(ID_DA_PLANILHA)
    aba_fin = planilha.worksheet("BD_Financeiro")
    
    dados = aba_fin.get_all_records()
    df = pd.DataFrame(dados)
    
    if not df.empty:
        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, errors='coerce')
        
        cols_fin = ['Faturamento Bruto', 'Lucro Liquido', 'Margem de Contribuição', 'Custos Venda (Produto+Taxa+Frete)', 'Custo Fixo Rateado', 'Custo ADS']
        for col in cols_fin:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                df[col] = df[col] / 100
        
        df = df.sort_values('Data')
    
    conexao_ok = True
except Exception as e:
    conexao_ok = False
    erro = str(e)

# --- FUNÇÃO PARA FORMATAR MOEDA ---
def formata_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- INTERFACE DO APP ---
st.title("🚀 Dashboard Financeiro - Amariti")
st.markdown("Acompanhamento de vendas, custos e lucros em tempo real.")
st.write("") # Espaço em branco

if conexao_ok:
    aba1, aba2, aba3 = st.tabs(["📊 Visão Geral (Financeiro)", "👗 PCP / Costureiras", "⚙️ Cadastros e Custos"])

    with aba1:
        if not df.empty:
            # 1. LINHA DE MÉTRICAS (CARTÕES ESTILIZADOS)
            total_faturado = df['Faturamento Bruto'].sum()
            total_lucro = df['Lucro Liquido'].sum()
            margem_percentual = (total_lucro / total_faturado) * 100 if total_faturado > 0 else 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 Faturamento Bruto", formata_moeda(total_faturado))
            c2.metric("💸 Custos Totais", formata_moeda(total_faturado - total_lucro))
            c3.metric("🤑 Lucro Líquido", formata_moeda(total_lucro))
            c4.metric("📈 Margem de Lucro", f"{margem_percentual:.1f}%")
            
            st.write("---")

            # 2. GRÁFICO PREMIUM (LINHAS E BARRAS LIMPAS)
            st.subheader("🗓️ Evolução do Faturamento e Lucro")
            
            df_dia = df.groupby('Data').agg({'Faturamento Bruto': 'sum', 'Lucro Liquido': 'sum'}).reset_index()
            
            fig = go.Figure()
            # Faturamento em barras elegantes
            fig.add_trace(go.Bar(x=df_dia['Data'], y=df_dia['Faturamento Bruto'], name='Faturamento', marker_color='#2A3644', marker_line_width=0))
            # Lucro em linha de destaque
            fig.add_trace(go.Scatter(x=df_dia['Data'], y=df_dia['Lucro Liquido'], name='Lucro', mode='lines+markers', line=dict(color='#00CC96', width=4), marker=dict(size=8)))
            
            # Limpando as grades de fundo para ficar mais moderno
            fig.update_layout(
                plot_bgcolor='rgba(0,0,0,0)',
                paper_bgcolor='rgba(0,0,0,0)',
                hovermode="x unified",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#2E303E', gridwidth=1),
                margin=dict(l=0, r=0, t=30, b=0)
            )
            st.plotly_chart(fig, use_container_width=True)

            st.write("---")

            # 3. TABELAS DE CONFERÊNCIA (Ocultas por padrão para deixar a tela limpa)
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("📊 Conferência do Fechamento Diário"):
                    df_dia_tabela = df.groupby('Data').agg({'Faturamento Bruto': 'sum', 'Custos Venda (Produto+Taxa+Frete)': 'sum', 'Custo Fixo Rateado': 'sum', 'Lucro Liquido': 'sum'}).reset_index()
                    df_dia_tabela['Data'] = df_dia_tabela['Data'].dt.strftime('%d/%m/%Y')
                    for col in ['Faturamento Bruto', 'Custos Venda (Produto+Taxa+Frete)', 'Custo Fixo Rateado', 'Lucro Liquido']:
                        df_dia_tabela[col] = df_dia_tabela[col].apply(formata_moeda)
                    st.dataframe(df_dia_tabela, use_container_width=True, hide_index=True)
            
            with c2:
                with st.expander("📋 Ver Lista Completa de Pedidos"):
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
    st.info("O módulo de produção das costureiras ficará aqui.")

with aba3:
    st.info("Tela para configuração de Custos Fixos e Impostos.")
