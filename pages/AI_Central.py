
import streamlit as st
import google.genai as genai
import auth
from sidebar import build_sidebar
import ui_utils
from components.ai_chat import render_chat_interface
from components.ai_valor import render_valor_fiscalizado
from components.ai_prompts import render_prompt_bank

# --- Autenticação e Guard Clause ---
auth.auth_guard()

# =====================================================================
# GUARD CLAUSE DE PERFIL
# =====================================================================
allowed_profiles = ["Servidor", "Chefe de Gabinete", "Procurador", "Administrador"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Você não tem permissão para acessar esta página.")
    st.stop()
# =====================================================================

st.session_state.active_page = "AI Central"
build_sidebar()

# Carregar CSS global e específicos
ui_utils.load_css()
ui_utils.load_css("styles/chat.css")
ui_utils.load_css("styles/ai_valor.css")
ui_utils.load_css("styles/prompt_bank.css")

# --- Configuração do Gemini (Novo SDK) ---
try:
    client = genai.Client(api_key=auth.get_gemini_api_key())
    # O modelo é especificado na chamada agora, mas podemos definir uma constante
    MODEL_ID = 'gemini-3.1-flash-lite-preview' # Atualizado para um modelo mais recente se possível, ou manter o equivalente
except Exception as e:
    st.error(f"Erro ao configurar o cliente Gemini. Verifique a chave da API em auth.py. Erro: {e}")
    st.stop()

# --- Funções Auxiliares do Chat ---
# --- Main Page Layout ---
st.title("🧠 Central de Inteligência Artificial")

tabs = st.tabs(["🤖 Chat Inteligente", "💰 Cálculo de Valor", "📚 Banco de Prompts"])

with tabs[0]:
    render_chat_interface(client, MODEL_ID)

with tabs[1]:
    render_valor_fiscalizado(client, MODEL_ID)

with tabs[2]:
    render_prompt_bank()
