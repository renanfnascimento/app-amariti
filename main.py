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
        
        # 1. Puxando a aba do Financeiro Geral
        aba_fin = planilha.worksheet("BD_Financeiro")
        df_fin = pd.DataFrame(aba_fin.get_all_records())
        if not df_fin.empty:
            df_fin['Data'] = pd.to_datetime(df_fin['Data'], dayfirst=True, errors='coerce')
            cols_fin = ['Faturamento Bruto', 'Lucro Liquido', 'Margem de Contribuição', 'Custos Venda (Produto+Taxa+Frete)', 'Custo Fixo Rateado', 'Custo ADS']
            for col in cols_fin:
                if col in df_fin.columns:
                    df_fin[col] = pd.to_numeric(df_fin[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                    df_fin[col] = df_fin[col] / 100
            df_fin = df_fin.sort_values('Data')

        # 2. Puxando a nova aba de Itens Vendidos
        try:
            aba_itens = planilha.worksheet("BD_Itens")
            df_itens = pd.DataFrame(aba_itens.get_all_records())
            if not df_itens.empty:
                # Tratando os números de quantidade e preço
                df_itens['Quantidade'] = pd.to_numeric(df_itens.get('Quantidade', 0), errors='coerce').fillna(0)
                df_itens['Preco_Unitario'] = pd.to_numeric(df_itens.get('Preco_Unitario', 0).astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        except Exception as e:
            df_itens = pd.DataFrame() # Se a aba estiver vazia ou com erro, cria tabela em branco
            
        return df_fin, df_itens, True, ""
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), False, str(e)

# --- CONEXÃO COM O TINY ERP ---
@st.cache_data(ttl=300)
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
                    "SKU": str(prod.get('codigo', '-')), # Força ser texto para não dar erro
                    "Produto": prod.get('nome', 'Sem Nome'),
                    "Preço de Venda": float(prod.get('preco', 0)),
                    "Custo (Tiny)": float(prod.get('preco_custo', 0))
                })
            return pd.DataFrame(lista), True, ""
        else:
            return pd.DataFrame(), False, "Erro na API do Tiny: " + str(data['retorno'].get('erros', ''))
    except Exception as e:
        return pd.DataFrame(), False, str(e)

# Carregando as três fontes de dados
df_fin, df_itens, conexao_ok, erro = load_data()
df_tiny, tiny_ok, erro_tiny = load_tiny_produtos()

# --- SIDEBAR (MENU LATERAL) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3214/3214746.png", width=50)
    st.title("Amariti ERP")
    st.markdown("---")
    menu_selecionado = st.radio("Menu Principal", ["📊 Dashboard", "📦 Gestão de Produtos (Custos)", "👗 Controle de Produção", "⚙️ Configurações"], label_visibility="collapsed")

