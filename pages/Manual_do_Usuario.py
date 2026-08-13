import auth
import streamlit as st
import os
from sidebar import build_sidebar

auth.auth_guard()

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
# Define os perfis permitidos. Neste caso, todos podem acessar.
allowed_profiles = ["Administrador", "Chefe de Gabinete", "Servidor", "Procurador"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Você não tem permissão para acessar esta página.")
    st.stop()
# ==============================================================================

st.session_state.active_page = "Manual do Usuário"
build_sidebar()

# CSS personalizado para layout profissional (Centralizado)
import ui_utils
ui_utils.load_css("style.css")

# Header principal com design profissional
st.markdown("""
<div class="manual-container">
    <div class="manual-header">
        <h1>📖 Manual do Usuário</h1>
        <div class="subtitle">Sistema de Gestão - Documentação Oficial</div>
    </div>
""", unsafe_allow_html=True)

# Pega o perfil ativo da sessão para saber qual manual exibir
perfil_ativo = st.session_state.active_perfil

# Mapeia perfis aos ícones e descrições
profile_info = {
    "Administrador": {
        "icon": "⚙️",
        "description": "Acesso completo ao sistema com privilégios administrativos"
    },
    "Chefe de Gabinete": {
        "icon": "👔",
        "description": "Gerenciamento estratégico e supervisão operacional"
    },
    "Servidor": {
        "icon": "👤",
        "description": "Acesso às funcionalidades operacionais do sistema"
    },
    "Procurador": {
        "icon": "⚖️",
        "description": "Acesso às funcionalidades jurídicas e processuais"
    }
}

# Card de informações do perfil
current_profile = profile_info.get(perfil_ativo, {"icon": "👤", "description": "Usuário do sistema"})
st.markdown(f"""
    <div class="profile-card">
        <div class="profile-icon">{current_profile['icon']}</div>
        <div class="profile-info">
            <h3>Perfil: {perfil_ativo}</h3>
            <p>{current_profile['description']}</p>
        </div>
    </div>
""", unsafe_allow_html=True)

# Mapeia o nome do perfil ao nome do arquivo .txt correspondente
manual_files = {
    "Administrador": "manual_administrador.txt",
    "Chefe de Gabinete": "manual_chefe_gabinete.txt",
    "Servidor": "manual_servidor.txt",
    "Procurador": "manual_procurador.txt"
}

# Obtém o caminho do arquivo para o perfil do usuário atual
file_path = manual_files.get(perfil_ativo)

if file_path and os.path.exists(file_path):
    try:
        # Lê o conteúdo do arquivo de texto
        with open(file_path, 'r', encoding='utf-8') as f:
            manual_content = f.read()
        
        # Container do conteúdo do manual
        st.markdown(f"""
            <div class="manual-content">
                {manual_content}
            </div>
        """, unsafe_allow_html=True)

    except Exception as e:
        st.markdown(f"""
            <div class="error-card">
                <h3>❌ Erro ao Carregar Manual</h3>
                <p>Ocorreu um erro ao ler o arquivo do manual: <strong>{e}</strong></p>
                <p>Entre em contato com o suporte técnico para resolver esta questão.</p>
            </div>
        """, unsafe_allow_html=True)
else:
    st.markdown(f"""
        <div class="warning-card">
            <h3>⚠️ Manual Não Encontrado</h3>
            <p>O arquivo do manual para o perfil <strong>'{perfil_ativo}'</strong> não foi encontrado.</p>
            <p>Arquivo esperado: <code>{file_path}</code></p>
            <p>Entre em contato com o administrador do sistema para disponibilizar a documentação.</p>
        </div>
    """, unsafe_allow_html=True)

# Fechamento do container principal
st.markdown("</div>", unsafe_allow_html=True)

# Rodapé informativo
st.markdown("""
---
<div style="text-align: center; color: #666; font-size: 0.9rem; padding: 1rem;">
    💡 <strong>Dica:</strong> Este manual é específico para o seu perfil de usuário. 
    Para dúvidas adicionais, consulte o suporte técnico.
</div>
""", unsafe_allow_html=True)