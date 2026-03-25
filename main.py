import streamlit as st
import gspread
import json
import pandas as pd

# Configuração da página
st.set_page_config(page_title="ERP Amariti", page_icon="🚀", layout="wide")

st.title("🚀 Sistema de Gestão - Amariti")

# Tentando abrir o cofre e conectar no Google
try:
    # Pega a senha que guardamos no painel do Streamlit
    credenciais_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    
    # Usa a senha para conectar
    gc = gspread.service_account_from_dict(credenciais_dict)
    
    st.success("🟢 Motor conectado! O App já tem acesso oficial ao Google Sheets da Amariti!")
    
except Exception as e:
    st.error(f"🔴 Opa, algo deu errado na conexão: {e}")

# Criando abas para o futuro
aba1, aba2, aba3 = st.tabs(["📊 Financeiro", "👗 PCP / Costureiras", "⚙️ Custos e Impostos"])

with aba1:
    st.info("Os dados da sua planilha aparecerão aqui no próximo passo!")

with aba2:
    st.info("Aqui a costureira vai dar baixa na produção do dia.")

with aba3:
    st.info("Aqui você vai cadastrar o custo de cada produto para abater da margem.")
