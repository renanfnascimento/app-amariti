import streamlit as st
import gspread
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import datetime

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="ERP Amariti | Financeiro e PCP", page_icon="🚀", layout="wide", initial_sidebar_state="expanded")

# --- CSS INSPIRADO NO TINY ERP E DRE ---
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
    [data-testid="stHeaderActionElements"] {display: none;}
    header {background: transparent !important;}
    
    [data-testid="stSidebar"] { background-color: #2C3338; }
    [data-testid="stSidebar"] * { color: #ffffff !important; }
    div[data-testid="stDateInput"] * { color: #333 !important; }
    div[data-testid="stDateInput"] label { color: #fff !important; }
    
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
    
    /* ESTILO DA DRE (Cascata Financeira) */
    .dre-container {
        background-color: var(--white);
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 15px 25px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.02);
        margin-bottom: 20px;
        font-family: 'Inter', sans-serif;
    }
    .dre-row {
        display: flex;
        justify-content: space-between;
        padding: 10px 15px;
        border-bottom: 1px solid #f4f4f4;
        font-size: 14px;
        color: #444;
    }
    .dre-row:last-child { border-bottom: none; }
    .dre-sub {
        padding-left: 40px;
        color: #666;
    }
    .dre-total {
        font-weight: 700;
        font-size: 15px;
        color: #222;
        background-color: #fafafa;
        border-radius: 4px;
        margin: 4px 0;
    }
    .dre-highlight {
        background-color: #e8f5e9;
        color: #2ca01c;
        font-size: 16px;
        margin-top: 10px;
    }
    .dre-profit {
        background-color: #e3f2fd;
        color: #0050DC;
        font-size: 16px;
        margin-top: 10px;
        border: 1px solid #bbdefb;
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
        planilha = gc.open_by_key("1HaqFImRnQgIrL-6BlnsifIyUwSVRngaUujQAsqTKOZY")
        
        # Financeiro
        aba_fin = planilha.worksheet("BD_Financeiro")
        df_fin = pd.DataFrame(aba_fin.get_all_records())
        if not df_fin.empty:
            df_fin['Data'] = pd.to_datetime(df_fin['Data'], dayfirst=True, errors='coerce')
            cols_fin = ['Faturamento Bruto', 'Lucro Liquido', 'Margem de Contribuição', 'Custos Venda (Produto+Taxa+Frete)', 'Custo Fixo Rateado', 'Custo ADS']
            for col in cols_fin:
                if col in df_fin.columns:
                    df_fin[col] = pd.to_numeric(df_fin[col].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                    if col != 'Custo ADS': # Apenas se o n8n nao dividiu por 100
                        df_fin[col] = df_fin[col] / 100
            df_fin = df_fin.sort_values('Data')

        # Itens
        try:
            aba_itens = planilha.worksheet("BD_Itens")
            df_itens = pd.DataFrame(aba_itens.get_all_records())
            if not df_itens.empty:
                df_itens['Data'] = pd.to_datetime(df_itens['Data'], dayfirst=True, errors='coerce')
                df_itens['Quantidade'] = pd.to_numeric(df_itens.get('Quantidade', 0), errors='coerce').fillna(0)
                df_itens['Preco_Unitario'] = pd.to_numeric(df_itens.get('Preco_Unitario', 0).astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
                df_itens['Preco_Unitario'] = df_itens['Preco_Unitario'] / 100
        except Exception:
            df_itens = pd.DataFrame()
            
        # PCP - Ficha Técnica
        try:
            aba_ficha = planilha.worksheet("Ficha_Tecnica")
            df_ficha = pd.DataFrame(aba_ficha.get_all_records())
            if not df_ficha.empty:
                # Garante que a quantidade seja numero
                if 'Quantidade' in df_ficha.columns:
                    df_ficha['Quantidade'] = pd.to_numeric(df_ficha['Quantidade'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        except Exception:
            df_ficha = pd.DataFrame()
            
        return df_fin, df_itens, df_ficha, True, ""
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), False, str(e)

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
df_fin_raw, df_itens_raw, df_ficha_raw, conexao_ok, erro = load_data()
df_tiny, tiny_ok, erro_tiny = load_tiny_produtos()

# --- SIDEBAR E FILTRO DE DATAS ---
with st.sidebar:
    st.markdown("### 🏢 Amariti ERP")
    st.markdown("---")
    
    modulo = st.selectbox("MÓDULO DO SISTEMA", ["Início", "Cadastros", "Suprimentos", "Vendas", "Finanças", "Configurações"])
    
    if modulo == "Início":
        submenu = st.radio("Navegação", ["📊 Dashboard Financeiro"])
    elif modulo == "Cadastros":
        submenu = st.radio("Navegação", ["📦 Gestão de Produtos (Custos)", "👥 Clientes e Fornecedores"])
    elif modulo == "Suprimentos":
        submenu = st.radio("Navegação", ["👗 Controle de Produção (PCP)", "📦 Estoque"])
    elif modulo == "Vendas":
        submenu = st.radio("Navegação", ["📈 DRE e Margem de Contribuição", "🏆 Curva ABC (Lucro por Produto)", "🛒 Pedidos de Venda"])
    elif modulo == "Finanças":
        submenu = st.radio("Navegação", ["💰 Caixa", "🧾 Contas a Pagar/Receber"])
    elif modulo == "Configurações":
        submenu = st.radio("Navegação", ["⚙️ Geral", "🔌 Integrações"])
        
    st.markdown("---")
    st.markdown("### 📅 Filtro de Período")
    hoje = datetime.date.today()
    ontem = hoje - datetime.timedelta(days=1)
    
    periodo_rapido = st.selectbox("Período rápido", ["Ontem", "Hoje", "Mês Atual", "Personalizado"])
    
    if periodo_rapido == "Ontem":
        data_inicio, data_fim = ontem, ontem
    elif periodo_rapido == "Hoje":
        data_inicio, data_fim = hoje, hoje
    elif periodo_rapido == "Mês Atual":
        data_inicio = hoje.replace(day=1)
        data_fim = hoje
    else:
        col1, col2 = st.columns(2)
        data_inicio = col1.date_input("Início", ontem)
        data_fim = col2.date_input("Fim", ontem)

# --- APLICANDO O FILTRO DE DATA ---
df_fin = df_fin_raw.copy()
df_itens = df_itens_raw.copy()
df_ficha = df_ficha_raw.copy()

if not df_fin.empty:
    mask_fin = (df_fin['Data'].dt.date >= data_inicio) & (df_fin['Data'].dt.date <= data_fim)
    df_fin = df_fin.loc[mask_fin]

if not df_itens.empty:
    mask_itens = (df_itens['Data'].dt.date >= data_inicio) & (df_itens['Data'].dt.date <= data_fim)
    df_itens = df_itens.loc[mask_itens]

# --- TRATAMENTO CRUZADO (ITENS X TINY) ---
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


# =====================================================================
# RENDERIZAÇÃO DAS PÁGINAS
# =====================================================================

if submenu == "📊 Dashboard Financeiro":
    st.title("Dashboard Financeiro")
    st.markdown(f"Período: **{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}**")
    
    if conexao_ok and not df_fin.empty:
        fat_total = df_fin['Faturamento Bruto'].sum()
        lucro_total = df_fin['Lucro Liquido'].sum()
        ticket_med = df_fin['Faturamento Bruto'].mean()
        margem_pct = (lucro_total / fat_total) * 100 if fat_total > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Faturamento Bruto", formata_moeda(fat_total))
        c2.metric("Lucro Líquido", formata_moeda(lucro_total))
        c3.metric("Ticket Médio", formata_moeda(ticket_med))
        c4.metric("Margem Final (%)", f"{margem_pct:.1f}%")
        
        st.write("---")
        st.subheader("Evolução: Faturamento x Lucro Diário")
        df_dia = df_fin.groupby('Data').agg({'Faturamento Bruto': 'sum', 'Lucro Liquido': 'sum'}).reset_index()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_dia['Data'], y=df_dia['Faturamento Bruto'], name='Faturamento', marker_color='#B0C4DE', marker_line_width=0))
        fig.add_trace(go.Scatter(x=df_dia['Data'], y=df_dia['Lucro Liquido'], name='Lucro Líquido', mode='lines+markers', line=dict(color='#0050DC', width=3), marker=dict(size=6)))
        fig.update_layout(plot_bgcolor='#ffffff', paper_bgcolor='#ffffff', hovermode="x unified", xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#E0E0E0'), margin=dict(l=0, r=0, t=20, b=0))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Sem dados financeiros registrados para este período.")

# -----------------------------------------
# MÓDULO: VENDAS -> DRE E MARGEM DE CONTRIBUIÇÃO
# -----------------------------------------
elif submenu == "📈 DRE e Margem de Contribuição":
    st.title("DRE Analítica e Margem de Contribuição")
    st.markdown(f"Demonstração do Resultado do Exercício. Período: **{data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}**")
    
    if not df_fin.empty and not df_merged.empty:
        # A MATEMÁTICA PERFEITA DA DRE
        receita_bruta = df_fin['Faturamento Bruto'].sum()
        deducoes = 0 
        receita_liquida = receita_bruta - deducoes
        
        cmv_produtos = df_merged['Custo_Total_Item'].sum()
        custos_venda_frete_comissao = df_fin['Custos Venda (Produto+Taxa+Frete)'].sum() 
        custo_ads = df_fin['Custo ADS'].sum() if 'Custo ADS' in df_fin.columns else 0
        total_custos_variaveis = cmv_produtos + custos_venda_frete_comissao + custo_ads
        
        margem_contribuicao = receita_liquida - total_custos_variaveis
        indice_margem = (margem_contribuicao / receita_bruta * 100) if receita_bruta > 0 else 0
        
        custos_fixos = df_fin['Custo Fixo Rateado'].sum()
        lucro_operacional = margem_contribuicao - custos_fixos
        indice_lucro = (lucro_operacional / receita_bruta * 100) if receita_bruta > 0 else 0
        
        st.subheader("📊 Visão Geral (DRE - Padrão Contábil)")
        st.markdown(f"""
        <div class="dre-container">
            <div class="dre-row dre-total">
                <span>Receita Bruta (Faturamento)</span> <span>{formata_moeda(receita_bruta)}</span>
            </div>
            <div class="dre-row dre-sub">
                <span>(-) Impostos e Devoluções</span> <span>{formata_moeda(deducoes)}</span>
            </div>
            <div class="dre-row dre-total">
                <span>= Receita Líquida</span> <span>{formata_moeda(receita_liquida)}</span>
            </div>
            <div class="dre-row dre-sub" style="margin-top: 10px;">
                <span>(-) CMV (Custo de Compra/Produção do Tiny)</span> <span style="color:#dc3545;">{formata_moeda(cmv_produtos)}</span>
            </div>
            <div class="dre-row dre-sub">
                <span>(-) Comissões e Fretes (Marketplaces)</span> <span style="color:#dc3545;">{formata_moeda(custos_venda_frete_comissao)}</span>
            </div>
            <div class="dre-row dre-sub">
                <span>(-) Investimento em ADS</span> <span style="color:#dc3545;">{formata_moeda(custo_ads)}</span>
            </div>
            <div class="dre-row dre-total dre-highlight">
                <span>= Margem de Contribuição (Lucro Bruto)</span> <span>{formata_moeda(margem_contribuicao)} ({formata_perc(indice_margem)})</span>
            </div>
            <div class="dre-row dre-sub" style="margin-top: 10px;">
                <span>(-) Despesas Fixas (Rateio Operacional)</span> <span style="color:#dc3545;">{formata_moeda(custos_fixos)}</span>
            </div>
            <div class="dre-row dre-total dre-profit">
                <span>= Lucro Líquido Operacional</span> <span>{formata_moeda(lucro_operacional)} ({formata_perc(indice_lucro)})</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.subheader("Canais de venda")
        df_canais_fin = df_fin.groupby('Canal').agg({'Faturamento Bruto': 'sum', 'Custos Venda (Produto+Taxa+Frete)': 'sum'}).reset_index()
        df_canais_itens = df_merged.groupby('Canal').agg({'Custo_Total_Item': 'sum'}).reset_index()
        df_canais = pd.merge(df_canais_fin, df_canais_itens, on='Canal', how='left').fillna(0)
        df_canais['Margem'] = df_canais['Faturamento Bruto'] - df_canais['Custos Venda (Produto+Taxa+Frete)'] - df_canais['Custo_Total_Item']
        df_canais['Índice (%)'] = (df_canais['Margem'] / df_canais['Faturamento Bruto']) * 100
        
        df_canais = df_canais.sort_values('Faturamento Bruto', ascending=False)
        df_canais_view = df_canais[['Canal', 'Faturamento Bruto', 'Margem', 'Índice (%)']].rename(columns={'Faturamento Bruto': 'Faturado'})
        df_canais_view['Faturado'] = df_canais_view['Faturado'].apply(formata_moeda)
        df_canais_view['Margem'] = df_canais_view['Margem'].apply(formata_moeda)
        df_canais_view['Índice (%)'] = df_canais_view['Índice (%)'].apply(formata_perc)
        st.dataframe(df_canais_view, use_container_width=True, hide_index=True)

    else:
        st.warning("Sem dados suficientes para processar a DRE no período selecionado.")

# -----------------------------------------
# MÓDULO: VENDAS -> CURVA ABC (Top Produtos)
# -----------------------------------------
elif submenu == "🏆 Curva ABC (Lucro por Produto)":
    st.title("Curva ABC de Produtos")
    st.markdown("Veja quais peças geram o maior Lucro Bruto real para a Amariti.")
    
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
        st.warning("Sem dados de itens vendidos no período selecionado.")

# -----------------------------------------
# MÓDULO: SUPRIMENTOS -> PCP (NOVO!)
# -----------------------------------------
elif submenu == "👗 Controle de Produção (PCP)":
    st.title("👗 Planejamento e Controle de Produção (PCP)")
    st.markdown("Calcule a necessidade de insumos para suas próximas produções.")
    
    if not df_ficha.empty:
        st.success("✅ Fichas Técnicas carregadas com sucesso da planilha!")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.subheader("1. Plano Mestre de Produção")
            # Lista única de SKUs que tem ficha técnica cadastrada
            skus_disponiveis = df_ficha['SKU_Produto'].unique()
            sku_selecionado = st.selectbox("Selecione o Produto (SKU) que deseja produzir:", skus_disponiveis)
            
            # Pega o nome do produto selecionado para exibir bonitinho
            nome_produto = df_ficha[df_ficha['SKU_Produto'] == sku_selecionado]['Nome_Produto'].iloc[0]
            st.info(f"**Produto Selecionado:** {nome_produto}")
            
        with col2:
            st.subheader("Meta")
            qtd_produzir = st.number_input("Quantidade a Produzir (peças):", min_value=1, value=50, step=5)

        st.markdown("---")
        
        # O botão mágico de cálculo (MRP)
        if st.button("🚀 Calcular Necessidade de Materiais (Explosão)", type="primary"):
            st.subheader("2. Lista de Compras / Separação (MRP)")
            
            # Filtra a ficha técnica só para o produto escolhido
            df_mrp = df_ficha[df_ficha['SKU_Produto'] == sku_selecionado].copy()
            
            # A Matemática: Insumo Unitário X Quantidade que quero produzir
            df_mrp['Necessidade Total'] = df_mrp['Quantidade'] * qtd_produzir
            
            # Organiza as colunas para ficar bonito na tela
            df_mrp_view = df_mrp[['Insumo', 'Quantidade', 'Necessidade Total', 'Unidade']].rename(
                columns={'Quantidade': 'Consumo por Peça'}
            )
            
            # Mostra a tabela na tela
            st.dataframe(df_mrp_view, use_container_width=True, hide_index=True)
            
            st.info("💡 Dica: Verifique no seu estoque físico se você tem o valor da coluna 'Necessidade Total' antes de iniciar a produção.")
            
    else:
        st.error("⚠️ Não encontramos a aba **'Ficha_Tecnica'** na sua planilha (ou ela está vazia).")
        st.markdown("""
        **Como resolver:**
        1. Abra sua planilha do Google.
        2. Crie uma aba chamada exatamente `Ficha_Tecnica`.
        3. Crie as colunas: `SKU_Produto`, `Nome_Produto`, `Insumo`, `Quantidade`, `Unidade`.
        4. Cadastre a receita de pelo menos um produto e atualize esta página.
        """)

# -----------------------------------------
# OUTROS MÓDULOS (Produtos / Configurações / etc)
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
    st.title(submenu.replace("⚙️ ", "").replace("📦 ", "").replace("👗 ", "").replace("💰 ", "").replace("🧾 ", "").replace("🛒 ", "").replace("👥 ", ""))
    st.info("Este módulo está em construção. Em breve estará disponível na Amariti ERP!")
