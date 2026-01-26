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

# CSS personalizado para layout profissional
st.markdown("""
<style>
/* Variáveis CSS para as cores do sistema */
:root {
    --primary-color: #9E0520;
    --background-color: #E9E3DF;
    --secondary-background: #9CAFAA;
    --text-color: #000000;
    --white: #FFFFFF;
    --light-gray: #F5F5F5;
    --shadow: rgba(0, 0, 0, 0.1);
}

/* Estilo para o container principal */
.manual-container {
    background: linear-gradient(135deg, var(--background-color) 0%, var(--light-gray) 100%);
    border-radius: 15px;
    padding: 2rem;
    margin: 1rem 0;
    box-shadow: 0 8px 25px var(--shadow);
    border: 1px solid rgba(158, 5, 32, 0.1);
}

/* Header do manual */
.manual-header {
    text-align: center;
    padding: 2rem 0;
    background: linear-gradient(135deg, var(--primary-color), #B91E3A);
    color: var(--white);
    border-radius: 12px;
    margin-bottom: 2rem;
    box-shadow: 0 4px 15px rgba(158, 5, 32, 0.3);
}

.manual-header h1 {
    font-size: 2.5rem;
    font-weight: 700;
    margin: 0;
    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
}

.manual-header .subtitle {
    font-size: 1.1rem;
    font-weight: 300;
    margin-top: 0.5rem;
    opacity: 0.9;
}

/* Card de informações do perfil */
.profile-card {
    background: var(--white);
    border-radius: 12px;
    padding: 1.5rem;
    margin: 1.5rem 0;
    border-left: 5px solid var(--primary-color);
    box-shadow: 0 4px 12px var(--shadow);
    display: flex;
    align-items: center;
    gap: 1rem;
}

.profile-icon {
    width: 60px;
    height: 60px;
    background: linear-gradient(135deg, var(--secondary-background), #B5C7C2);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    color: var(--primary-color);
    flex-shrink: 0;
}

.profile-info h3 {
    color: var(--primary-color);
    margin: 0;
    font-size: 1.3rem;
    font-weight: 600;
}

.profile-info p {
    margin: 0.5rem 0 0 0;
    color: var(--text-color);
    opacity: 0.8;
}

/* Container do conteúdo do manual */
.manual-content {
    background: var(--white);
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 4px 12px var(--shadow);
    border: 1px solid rgba(156, 175, 170, 0.2);
    line-height: 1.8;
}

.manual-content h1, .manual-content h2, .manual-content h3 {
    color: var(--primary-color);
    border-bottom: 2px solid var(--secondary-background);
    padding-bottom: 0.5rem;
    margin-top: 2rem;
    margin-bottom: 1rem;
}

.manual-content h1 {
    font-size: 1.8rem;
}

.manual-content h2 {
    font-size: 1.5rem;
}

.manual-content h3 {
    font-size: 1.3rem;
}

.manual-content p {
    margin: 1rem 0;
    text-align: justify;
}

.manual-content ul, .manual-content ol {
    margin: 1rem 0;
    padding-left: 2rem;
}

.manual-content li {
    margin: 0.5rem 0;
}

.manual-content code {
    background: var(--background-color);
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-family: 'Courier New', monospace;
}

.manual-content blockquote {
    border-left: 4px solid var(--secondary-background);
    background: var(--light-gray);
    margin: 1rem 0;
    padding: 1rem 1.5rem;
    border-radius: 0 8px 8px 0;
}

/* Card de erro/aviso estilizado */
.error-card {
    background: linear-gradient(135deg, #ffebee, #ffcdd2);
    border: 1px solid #f44336;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    margin: 2rem 0;
}

.error-card h3 {
    color: #c62828;
    margin-top: 0;
}

.warning-card {
    background: linear-gradient(135deg, #fff3e0, #ffe0b2);
    border: 1px solid #ff9800;
    border-radius: 12px;
    padding: 2rem;
    text-align: center;
    margin: 2rem 0;
}

.warning-card h3 {
    color: #ef6c00;
    margin-top: 0;
}

/* Animações suaves */
.manual-container, .profile-card, .manual-content {
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.manual-container:hover, .profile-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 12px 30px var(--shadow);
}

/* Responsividade */
@media (max-width: 768px) {
    .manual-container {
        padding: 1rem;
        margin: 0.5rem 0;
    }
    
    .manual-header h1 {
        font-size: 2rem;
    }
    
    .profile-card {
        flex-direction: column;
        text-align: center;
    }
    
    .manual-content {
        padding: 1rem;
    }
}
</style>
""", unsafe_allow_html=True)

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