import streamlit as st
import gspread
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página - layout wide
st.set_page_config(page_title="ERP Amariti", page_icon="🚀", layout="wide")

# --- CSS INSPIRADO NO QUICKBOOKS ---
st.markdown("""
<style>
    /* Fundo da tela inteira em um cinza super claro (padrão de dashboards) */
    .stApp {
        background-color: #F4F5F8;
    }
    
    /* Estilo dos Cartões de Métricas (Brancos, sombra leve, topo verde) */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E3E5E8;
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.05);
        border-top: 4px solid #2CA01C; /* Verde QuickBooks */
    }
    
    /* Cor e tamanho dos Valores ($) */
    div[data-testid="stMetricValue"] {
        color: #393A3D; /* Cinza escuro/Quase preto */
        font-size: 32px !important;
        font-weight: 700;
    }
    
    /* Cor e tamanho dos Títulos dos cartões */
    div[data-testid="stMetricLabel"] {
        font-size: 15px !important;
        color: #6B6C72; /* Cinza médio */
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* Ajustes para textos gerais ficarem escuros no fundo claro */
    h1, h2, h3, p, span {
        color: #393A3D !important;
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
st.title("Fluxo de Caixa - Amariti")
st.markdown("Visão geral das finanças e performance de vendas.")
st.write("") 

if conexao_ok:
    aba1, aba2, aba3 = st.tabs(["📊 Visão Geral", "👗 Produção", "⚙️ Configurações"])

    with aba1:
        if not df.empty:
            # 1. LINHA DE MÉTRICAS (CARTÕES QUICKBOOKS)
            total_faturado = df['Faturamento Bruto'].sum()
            total_lucro = df['Lucro Liquido'].sum()
            margem_percentual = (total_lucro / total_faturado) * 100 if total_faturado > 0 else 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Faturamento Bruto", formata_moeda(total_faturado))
            c2.metric("Despesas e Custos", formata_moeda(total_faturado - total_lucro))
            c3.metric("Lucro Líquido", formata_moeda(total_lucro))
            c4.metric("Margem de Lucro", f"{margem_percentual:.1f}%")
            
            st.write("")
            st.write("")

            # 2. GRÁFICO CLEAN (PADRÃO QUICKBOOKS)
            st.subheader("Faturamento x Lucro (Diário)")
            
            df_dia = df.groupby('Data').agg({'Faturamento Bruto': 'sum', 'Lucro Liquido': 'sum'}).reset_index()
            
            fig = go.Figure()
            # Faturamento em barras cinza claro
            fig.add_trace(go.Bar(x=df_dia['Data'], y=df_dia['Faturamento Bruto'], name='Faturamento', marker_color='#E3E5E8', marker_line_width=0))
            # Lucro em linha Verde QuickBooks
            fig.add_trace(go.Scatter(x=df_dia['Data'], y=df_dia['Lucro Liquido'], name='Lucro', mode='lines+markers', line=dict(color='#2CA01C', width=4), marker=dict(size=8, color='#2CA01C')))
            
            # Fundo branco e limpo para o gráfico
            fig.update_layout(
                plot_bgcolor='#FFFFFF',
                paper_bgcolor='#FFFFFF',
                hovermode="x unified",
                font=dict(color='#393A3D'),
                xaxis=dict(showgrid=False, linecolor='#E3E5E8'),
                yaxis=dict(showgrid=True, gridcolor='#F4F5F8', linecolor='#E3E5E8'),
                margin=dict(l=0, r=0, t=30, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

            st.write("---")

            # 3. TABELAS DE CONFERÊNCIA
            c1, c2 = st.columns(2)
            with c1:
                with st.expander("Conferência do Fechamento Diário"):
                    df_dia_tabela = df.groupby('Data').agg({'Faturamento Bruto': 'sum', 'Custos Venda (Produto+Taxa+Frete)': 'sum', 'Custo Fixo Rateado': 'sum', 'Lucro Liquido': 'sum'}).reset_index()
                    df_dia_tabela['Data'] = df_dia_tabela['Data'].dt.strftime('%d/%m/%Y')
                    for col in ['Faturamento Bruto', 'Custos Venda (Produto+Taxa+Frete)', 'Custo Fixo Rateado', 'Lucro Liquido']:
                        df_dia_tabela[col] = df_dia_tabela[col].apply(formata_moeda)
                    st.dataframe(df_dia_tabela, use_container_width=True, hide_index=True)
            
            with c2:
                with st.expander("Lista Completa de Pedidos"):
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
