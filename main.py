import streamlit as st
import gspread
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Configuração da página - layout wide
st.set_page_config(page_title="Jodda.ia | Dashboard de Vendas", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# --- CSS INSPIRADO NO JODDA.IA ---
st.markdown("""
<style>
    /* Cores padrão do Jodda.ia */
    :root {
        --primary-color: #3c6fff;
        --text-color: #1a1d1f;
        --text-light: #6f767e;
        --bg-light: #f8faff;
        --white: #fff;
        --border-color: #efefef;
        --accent-green: #83bf6e;
    }

    /* Fundo da tela inteira e Esconder Menu Padrão do Streamlit */
    .stApp { background-color: var(--bg-light); }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}

    /* Estilo da Sidebar (Menu Lateral) */
    [data-testid="stSidebar"] {
        background-color: var(--white);
        border-right: 1px solid var(--border-color);
        box-shadow: 2px 0 10px rgba(0,0,0,0.02);
    }
    
    /* Estilo dos Cartões de Métricas (Brancos, sombra leve, ícones azuis) */
    div[data-testid="stMetric"] {
        background-color: var(--white);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.05);
    }
    
    /* Cor e tamanho dos Valores ($) */
    div[data-testid="stMetricValue"] {
        color: var(--text-color);
        font-size: 32px !important;
        font-weight: 700;
        margin-top: 10px;
    }
    
    /* Cor e tamanho dos Títulos dos cartões */
    div[data-testid="stMetricLabel"] {
        font-size: 15px !important;
        color: var(--text-light);
        font-weight: 600;
    }
    
    /* Deixar todos os textos com a fonte/cor do Jodda */
    h1, h2, h3, p, span { color: var(--text-color) !important; font-family: 'Inter', sans-serif; }
    
    /* Cards de gráficos */
    .element-container [data-testid="stPlotlyChart"] {
        background-color: var(--white);
        border-radius: 16px;
        border: 1px solid var(--border-color);
        box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.05);
        padding: 20px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- CONEXÃO COM O GOOGLE ---
@st.cache_data(ttl=60) # Cache para deixar o app rápido
def load_data():
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
            
            # Tratamento de colunas financeiras (Dividindo por 100 para acertar centavos)
            cols_fin = ['Faturamento Bruto', 'Lucro Liquido', 'Margem de Contribuição', 'Custos Venda (Produto+Taxa+Frete)', 'Custo Fixo Rateado', 'Custo ADS']
            for col in cols_fin:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                    df[col] = df[col] / 100
            
            df = df.sort_values('Data')
        
        return df, True, ""
    except Exception as e:
        return pd.DataFrame(), False, str(e)

df, conexao_ok, erro = load_data()

# --- FUNÇÃO PARA FORMATAR MOEDA ---
def formata_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- SIDEBAR (MENU LATERAL ESTILO JODDA.IA) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3214/3214746.png", width=50) # Logo provisória
    st.title("Amariti ERP")
    st.markdown("---")
    
    # Criando a navegação
    menu_selecionado = st.radio(
        "Menu Principal",
        ["📊 Dashboard", "📦 Gestão de Produtos (Custos)", "👗 Controle de Produção", "⚙️ Configurações"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.info("💡 Fale com o suporte no WhatsApp")

# --- LÓGICA DE NAVEGAÇÃO ENTRE PÁGINAS ---

# PÁGINA 1: DASHBOARD FINANCEIRO (Como era antes, mas no estilo Jodda)
if menu_selecionado == "📊 Dashboard":
    
    st.title("Olá, Renan Ferreira do Nascimento 👋")
    st.markdown("Bem-vindo ao seu **Dashboard de Vendas**.")
    st.write("") 

    if conexao_ok:
        if not df.empty:
            # 1. LINHA DE MÉTRICAS (CARTÕES JODDA)
            total_faturado = df['Faturamento Bruto'].sum()
            total_lucro = df['Lucro Liquido'].sum()
            ticket_medio = df['Faturamento Bruto'].mean()
            margem_percentual = (total_lucro / total_faturado) * 100 if total_faturado > 0 else 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Faturamento Total", formata_moeda(total_faturado))
            c2.metric("Total de Pedidos", f"{len(df)}")
            c3.metric("Ticket Médio", formata_moeda(ticket_medio))
            c4.metric("Margem de Lucro Bruto", f"{margem_percentual:.1f}%")
            
            # 2. SEÇÃO DE ADS
            st.write("### 📢 Investimento em Anúncios (ADS)")
            ca1, ca2 = st.columns(2)
            ca1.metric("Custo Total ADS (Mês)", "R$ 0,00") # Vamos puxar isso no futuro
            ca2.metric("Lucro Líquido Pós ADS", formata_moeda(total_lucro))
            
            # 3. GRÁFICO (LINHAS E BARRAS LIMPAS TIPO JODDA)
            st.write("---")
            st.subheader("Faturamento x Lucro Diário")
            
            df_dia = df.groupby('Data').agg({'Faturamento Bruto': 'sum', 'Lucro Liquido': 'sum'}).reset_index()
            
            fig = go.Figure()
            # Faturamento em barras (Azul Jodda)
            fig.add_trace(go.Bar(x=df_dia['Data'], y=df_dia['Faturamento Bruto'], name='Faturamento', marker_color='#e8efff', marker_line_width=0))
            # Lucro em linha de destaque (Verde Jodda)
            fig.add_trace(go.Scatter(x=df_dia['Data'], y=df_dia['Lucro Liquido'], name='Lucro Líquido', mode='lines+markers', line=dict(color='#83bf6e', width=4), marker=dict(size=8)))
            
            fig.update_layout(
                plot_bgcolor='#ffffff',
                paper_bgcolor='#ffffff',
                hovermode="x unified",
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=True, gridcolor='#efefef', gridwidth=1),
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.warning("Nenhum dado encontrado no momento.")
    else:
        st.error(f"🔴 Erro de Conexão: {erro}")


# PÁGINA 2: GESTÃO DE PRODUTOS E CUSTOS (O QUE VOCÊ PEDIU AGORA!)
elif menu_selecionado == "📦 Gestão de Produtos (Custos)":
    st.title("📦 Gestão de Produtos e Custos")
    st.markdown("Aqui você cadastra o Custo de Produção (Tecido, aviamentos, mão de obra) de cada produto para calcularmos o **Lucro Real**.")
    
    st.info("💡 Em breve: Nesta tela, o sistema vai ler os produtos vendidos na aba 'BD_Financeiro' e pedir para você preencher o custo de cada um deles. Quando você salvar, o aplicativo vai descontar esse custo automaticamente do Faturamento do Dashboard.")
    
    # Criando uma tabela falsa por enquanto só para você ver o visual
    st.write("### Produtos com Custos a Definir")
    
    df_exemplo = pd.DataFrame({
        "SKU": ["AMR-VEST-PRETO", "AMR-SAIA-CURTA", "AMR-BLUSA-TRICOT"],
        "Produto": ["Vestido Longo Preto Amariti", "Saia Curta Amariti", "Blusa de Tricot Gola V"],
        "Faturamento Bruto (Ref)": ["R$ 159,90", "R$ 89,90", "R$ 120,00"],
        "Custo Cadastrado": ["❌ Sem Custo", "❌ Sem Custo", "❌ Sem Custo"]
    })
    
    st.dataframe(df_exemplo, use_container_width=True, hide_index=True)
    
    st.button("Cadastrar Novo Custo de Produto", type="primary")


# PÁGINA 3 E 4: PLACEHOLDERS
elif menu_selecionado == "👗 Controle de Produção":
    st.title("👗 Controle de Produção (PCP)")
    st.markdown("Aqui será a tela da sua **Fábrica**.")
    st.info("A costureira poderá clicar em um botão para dar baixa nas peças que ela costurou hoje, gerando um histórico de produtividade.")

elif menu_selecionado == "⚙️ Configurações":
    st.title("⚙️ Configurações")
    st.markdown("Ajustes de Impostos, Custos Fixos Mensais (Aluguel, Luz, etc) e Conexões (Mercado Livre e Shopee).")