# --- PÁGINA 1: DASHBOARD FINANCEIRO ---
if menu_selecionado == "📊 Dashboard":
    st.title("Dashboard Financeiro Amariti 👋")
    
    if conexao_ok and not df_fin.empty:
        total_faturado = df_fin['Faturamento Bruto'].sum()
        total_lucro = df_fin['Lucro Liquido'].sum()
        ticket_medio = df_fin['Faturamento Bruto'].mean()
        margem_percentual = (total_lucro / total_faturado) * 100 if total_faturado > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Total", formata_moeda(total_faturado))
        c2.metric("Total de Pedidos", f"{len(df_fin)}")
        c3.metric("Ticket Médio", formata_moeda(ticket_medio))
        c4.metric("Margem de Lucro", f"{margem_percentual:.1f}%")
        
        st.write("---")
        
        # --- A MÁGICA DO JODDA ACONTECE AQUI: CURVA ABC ---
        st.subheader("🏆 Top Produtos - Mais Lucrativos (Curva A)")
        st.markdown("Veja exatamente quais peças estão a colocar mais dinheiro no caixa da Amariti, já descontando o custo de produção de cada uma.")
        
        if not df_itens.empty and tiny_ok and not df_tiny.empty:
            # Transforma o SKU em texto nas duas planilhas para o casamento não falhar
            df_itens['SKU'] = df_itens['SKU'].astype(str)
            df_tiny['SKU'] = df_tiny['SKU'].astype(str)
            
            # Cruzando as vendas com os custos do Tiny (Match pelo SKU)
            df_merged = pd.merge(df_itens, df_tiny, on="SKU", how="left")
            
            # Produtos que não foram encontrados no Tiny ficam com custo 0
            df_merged['Custo (Tiny)'] = df_merged['Custo (Tiny)'].fillna(0)
            df_merged['Produto'] = df_merged['Produto_x'].fillna("Sem Nome")
            
            # A Matemática!
            df_merged['Faturamento_Item'] = df_merged['Quantidade'] * df_merged['Preco_Unitario']
            df_merged['Custo_Total_Item'] = df_merged['Quantidade'] * df_merged['Custo (Tiny)']
            df_merged['Lucro_Bruto_Item'] = df_merged['Faturamento_Item'] - df_merged['Custo_Total_Item']
            
            # Agrupando todos os SKUs iguais para ver o lucro total de cada modelo
            df_abc = df_merged.groupby(['SKU', 'Produto']).agg({
                'Quantidade': 'sum',
                'Faturamento_Item': 'sum',
                'Lucro_Bruto_Item': 'sum'
            }).reset_index()
            
            # Ordenando do que dá mais lucro para o que dá menos
            df_abc = df_abc.sort_values(by='Lucro_Bruto_Item', ascending=False)
            
            # Embelezando a tabela para a tela
            df_abc_view = df_abc.copy()
            df_abc_view = df_abc_view.rename(columns={'Quantidade': 'Qtd Vendida', 'Faturamento_Item': 'Faturamento Total', 'Lucro_Bruto_Item': 'Lucro Bruto (Fat - Custo)'})
            df_abc_view['Faturamento Total'] = df_abc_view['Faturamento Total'].apply(formata_moeda)
            df_abc_view['Lucro Bruto (Fat - Custo)'] = df_abc_view['Lucro Bruto (Fat - Custo)'].apply(formata_moeda)
            
            # Mostra apenas os 10 mais vendidos/lucrativos na tela inicial
            st.dataframe(df_abc_view.head(10), use_container_width=True, hide_index=True)
            
        else:
            st.info("💡 À espera que o seu n8n envie os primeiros produtos para a aba 'BD_Itens' para podermos gerar a tabela de Lucro por Produto!")
        
        st.write("---")
        st.subheader("Faturamento x Lucro Diário")
        df_dia = df_fin.groupby('Data').agg({'Faturamento Bruto': 'sum', 'Lucro Liquido': 'sum'}).reset_index()
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
    st.markdown("Estes produtos estão a ser **puxados agora mesmo** direto do seu Tiny ERP.")
    
    if tiny_ok and not df_tiny.empty:
        produtos_sem_custo = len(df_tiny[df_tiny['Custo (Tiny)'] == 0])
        col1, col2 = st.columns(2)
        col1.metric("📦 Total de Produtos no Tiny", f"{len(df_tiny)} SKUs")
        
        if produtos_sem_custo > 0:
            col2.error(f"⚠️ Atenção: {produtos_sem_custo} produtos estão com custo ZERO no Tiny!")
        else:
            col2.success("✅ Todos os produtos possuem custo cadastrado!")
            
        st.write("---")
        c1, c2 = st.columns([1, 3])
        with c1:
            mostrar_zerados = st.toggle("🚨 Mostrar apenas produtos SEM CUSTO", value=True if produtos_sem_custo > 0 else False)
        
        df_mostrar = df_tiny.copy()
        if mostrar_zerados:
            df_mostrar = df_mostrar[df_mostrar['Custo (Tiny)'] == 0]
            st.warning("A exibir apenas os produtos que precisam de atualização de custo urgente no Tiny.")
            
        df_mostrar['Preço de Venda'] = df_mostrar['Preço de Venda'].apply(formata_moeda)
        df_mostrar['Custo (Tiny)'] = df_mostrar['Custo (Tiny)'].apply(formata_moeda)
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        st.info("💡 Como arranjar: Abra o seu Tiny ERP, procure os SKUs listados acima e preencha o 'Preço de Custo'. Assim que guardar lá, atualize esta página e eles sumirão da lista de alertas!")
    else:
        st.error(f"🔴 Não consegui carregar os produtos do Tiny. Erro: {erro_tiny}")

elif menu_selecionado == "👗 Controle de Produção":
    st.title("👗 Controle de Produção (PCP)")
    st.info("Abaixo, ficará a tela para a sua equipa dar baixa na costura!")

elif menu_selecionado == "⚙️ Configurações":
    st.title("⚙️ Configurações")
    st.info("Ajustes gerais e impostos.")
