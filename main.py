import streamlit as st
import gspread
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

# Configuração da página - layout wide
st.set_page_config(page_title="Jodda.ia | Dashboard de Vendas", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# --- CSS INSPIRADO NO JODDA.IA ---
st.markdown("""
<style>
    :root {
        --primary-color: #3c6fff;
        --text-color: #1a1d1f;
        --text-light: #6f767e;
        --bg-light: #f8faff;
        --white: #fff;
        --border-color: #efefef;
        --accent-green: #83bf6e;
    }
    .stApp { background-color: var(--bg-light); }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebar"] {
        background-color: var(--white);
        border-right: 1px solid var(--border-color);
        box-shadow: 2px 0 10px rgba(0,0,0,0.02);
    }
    div[data-testid="stMetric"] {
        background-color: var(--white);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0px 2px 10px rgba(0, 0, 0, 0.05);
    }
    div[data-testid="stMetricValue"] {
        color: var(--text-color);
        font-size: 32px !important;
        font-weight: 700;
        margin-top: 10px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 15px !important;
        color: var(--text-light);
        font-weight: 600;
    }
    h1, h2, h3, p, span { color: var(--text-color) !important; font-family: 'Inter', sans-serif; }
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

# --- FUNÇÃO PARA FORMATAR MOEDA ---
def formata_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# --- CONEXÃO COM O GOOGLE ---
@st.cache_data(ttl=60)
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
            cols_fin = ['Faturamento Bruto', 'Lucro Liquido', 'Margem de Contribuição', 'Custos Venda (Produto+Taxa+Frete)', 'Custo Fixo Rateado', 'Custo ADS']
            for col in cols_fin:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                    df[col] = df[col] / 100
            df = df.sort_values('Data')
        return df, True, ""
    except Exception as e:
        return pd.DataFrame(), False, str(e)

# --- CONEXÃO COM O TINY ERP ---
@st.cache_data(ttl=300) # Atualiza a cada 5 minutos
def load_tiny_produtos():
    token = st.secrets.get("TINY_TOKEN", "")
    if not token:
        return pd.DataFrame(), False, "Token não encontrado."
    
    url = "https://api.tiny.com.br/api2/produtos.pesquisa.php"
    payload = {'token': token, 'formato': 'JSON'}
    
    try:
        response = requests.post(url, data=payload)
        data = response.json()
        
        if data['retorno']['status'] == 'OK':
            produtos = data['retorno']['produtos']
            lista = []
            for p in produtos:
                prod = p['produto']
                lista.append({
                    "SKU": prod.get('codigo', '-'),
                    "Produto": prod.get('nome', 'Sem Nome'),
                    "Preço de Venda": float(prod.get('preco', 0)),
                    "Custo (Tiny)": float(prod.get('preco_custo', 0))
                })
            return pd.DataFrame(lista), True, ""
        else:
            return pd.DataFrame(), False, "Erro na API do Tiny: " + str(data['retorno'].get('erros', ''))
    except Exception as e:
        return pd.DataFrame(), False, str(e)

df, conexao_ok, erro = load_data()

# --- SIDEBAR (MENU LATERAL) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3214/3214746.png", width=50)
    st.title("Amariti ERP")
    st.markdown("---")
    menu_selecionado = st.radio("Menu Principal", ["📊 Dashboard", "📦 Gestão de Produtos (Custos)", "👗 Controle de Produção", "⚙️ Configurações"], label_visibility="collapsed")

# --- PÁGINA 1: DASHBOARD FINANCEIRO ---
if menu_selecionado == "📊 Dashboard":
    st.title("Dashboard Financeiro Amariti 👋")
    
    if conexao_ok and not df.empty:
        total_faturado = df['Faturamento Bruto'].sum()
        total_lucro = df['Lucro Liquido'].sum()
        ticket_medio = df['Faturamento Bruto'].mean()
        margem_percentual = (total_lucro / total_faturado) * 100 if total_faturado > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Total", formata_moeda(total_faturado))
        c2.metric("Total de Pedidos", f"{len(df)}")
        c3.metric("Ticket Médio", formata_moeda(ticket_medio))
        c4.metric("Margem de Lucro", f"{margem_percentual:.1f}%")
        
        st.write("---")
        st.subheader("Faturamento x Lucro Diário")
        df_dia = df.groupby('Data').agg({'Faturamento Bruto': 'sum', 'Lucro Liquido': 'sum'}).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_dia['Data'], y=df_dia['Faturamento Bruto'], name='Faturamento', marker_color='#e8efff', marker_line_width=0))
        fig.add_trace(go.Scatter(x=df_dia['Data'], y=df_dia['Lucro Liquido'], name='Lucro Líquido', mode='lines+markers', line=dict(color='#83bf6e', width=4), marker=dict(size=8)))
        fig.update_layout(plot_bgcolor='#ffffff', paper_bgcolor='#ffffff', hovermode="x unified", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#efefef'), margin=dict(l=0, r=0, t=10, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Sem dados financeiros ou erro de conexão.")

# --- PÁGINA 2: GESTÃO DE PRODUTOS E CUSTOS ---
elif menu_selecionado == "📦 Gestão de Produtos (Custos)":
    st.title("📦 Catálogo e Custos (Ao Vivo do Tiny)")
    st.markdown("Estes produtos estão sendo **puxados agora mesmo** direto do seu Tiny ERP.")
    
    with st.spinner("Conectando ao Tiny ERP para buscar seu estoque..."):
        df_tiny, tiny_ok, erro_tiny = load_tiny_produtos()
        
    if tiny_ok and not df_tiny.empty:
        # Conta os zerados
        produtos_sem_custo = len(df_tiny[df_tiny['Custo (Tiny)'] == 0])
        
        # Mostra KPIs rápidos do catálogo
        col1, col2 = st.columns(2)
        col1.metric("📦 Total de Produtos no Tiny", f"{len(df_tiny)} SKUs")
        
        if produtos_sem_custo > 0:
            col2.error(f"⚠️ Atenção: {produtos_sem_custo} produtos estão com custo ZERO no Tiny!")
        else:
            col2.success("✅ Todos os produtos possuem custo cadastrado!")
            
        st.write("---")
        
        # O BOTÃO MÁGICO DE FILTRO
        c1, c2 = st.columns([1, 3])
        with c1:
            mostrar_zerados = st.toggle("🚨 Mostrar apenas produtos SEM CUSTO", value=True if produtos_sem_custo > 0 else False)
        
        # Filtra os dados se o botão estiver ativado
        df_mostrar = df_tiny.copy()
        if mostrar_zerados:
            df_mostrar = df_mostrar[df_mostrar['Custo (Tiny)'] == 0]
            st.warning("Exibindo apenas os produtos que precisam de atualização de custo urgente no Tiny.")
            
        # Formata para dinheiro na hora de mostrar na tela
        df_mostrar['Preço de Venda'] = df_mostrar['Preço de Venda'].apply(formata_moeda)
        df_mostrar['Custo (Tiny)'] = df_mostrar['Custo (Tiny)'].apply(formata_moeda)
        
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        
        st.info("💡 Como arrumar: Abra o seu Tiny ERP, procure os SKUs listados acima e preencha o 'Preço de Custo'. Assim que salvar lá, atualize esta página e eles sumirão da lista de alertas!")
    else:
        st.error(f"🔴 Não consegui carregar os produtos do Tiny. Erro: {erro_tiny}")
