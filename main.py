import streamlit as st
import gspread
import json
import pandas as pd

# Configuração da página
st.set_page_config(page_title="ERP Amariti", page_icon="🚀", layout="wide")

# --- CONEXÃO COM O GOOGLE ---
# Pegando as credenciais que salvamos nos Secrets do Streamlit
try:
    credenciais_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    gc = gspread.service_account_from_dict(credenciais_dict)
    
    # ID da sua planilha que você me passou
    ID_DA_PLANILHA = "1HaqFImRnQgIrL-6BlnsifIyUwSVRngaUujQAsqTKOZY"
    
    planilha = gc.open_by_key(ID_DA_PLANILHA)
    
    # Tenta abrir a aba do financeiro
    # Se o nome da aba na sua planilha for diferente de 'BD_Financeiro', mude o nome abaixo:
    aba_fin = planilha.worksheet("BD_Financeiro")
    
    dados = aba_fin.get_all_records()
    df = pd.DataFrame(dados)
    conexao_ok = True
except Exception as e:
    conexao_ok = False
    erro = str(e)

# --- INTERFACE DO APP ---
st.title("🚀 Sistema de Gestão - Amariti")

if conexao_ok:
    st.success("🟢 Conectado à planilha com sucesso!")
    
    aba1, aba2, aba3 = st.tabs(["📊 Financeiro", "👗 PCP / Costureiras", "⚙️ Custos e Impostos"])

    with aba1:
        st.subheader("Resumo de Vendas e Faturamento")
        
        if not df.empty:
            # Mostra os números principais (Ex: Total de linhas na planilha)
            col1, col2, col3 = st.columns(3)
            col1.metric("Total de Pedidos", f"{len(df)}")
            
            st.write("### Dados da Planilha (Últimos 20 registros)")
            # Mostra a tabela de dados
            st.dataframe(df.tail(20), use_container_width=True)
        else:
            st.warning("A aba 'BD_Financeiro' foi encontrada, mas parece estar vazia.")

else:
    st.error("🔴 Erro de Conexão")
    st.write(f"Detalhes do erro: {erro}")
    st.info("💡 Dica: Verifique se você compartilhou a planilha com o e-mail do robô (Editor)!")

with aba2:
    st.info("Aqui entrará o controle de produção das costureiras.")

with aba3:
    st.info("Aqui você poderá cadastrar os custos fixos e impostos.")
