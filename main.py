import streamlit as st

# Configuração da página
st.set_page_config(page_title="ERP Amariti", page_icon="🚀", layout="wide")

# Título do App
st.title("🚀 Sistema de Gestão - Amariti")
st.subheader("Bem-vindo ao seu novo painel de controle, Renan!")

st.write("A fundação do nosso App foi criada com sucesso no GitHub!")

# Criando abas para o futuro
aba1, aba2, aba3 = st.tabs(["📊 Financeiro", "👗 PCP / Costureiras", "⚙️ Custos e Impostos"])

with aba1:
    st.info("Aqui entrarão os gráficos de faturamento e lucro líquido.")

with aba2:
    st.info("Aqui a costureira vai dar baixa na produção do dia.")

with aba3:
    st.info("Aqui você vai cadastrar o custo de cada produto.")
