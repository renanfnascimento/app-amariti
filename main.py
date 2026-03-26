import streamlit as st
import gspread
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="Dashboard | Margem de Contribuição", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# --- CSS INSPIRADO NO JODDA.IA / TINY ---
st.markdown("""
<style>
    :root {
        --primary-color: #3c6fff;
        --text-color: #1a1d1f;
        --text-light: #6f767e;
        --bg-light: #f4f5f8;
        --white: #fff;
        --border-color: #e3e5e8;
        --accent-green: #2ca01c;
        --accent-red: #dc3545;
    }
    .stApp { background-color: var(--bg-light); }
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stSidebar"] {
        background-color: var(--white);
        border-right: 1px solid var(--border-color);
    }
    .tiny-card {
        background-color: var(--white);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 20px;
        box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.02);
        margin-bottom: 20px;
    }
    .tiny-row {
        display: flex; 
        justify-content: space-between; 
        border-bottom: 1px solid var(--border-color); 
        padding: 10px 0;
        font-size: 14px;
        color: var(--text-color);
    }
    .tiny-row:last-child { border-bottom: none; }
    .tiny-bold { font-weight: 600; }
    .tiny-green { color: var(--accent-green); font-weight: 600; }
    .tiny-red { color: var(--accent-red); }
</style>
""", unsafe_allow_html=True)

def formata_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def formata_perc(valor):
    return f"{valor:,.2f}%".replace(".", ",")

