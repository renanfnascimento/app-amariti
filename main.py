import streamlit as st
import gspread
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="ERP Amariti | Estilo Tiny", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# --- CSS INSPIRADO NO TINY ERP ---
st.markdown("""
<style>
    :root {
        --primary-color: #0050DC; 
        --text-color: #333333;
        --text-light: #666666;
        --bg-light: #F4F6F8;
        --white: #ffffff;
        --border-color: #E0E0E0;
        --accent-green: #28a745;
        --accent-red: #dc3545;
    }
    .stApp { background-color: var(--bg-light); }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #2C3338; 
    }
    [data-testid="stSidebar"] * {
        color: #ffffff !important;
    }
    
    /* Cartões e Paineis */
    div[data-testid="stMetric"], .tiny-card {
        background-color: var(--white);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 20px;
        box-shadow: 0px 1px 3px rgba(0, 0, 0, 0.05);
        margin-bottom: 15px;
    }
    div[data-testid="stMetricValue"] {
        color: var(--text-color) !important;
        font-size: 28px !important;
        font-weight: 700;
        margin-top: 5px;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px !important;
        color: var(--text-light) !important;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    /* Tabelas da Margem de Contribuição */
    .tiny-row {
        display: flex; 
        justify-content: space-between; 
        border-bottom: 1px solid var(--border-color); 
        padding: 12px 0;
        font-size: 14px;
        color: var(--text-color);
    }
    .tiny-row:last-child { border-bottom: none; }
    .tiny-bold { font-weight: 600; color: var(--text-color); }
    .tiny-green { color: var(--accent-green); font-weight: 700; }
    .tiny-red { color: var(--accent-red); font-weight: 600; }
    
    /* Gráficos */
    .element-container [data-testid="stPlotlyChart"] {
        background-color: var(--white);
        border-radius: 6px;
        border: 1px solid var(--border-color);
        padding: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES DE FORMATAÇÃO ---
def formata_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formata_perc(valor):
    return f"{valor:,.2f}%".replace(".", ",")

# --- 1. BUSCA DE DADOS (GOOGLE SHEETS) ---
@st.cache_data(ttl=60)
def load_data():
    try:
        credenciais_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        gc = gspread.service_account_from_dict(credenciais_dict)
        ID_DA_PLANILHA = "1HaqFImRnQgIrL-6BlnsifIyUwSVRngaUujQAsqTKOZY"
        planilha = gc.open_by_key(ID_DA_PLANILHA)
        
        # Aba BD_Financeiro
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

        # Aba BD_Itens
        try:
            aba_itens = planilha.worksheet("BD_Itens")
            df_itens = pd.DataFrame(aba_itens.get_all_records())
            if not df_itens.empty:
                df_itens['Data'] = pd.to_datetime(df_itens['Data'], dayfirst=True, errors='coerce')
                df_itens['Quantidade'] = pd.to_numeric(df_itens.get('Quantidade', 0), errors='coerce').fillna(0)
                # CORREÇÃO DOS ZEROS: Tratando e Dividindo por 100
                df_itens['Preco_Unitario'] = pd.to_numeric(df_itens.get('Preco_Unitario', 0).astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                df_itens['Preco_Unitario'] = df_itens['Preco_Unitario'] / 100
        except Exception:
            df_itens = pd.DataFrame()
            
        return df_fin, df_itens, True, ""
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), False, str(e)

# --- 2. BUSCA DE DADOS (TINY ERP) ---
@st.cache_data(ttl=300)
def load_tiny_produtos():
    token = st.secrets.get("TINY_TOKEN", "")
    if not token: return pd.DataFrame(), False, "Token não encontrado."
    
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
                    "SKU": str(prod.get('codigo', '-')),
                    "Produto": prod.get('nome', 'Sem Nome'),
                    "Preço de Venda": float(prod.get('preco', 0)),
                    "Custo (Tiny)": float(prod.get('preco_custo', 0))
                })
            return pd.DataFrame(lista), True, ""
        return pd.DataFrame(), False, "Erro na API do Tiny."
    except Exception as e:
        return pd.DataFrame(), False, str(e)

# Carregando Tudo
df_fin, df_itens, conexao_ok, erro = load_data()
df_tiny, tiny_ok, erro_tiny = load_tiny_produtos()

# Tratamento cruzado para páginas de Vendas
if conexao_ok and tiny_ok and not df_itens.empty and not df_tiny.empty:
    df_itens['SKU'] = df_itens['SKU'].astype(str)
    df_tiny['SKU'] = df_tiny['SKU'].astype(str)
    df_merged = pd.merge(df_itens, df_tiny, on="SKU", how="left")
    df_merged['Custo (Tiny)'] = df_merged['Custo (Tiny)'].fillna(0)
    df_merged['Produto_y'] = df_merged['Produto_y'].fillna(df_merged['Produto_x'])
    df_merged['Faturamento_Item'] = df_merged['Quantidade'] * df_merged['Preco_Unitario']
    df_merged['Custo_Total_Item'] = df_merged['Quantidade'] * df_merged['Custo (Tiny)']
else:
    df_merged = pd.DataFrame()


# --- ESTRUTURA DO MENU LATERAL (ESTILO TINY) ---
with st.sidebar:
    st.markdown("### 🏢 Amariti ERP")
    st.markdown("---")
    
    modulo = st.selectbox("MÓDULO DO SISTEMA", ["Início", "Cadastros", "Suprimentos", "Vendas", "Finanças", "Configurações"])
    st.markdown("---")
    
    if modulo == "Início":
        submenu = st.radio("Navegação", ["📊 Dashboard Financeiro"])
    elif modulo == "Cadastros":
        submenu = st.radio("Navegação", ["📦 Gestão de Produtos (Custos)", "👥 Clientes e Fornecedores"])
    elif modulo == "Suprimentos":
        submenu = st.radio("Navegação", ["👗 Controle de Produção (PCP)", "📦 Estoque"])
    elif modulo == "Vendas":
        submenu = st.radio("Navegação", ["📈 Margem de Contribuição", "🏆 Curva ABC (Lucro por Produto)", "🛒 Pedidos de Venda"])
    elif modulo == "Finanças":
        submenu = st.radio("Navegação", ["💰 Caixa", "🧾 Contas a Pagar/Receber"])
    elif modulo == "Configurações":
        submenu = st.radio("Navegação", ["⚙️ Geral", "🔌 Integrações"])


# =====================================================================
# RENDERIZAÇÃO DAS PÁGINAS COM BASE NO MENU ESCOLHIDO
# =====================================================================

# -----------------------------------------
# MÓDULO: INÍCIO -> DASHBOARD FINANCEIRO
# -----------------------------------------
if submenu == "📊 Dashboard Financeiro":
    st.title("Dashboard Financeiro")
    st.markdown("Visão geral do desempenho da sua empresa.")
    
    if conexao_ok and not df_fin.empty:
        fat_total = df_fin['Faturamento Bruto'].sum()
        lucro_total = df_fin['Lucro Liquido'].sum()
        ticket_med = df_fin['Faturamento Bruto'].mean()
        margem_pct = (lucro_total / fat_total) * 100 if fat_total > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Bruto", formata_moeda(fat_total))
        c2.metric("Lucro Líquido", formata_moeda(lucro_total))
        c3.metric("Ticket Médio", formata_moeda(ticket_med))
        c4.metric("Margem Final", f"{margem_pct:.1f}%")
        
        st.write("---")
        st.subheader("Evolução: Faturamento x Lucro Diário")
        
        df_dia = df_fin.groupby('Data').agg({'Faturamento Bruto': 'sum', 'Lucro Liquido': 'sum'}).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_dia['Data'], y=df_dia['Faturamento Bruto'], name='Faturamento', marker_color='#B0C4DE', marker_line_width=0))
        fig.add_trace(go.Scatter(x=df_dia['Data'], y=df_dia['Lucro Liquido'], name='Lucro Líquido', mode='lines+markers', line=dict(color='#0050DC', width=3), marker=dict(size=6)))
        fig.update_layout(plot_bgcolor='#ffffff', paper_bgcolor='#ffffff', hovermode="x unified", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#E0E0E0'), margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Sem dados financeiros registrados ainda.")

# -----------------------------------------
# MÓDULO: CADASTROS -> GESTÃO DE PRODUTOS
# -----------------------------------------
elif submenu == "📦 Gestão de Produtos (Custos)":
    st.title("Gestão de Produtos e Custos")
    st.markdown("Estes produtos estão sincronizados **ao vivo** com o Tiny ERP.")
    
    if tiny_ok and not df_tiny.empty:
        produtos_sem_custo = len(df_tiny[df_tiny['Custo (Tiny)'] == 0])
        col1, col2 = st.columns(2)
        col1.metric("Total de SKUs Ativos", f"{len(df_tiny)}")
        
        if produtos_sem_custo > 0:
            col2.error(f"⚠️ {produtos_sem_custo} produtos estão com custo ZERO no Tiny!")
        else:
            col2.success("✅ Todos os produtos possuem custo cadastrado!")
            
        st.write("---")
        mostrar_zerados = st.toggle("🚨 Mostrar apenas produtos SEM CUSTO", value=True if produtos_sem_custo > 0 else False)
        
        df_mostrar = df_tiny.copy()
        if mostrar_zerados:
            df_mostrar = df_mostrar[df_mostrar['Custo (Tiny)'] == 0]
            
        df_mostrar['Preço de Venda'] = df_mostrar['Preço de Venda'].apply(formata_moeda)
        df_mostrar['Custo (Tiny)'] = df_mostrar['Custo (Tiny)'].apply(formata_moeda)
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
    else:
        st.error("Erro ao comunicar com a API do Tiny.")

# -----------------------------------------
# MÓDULO: VENDAS -> MARGEM DE CONTRIBUIÇÃO (A réplica do Tiny)
# -----------------------------------------
elif submenu == "📈 Margem de Contribuição":
    st.title("Margem de Contribuição")
    
    if not df_fin.empty and not df_merged.empty:
        fat_total = df_fin['Faturamento Bruto'].sum()
        custos_venda = df_fin['Custos Venda (Produto+Taxa+Frete)'].sum() 
        custos_compras = df_merged['Custo_Total_Item'].sum()
        
        margem_contribuicao = fat_total - custos_venda - custos_compras
        indice_total = (margem_contribuicao / fat_total * 100) if fat_total > 0 else 0
        
        st.subheader("Visão geral")
        st.markdown(f"""
        <div class="tiny-card">
            <div class="tiny-row"><span>(+) Faturamento</span> <span class="tiny-bold" style="color:#333;">{formata_moeda(fat_total)}</span></div>
            <div class="tiny-row tiny-red"><span>(-) Custos de Venda (Fretes e Comissões)</span> <span>{formata_moeda(custos_venda)}</span></div>
            <div class="tiny-row tiny-red"><span>(-) Custos de compras (Produção/Estoque)</span> <span>{formata_moeda(custos_compras)}</span></div>
            <div class="tiny-row" style="margin-top: 15px;">
                <span class="tiny-bold" style="font-size: 16px;">Margem de contribuição</span> 
                <span class="tiny-green" style="font-size: 16px;">{formata_moeda(margem_contribuicao)}</span>
            </div>
            <div class="tiny-row">
                <span class="tiny-bold" style="font-size: 16px;">Índice total da margem</span> 
                <span class="tiny-bold" style="font-size: 16px; color:#333;">{formata_perc(indice_total)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("Canais de venda")
        df_canais_fin = df_fin.groupby('Canal').agg({'Faturamento Bruto': 'sum', 'Custos Venda (Produto+Taxa+Frete)': 'sum'}).reset_index()
        df_canais_itens = df_merged.groupby('Canal').agg({'Custo_Total_Item': 'sum'}).reset_index()
        df_canais = pd.merge(df_canais_fin, df_canais_itens, on='Canal', how='left').fillna(0)
        df_canais['Margem'] = df_canais['Faturamento Bruto'] - df_canais['Custos Venda (Produto+Taxa+Frete)'] - df_canais['Custo_Total_Item']
        df_canais['Índice'] = (df_canais['Margem'] / df_canais['Faturamento Bruto']) * 100
        
        df_canais_view = df_canais[['Canal', 'Faturamento Bruto', 'Margem', 'Índice']].rename(columns={'Faturamento Bruto': 'Faturado', 'Índice': 'Índice (%)'})
        df_canais_view['Faturado'] = df_canais_view['Faturado'].apply(formata_moeda)
        df_canais_view['Margem'] = df_canais_view['Margem'].apply(formata_moeda)
        df_canais_view['Índice (%)'] = df_canais_view['Índice (%)'].apply(formata_perc)
        st.dataframe(df_canais_view, use_container_width=True, hide_index=True)

        st.subheader("Produtos")
        df_prods = df_merged.groupby('Produto_y').agg({'Numero_Pedido': 'nunique', 'Quantidade': 'sum', 'Faturamento_Item': 'sum', 'Custo_Total_Item': 'sum'}).reset_index()
        df_prods['Margem'] = df_prods['Faturamento_Item'] - df_prods['Custo_Total_Item']
        df_prods['Índice (%)'] = (df_prods['Margem'] / df_prods['Faturamento_Item']) * 100
        
        df_prods = df_prods.sort_values('Faturamento_Item', ascending=False)
        df_prods_view = df_prods[['Produto_y', 'Numero_Pedido', 'Quantidade', 'Faturamento_Item', 'Índice (%)']].copy()
        df_prods_view = df_prods_view.rename(columns={'Produto_y': 'Descrição', 'Numero_Pedido': 'Qtd. de vendas', 'Quantidade': 'Qtd. vendida', 'Faturamento_Item': 'Total faturado'})
        df_prods_view['Total faturado'] = df_prods_view['Total faturado'].apply(formata_moeda)
        df_prods_view['Índice (%)'] = df_prods_view['Índice (%)'].apply(formata_perc)
        
        st.dataframe(df_prods_view, use_container_width=True, hide_index=True)

        st.subheader("Pedidos de venda")
        df_pedidos = df_merged.groupby(['Numero_Pedido', 'Data']).agg({'Quantidade': 'sum', 'Faturamento_Item': 'sum', 'Custo_Total_Item': 'sum'}).reset_index()
        df_pedidos['Índice (%)'] = ((df_pedidos['Faturamento_Item'] - df_pedidos['Custo_Total_Item']) / df_pedidos['Faturamento_Item']) * 100
        df_pedidos = df_pedidos.sort_values('Data', ascending=False)
        df_pedidos_view = df_pedidos[['Numero_Pedido', 'Data', 'Quantidade', 'Faturamento_Item', 'Índice (%)']].rename(columns={'Numero_Pedido': 'Nº Pedido', 'Quantidade': 'Qtd. de itens', 'Faturamento_Item': 'Total faturado'})
        df_pedidos_view['Data'] = df_pedidos_view['Data'].dt.strftime('%d/%m/%Y')
        df_pedidos_view['Total faturado'] = df_pedidos_view['Total faturado'].apply(formata_moeda)
        df_pedidos_view['Índice (%)'] = df_pedidos_view['Índice (%)'].apply(formata_perc)
        st.dataframe(df_pedidos_view, use_container_width=True, hide_index=True)
    else:
        st.warning("Faltam dados para processar a margem de contribuição (necessita de vendas no BD_Financeiro e BD_Itens).")

# -----------------------------------------
# MÓDULO: VENDAS -> CURVA ABC (Top Produtos)
# -----------------------------------------
elif submenu == "🏆 Curva ABC (Lucro por Produto)":
    st.title("Curva ABC de Produtos")
    st.markdown("Descubra quais SKUs trazem o maior Lucro Bruto real para a empresa.")
    
    if not df_merged.empty:
        df_merged['Lucro_Bruto_Item'] = df_merged['Faturamento_Item'] - df_merged['Custo_Total_Item']
        
        df_abc = df_merged.groupby(['SKU', 'Produto_y']).agg({
            'Quantidade': 'sum',
            'Faturamento_Item': 'sum',
            'Lucro_Bruto_Item': 'sum'
        }).reset_index()
        
        df_abc = df_abc.sort_values(by='Lucro_Bruto_Item', ascending=False)
        df_abc_view = df_abc.rename(columns={'Produto_y': 'Descrição', 'Quantidade': 'Qtd Vendida', 'Faturamento_Item': 'Faturamento', 'Lucro_Bruto_Item': 'Lucro Bruto'})
        df_abc_view['Faturamento'] = df_abc_view['Faturamento'].apply(formata_moeda)
        df_abc_view['Lucro Bruto'] = df_abc_view['Lucro Bruto'].apply(formata_moeda)
        
        st.dataframe(df_abc_view, use_container_width=True, hide_index=True)
    else:
        st.warning("Sem dados de itens vendidos no momento.")

# -----------------------------------------
# OUTROS MÓDULOS (EM CONSTRUÇÃO)
# -----------------------------------------
else:
    st.title(submenu.replace("⚙️ ", "").replace("📦 ", "").replace("👗 ", "").replace("💰 ", "").replace("🧾 ", "").replace("🛒 ", "").replace("👥 ", ""))
    st.info("Este módulo está em construção. Em breve estará disponível na Amariti ERP!")
