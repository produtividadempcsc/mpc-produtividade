import auth
import streamlit as st
from sidebar import build_sidebar
import ui_utils
from components import admin_tabs as tabs

auth.auth_guard()

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
if st.session_state.get("active_perfil") != "Administrador":
    st.error("🚫 Você não tem permissão para acessar esta página.")
    st.stop()
# ==============================================================================

st.session_state.active_page = "Administração"
build_sidebar()

# CSS Profissional com as cores do sistema
ui_utils.load_css("styles/admin.css")

st.title("🏛️ Painel de Administração")

admin_tabs = st.tabs([
    "📦 Tipos de Produto", 
    "📅 Gerenciar Feriados", 
    "🌴 Afastamento Global", 
    "💾 Gerenciar Backup", 
    "📊 Relatório Mensal",
    "⚖️ Relatório Corregedoria",
    "⚙️ Configurações Gerais"
])

# --- ABA GERENCIAR TIPOS DE PRODUTO ---
with admin_tabs[0]:
    tabs.render_tab_produtos()

# --- ABA GERENCIAR FERIADOS ---
with admin_tabs[1]:
    tabs.render_tab_feriados()

# --- ABA AFASTAMENTO GLOBAL ---
with admin_tabs[2]:
    tabs.render_tab_afastamentos()

# --- ABA GERENCIAR BACKUP ---
with admin_tabs[3]:
    tabs.render_tab_backup()

# --- ABA RELATÓRIO MENSAL ---
with admin_tabs[4]:
    tabs.render_tab_relatorios_mensais()

# --- ABA RELATÓRIO CORREGEDORIA ---
with admin_tabs[5]:
    tabs.render_tab_corregedoria()

# --- ABA CONFIGURAÇÕES GERAIS ---
with admin_tabs[6]:
    tabs.render_tab_configuracoes()