# --- CONEXÕES DE DADOS ---
@st.cache_data(ttl=60)
def load_data():
    try:
        credenciais_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
        gc = gspread.service_account_from_dict(credenciais_dict)
        ID_DA_PLANILHA = "1HaqFImRnQgIrL-6BlnsifIyUwSVRngaUujQAsqTKOZY"
        planilha = gc.open_by_key(ID_DA_PLANILHA)
        
        # Financeiro Geral (Fretes e Comissões)
        aba_fin = planilha.worksheet("BD_Financeiro")
        df_fin = pd.DataFrame(aba_fin.get_all_records())
        if not df_fin.empty:
            df_fin['Data'] = pd.to_datetime(df_fin['Data'], dayfirst=True, errors='coerce')
            cols_fin = ['Faturamento Bruto', 'Custos Venda (Produto+Taxa+Frete)']
            for col in cols_fin:
                if col in df_fin.columns:
                    df_fin[col] = pd.to_numeric(df_fin[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                    df_fin[col] = df_fin[col] / 100
                    
        # Itens Vendidos (Para produtos e pedidos)
        try:
            aba_itens = planilha.worksheet("BD_Itens")
            df_itens = pd.DataFrame(aba_itens.get_all_records())
            if not df_itens.empty:
                df_itens['Data'] = pd.to_datetime(df_itens['Data'], dayfirst=True, errors='coerce')
                df_itens['Quantidade'] = pd.to_numeric(df_itens.get('Quantidade', 0), errors='coerce').fillna(0)
                df_itens['Preco_Unitario'] = pd.to_numeric(df_itens.get('Preco_Unitario', 0).astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        except Exception:
            df_itens = pd.DataFrame()
            
        return df_fin, df_itens, True, ""
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), False, str(e)

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
            lista = [{"SKU": str(p['produto'].get('codigo', '-')), "Custo (Tiny)": float(p['produto'].get('preco_custo', 0))} for p in produtos]
            return pd.DataFrame(lista), True, ""
        return pd.DataFrame(), False, "Erro na API"
    except Exception as e:
        return pd.DataFrame(), False, str(e)

df_fin, df_itens, conexao_ok, erro = load_data()
df_tiny, tiny_ok, erro_tiny = load_tiny_produtos()

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3214/3214746.png", width=50)
    st.title("Amariti ERP")
    st.markdown("---")
    menu_selecionado = st.radio("Menu Principal", ["📊 Margem de Contribuição", "📦 Produtos e Custos"], label_visibility="collapsed")

# --- PÁGINA 1: MARGEM DE CONTRIBUIÇÃO (ESTILO TINY) ---
if menu_selecionado == "📊 Margem de Contribuição":
    st.title("Margem de Contribuição")
    
    if conexao_ok and not df_fin.empty and not df_itens.empty and tiny_ok:
        
        # PREPARANDO OS DADOS
        df_itens['SKU'] = df_itens['SKU'].astype(str)
        df_tiny['SKU'] = df_tiny['SKU'].astype(str)
        df_merged = pd.merge(df_itens, df_tiny, on="SKU", how="left")
        df_merged['Custo (Tiny)'] = df_merged['Custo (Tiny)'].fillna(0)
        
        df_merged['Faturamento_Item'] = df_merged['Quantidade'] * df_merged['Preco_Unitario']
        df_merged['Custo_Total_Item'] = df_merged['Quantidade'] * df_merged['Custo (Tiny)']
        
        # MATEMÁTICA DA VISÃO GERAL
        fat_total = df_fin['Faturamento Bruto'].sum()
        custos_venda = df_fin['Custos Venda (Produto+Taxa+Frete)'].sum() # No momento o n8n agrupa frete e comissão aqui
        custos_compras = df_merged['Custo_Total_Item'].sum()
        
        margem_contribuicao = fat_total - custos_venda - custos_compras
        indice_total = (margem_contribuicao / fat_total * 100) if fat_total > 0 else 0
        
        # 1. BLOCO VISÃO GERAL
        st.subheader("Visão geral")
        st.markdown(f"""
        <div class="tiny-card">
            <div class="tiny-row"><span>(+) Faturamento</span> <span class="tiny-bold">{formata_moeda(fat_total)}</span></div>
            <div class="tiny-row tiny-red"><span>(-) Custos de Venda (Fretes e Comissões)</span> <span>{formata_moeda(custos_venda)}</span></div>
            <div class="tiny-row tiny-red"><span>(-) Custos de compras (Custo Produção)</span> <span>{formata_moeda(custos_compras)}</span></div>
            <div class="tiny-row" style="margin-top: 10px; font-size: 16px;">
                <span class="tiny-bold">Margem de contribuição</span> 
                <span class="tiny-green">{formata_moeda(margem_contribuicao)}</span>
            </div>
            <div class="tiny-row" style="font-size: 16px;">
                <span class="tiny-bold">Índice total da margem</span> 
                <span class="tiny-bold">{formata_perc(indice_total)}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. BLOCO CANAIS DE VENDA
        st.subheader("Canais de venda")
        # Pega faturamento e custo de venda por canal
        df_canais_fin = df_fin.groupby('Canal').agg({'Faturamento Bruto': 'sum', 'Custos Venda (Produto+Taxa+Frete)': 'sum'}).reset_index()
        # Pega custo de produto por canal
        df_canais_itens = df_merged.groupby('Canal').agg({'Custo_Total_Item': 'sum'}).reset_index()
        
        df_canais = pd.merge(df_canais_fin, df_canais_itens, on='Canal', how='left').fillna(0)
        df_canais['Margem'] = df_canais['Faturamento Bruto'] - df_canais['Custos Venda (Produto+Taxa+Frete)'] - df_canais['Custo_Total_Item']
        df_canais['Índice'] = (df_canais['Margem'] / df_canais['Faturamento Bruto']) * 100
        
        df_canais_view = df_canais[['Canal', 'Faturamento Bruto', 'Margem', 'Índice']].copy()
        df_canais_view = df_canais_view.rename(columns={'Faturamento Bruto': 'Faturado', 'Índice': 'Índice (%)'})
        df_canais_view['Faturado'] = df_canais_view['Faturado'].apply(formata_moeda)
        df_canais_view['Margem'] = df_canais_view['Margem'].apply(formata_moeda)
        df_canais_view['Índice (%)'] = df_canais_view['Índice (%)'].apply(formata_perc)
        
        st.dataframe(df_canais_view, use_container_width=True, hide_index=True)
        
        # 3. BLOCO PRODUTOS
        st.subheader("Produtos")
        df_prods = df_merged.groupby('Produto').agg({'Numero_Pedido': 'nunique', 'Quantidade': 'sum', 'Faturamento_Item': 'sum', 'Custo_Total_Item': 'sum'}).reset_index()
        df_prods['Margem'] = df_prods['Faturamento_Item'] - df_prods['Custo_Total_Item']
        df_prods['Índice (%)'] = (df_prods['Margem'] / df_prods['Faturamento_Item']) * 100
        
        df_prods = df_prods.sort_values('Faturamento_Item', ascending=False)
        df_prods_view = df_prods[['Produto', 'Numero_Pedido', 'Quantidade', 'Faturamento_Item', 'Índice (%)']].copy()
        df_prods_view = df_prods_view.rename(columns={'Produto': 'Descrição', 'Numero_Pedido': 'Qtd. de vendas', 'Quantidade': 'Qtd. vendida', 'Faturamento_Item': 'Total faturado'})
        df_prods_view['Total faturado'] = df_prods_view['Total faturado'].apply(formata_moeda)
        df_prods_view['Índice (%)'] = df_prods_view['Índice (%)'].apply(formata_perc)
        
        st.dataframe(df_prods_view, use_container_width=True, hide_index=True)

        # 4. BLOCO PEDIDOS DE VENDA
        st.subheader("Pedidos de venda")
        df_pedidos = df_merged.groupby(['Numero_Pedido', 'Data']).agg({'Quantidade': 'sum', 'Faturamento_Item': 'sum', 'Custo_Total_Item': 'sum'}).reset_index()
        df_pedidos['Índice (%)'] = ((df_pedidos['Faturamento_Item'] - df_pedidos['Custo_Total_Item']) / df_pedidos['Faturamento_Item']) * 100
        
        df_pedidos = df_pedidos.sort_values('Data', ascending=False)
        df_pedidos_view = df_pedidos[['Numero_Pedido', 'Data', 'Quantidade', 'Faturamento_Item', 'Índice (%)']].copy()
        df_pedidos_view = df_pedidos_view.rename(columns={'Numero_Pedido': 'Nº Pedido', 'Quantidade': 'Qtd. de itens', 'Faturamento_Item': 'Total faturado'})
        df_pedidos_view['Data'] = df_pedidos_view['Data'].dt.strftime('%d/%m/%Y')
        df_pedidos_view['Total faturado'] = df_pedidos_view['Total faturado'].apply(formata_moeda)
        df_pedidos_view['Índice (%)'] = df_pedidos_view['Índice (%)'].apply(formata_perc)
        
        st.dataframe(df_pedidos_view, use_container_width=True, hide_index=True)

    else:
        st.warning("À espera de dados na planilha ou configuração do Tiny.")

# --- PÁGINA 2: GESTÃO DE PRODUTOS ---
elif menu_selecionado == "📦 Produtos e Custos":
    st.title("📦 Produtos e Custos")
    if tiny_ok and not df_tiny.empty:
        produtos_sem_custo = len(df_tiny[df_tiny['Custo (Tiny)'] == 0])
        col1, col2 = st.columns(2)
        col1.metric("📦 Total de SKUs", f"{len(df_tiny)}")
        if produtos_sem_custo > 0:
            col2.error(f"⚠️ {produtos_sem_custo} produtos com custo ZERO!")
        else:
            col2.success("✅ Tudo com custo!")
            
        mostrar_zerados = st.toggle("🚨 Mostrar apenas SEM CUSTO", value=True if produtos_sem_custo > 0 else False)
        df_mostrar = df_tiny.copy()
        if mostrar_zerados:
            df_mostrar = df_mostrar[df_mostrar['Custo (Tiny)'] == 0]
            
        df_mostrar['Custo (Tiny)'] = df_mostrar['Custo (Tiny)'].apply(formata_moeda)
        st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
