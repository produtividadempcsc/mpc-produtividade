import streamlit as st
import auth
from sidebar import build_sidebar
import os
from utils.ui import load_logo

# --- INICIALIZAÇÃO DO SUPABASE ---
# O banco de dados já existe no Supabase, não precisa de create_database()
from supabase_client import supabase, is_client_initialized

st.set_page_config(
    page_title="MPC/SC Produtividade", 
    page_icon="⚖️", 
    layout="wide",
)

# --- WORKER EM BACKGROUND (DESATIVADO) ---
# Os jobs foram migrados para Supabase Edge Functions + pg_cron.
# update-statuses: a cada 1h | notify-deadlines: 08:00 | auto-backup: 23:00
# NÃO é necessário iniciar scheduler aqui.

# CSS Profissional para o Sistema MPC/SC
def apply_professional_styling():
    st.markdown("""
    <style>
    /* Importar fonte profissional */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Variáveis de cores do sistema MPC/SC */
    :root {
        --primary-color: #9E0520;
        --background-color: #E9E3DF;
        --secondary-bg: #9CAFAA;
        --text-color: #000000;
        --white: #ffffff;
        --light-gray: #f8f9fa;
        --shadow: rgba(0, 0, 0, 0.1);
    }
    
    /* Reset e configurações globais */
    .main {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, var(--background-color) 0%, #f5f1ed 100%);
        min-height: 100vh;
    }
    
    /* Esconder elementos padrão do Streamlit */
    [data-testid='stSidebarNav'] {
        display: none;
    }
    
    .stApp > header {
        background: transparent;
    }
    
    /* Container principal de login */
    .login-container {
        max-width: 500px;
        margin: 0 auto;
        padding: 2rem;
        background: var(--white);
        border-radius: 16px;
        box-shadow: 0 20px 40px var(--shadow);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        margin-top: 5vh;
    }
    
    /* Logo container */
    .logo-container {
        text-align: center;
        margin-bottom: 3rem;
        padding: 2rem;
        background: linear-gradient(135deg, var(--primary-color), #b8062a);
        border-radius: 16px;
        box-shadow: 0 12px 24px rgba(158, 5, 32, 0.4);
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    .logo-container img {
        border-radius: 12px;
        box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
        max-width: 100%;
        height: auto;
        display: block;
        margin: 0 auto;
    }
    
    /* Títulos e headers */
    .main-title {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
        color: var(--primary-color);
        text-align: center;
        margin: 2rem 0;
        text-shadow: 2px 2px 4px var(--shadow);
    }
    
    .welcome-title {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1.8rem;
        color: var(--primary-color);
        text-align: center;
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: linear-gradient(135deg, var(--white), var(--light-gray));
        border-radius: 12px;
        box-shadow: 0 4px 8px var(--shadow);
        border-left: 4px solid var(--primary-color);
    }
    
    .section-header {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 1.4rem;
        color: var(--primary-color);
        margin: 1.5rem 0 1rem 0;
        padding: 0.5rem 0;
        border-bottom: 2px solid var(--secondary-bg);
    }
    
    /* Formulários */
    .stForm {
        background: var(--white);
        padding: 2rem;
        border-radius: 12px;
        border: 1px solid var(--secondary-bg);
        box-shadow: 0 4px 12px var(--shadow);
        margin-bottom: 1.5rem;
    }
    
    /* Inputs */
    .stTextInput > div > div > input {
        font-family: 'Inter', sans-serif;
        border: 2px solid var(--secondary-bg);
        border-radius: 8px;
        padding: 12px 16px;
        font-size: 16px;
        transition: all 0.3s ease;
        background: var(--white);
    }
    
    .stTextInput > div > div > input:focus {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 3px rgba(158, 5, 32, 0.1);
        outline: none;
    }
    
    /* Labels dos inputs */
    .stTextInput > label {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        color: var(--text-color);
        margin-bottom: 0.5rem;
        font-size: 14px;
    }
    
    /* Botões */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color), #b8062a);
        color: var(--white);
        border: none;
        border-radius: 8px;
        padding: 12px 24px;
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        font-size: 16px;
        transition: all 0.3s ease;
        width: 100%;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(158, 5, 32, 0.3);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(158, 5, 32, 0.4);
        background: linear-gradient(135deg, #b8062a, var(--primary-color));
    }
    
    .stButton > button:active {
        transform: translateY(0);
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        font-family: 'Inter', sans-serif;
        font-weight: 500;
        color: var(--primary-color);
        background: var(--light-gray);
        border-radius: 8px;
        border: 1px solid var(--secondary-bg);
    }
    
    .streamlit-expanderContent {
        background: var(--white);
        border: 1px solid var(--secondary-bg);
        border-radius: 8px;
        padding: 1rem;
    }
    
    /* Mensagens de status */
    .stSuccess {
        background: linear-gradient(135deg, #d4edda, #c3e6cb);
        border: 1px solid #a3d5a1;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Inter', sans-serif;
    }
    
    .stError {
        background: linear-gradient(135deg, #f8d7da, #f5c6cb);
        border: 1px solid #f1b0b7;
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Inter', sans-serif;
    }
    
    .stInfo {
        background: linear-gradient(135deg, var(--secondary-bg), #b8c5c1);
        border: 1px solid var(--secondary-bg);
        border-radius: 8px;
        padding: 1rem;
        font-family: 'Inter', sans-serif;
        color: var(--text-color);
    }
    
    /* Spinner customizado */
    .stSpinner > div {
        border-color: var(--primary-color) !important;
    }
    
    /* Cards de boas-vindas */
    .welcome-card {
        background: linear-gradient(135deg, var(--white), var(--light-gray));
        border: 1px solid var(--secondary-bg);
        border-radius: 16px;
        padding: 2rem;
        margin: 1.5rem 0;
        box-shadow: 0 8px 20px var(--shadow);
        text-align: center;
    }
    
    .welcome-card h1 {
        color: var(--primary-color);
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        margin-bottom: 1rem;
    }
    
    .welcome-card p {
        color: var(--text-color);
        font-family: 'Inter', sans-serif;
        font-size: 1.1rem;
        line-height: 1.6;
    }
    
    /* Perfil info */
    .profile-info {
        background: linear-gradient(135deg, var(--secondary-bg), #b8c5c1);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin: 1rem 0;
        border-left: 4px solid var(--primary-color);
        font-family: 'Inter', sans-serif;
        font-weight: 500;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .login-container {
            margin: 1rem;
            padding: 1.5rem;
        }
        
        .main-title {
            font-size: 2rem;
        }
        
        .welcome-title {
            font-size: 1.5rem;
        }
    }
    
    /* Animações sutis */
    .login-container, .welcome-card, .stForm {
        animation: fadeInUp 0.6s ease-out;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: var(--text-color);
        font-family: 'Inter', sans-serif;
        font-size: 0.9rem;
        margin-top: 3rem;
        border-top: 1px solid var(--secondary-bg);
    }
    </style>
    """, unsafe_allow_html=True)

# Aplicar estilos profissionais
apply_professional_styling()

# --- PWA (Progressive Web App) ---
st.markdown("""
<link rel="manifest" href="./manifest.json">
<meta name="theme-color" content="#D32F2F">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="MPC Produtividade">
<link rel="apple-touch-icon" href="./logo_mpcsc.jpg">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script>
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('./service-worker.js')
            .then(function(registration) {
                console.log('[PWA] Service Worker registrado:', registration.scope);
            })
            .catch(function(error) {
                console.log('[PWA] Falha ao registrar Service Worker:', error);
            });
    });
}
</script>
""", unsafe_allow_html=True)

def display_reset_password_form():
    """Exibe o formulário para resetar a senha."""
    with st.expander("🔐 Esqueceu sua senha?"):
        st.markdown('<div class="section-header">Redefinição de Senha</div>', unsafe_allow_html=True)
        with st.form("reset_password_form"):
            login_to_reset = st.text_input("Digite seu login para redefinir a senha", placeholder="Seu login aqui...")
            submitted = st.form_submit_button("🔄 Redefinir Senha")
            if submitted:
                if not login_to_reset:
                    st.error("⚠️ Por favor, insira um login.")
                else:
                    with st.spinner("🔄 Processando redefinição..."):
                        success, message = auth.reset_password(login_to_reset)
                    if success:
                        st.success(f"✅ {message}")
                    else:
                        st.error(f"❌ {message}")

def build_login_form():
    """Constrói e gerencia o formulário de login."""
    
    # Logo
    logo = load_logo()
    if logo:
        st.image(logo, width=400)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Formulário de login
    with st.form("login_form"):
        st.markdown('<div class="section-header">🔐 Acesso ao Sistema</div>', unsafe_allow_html=True)
        
        # Verificar configuração crítica antes de permitir login
        if not is_client_initialized():
            st.error("⚠️ ERRO DE CONFIGURAÇÃO: Não foi possível conectar ao banco de dados.")
            st.warning("Verifique se as variáveis SUPABASE_URL e SUPABASE_KEY estão configuradas corretamente nas Secrets do Streamlit ou no arquivo .env.")
            st.stop()

        login = st.text_input("👤 Login", placeholder="Digite seu login")
        password = st.text_input("🔑 Senha", type="password", placeholder="Digite sua senha")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submitted = st.form_submit_button("🚀 Entrar no Sistema")

        if submitted:
            if not login or not password:
                st.error("⚠️ Por favor, preencha todos os campos.")
            else:
                with st.spinner("🔄 Verificando credenciais..."):
                    if auth.login_user(login, password):
                        st.success("✅ Login realizado com sucesso!")
                        st.rerun()  # Força o rerender da página para o estado 'logado'
                    else:
                        st.error("❌ Login ou senha incorretos. ")
                        st.info("Se o erro persistir, verifique os logs para detalhes de conexão.")
    
    # Formulário de reset de senha
    display_reset_password_form()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown(
        '<div class="footer">© 2025 Ministério Público de Contas do Estado de Santa Catarina - Todos os direitos reservados</div>', 
        unsafe_allow_html=True
    )

def run_authenticated_app():
    """Função que executa o app principal após o login."""
    st.session_state.active_page = "Início"
    build_sidebar()  # A sidebar não precisa mais do 'authenticator'
    
    # Card de boas-vindas
    st.markdown(f'<h1>🏠 Bem-vindo(a), {st.session_state.user_nome}!</h1>', unsafe_allow_html=True)
    st.markdown('<p>Selecione uma opção no menu à esquerda para começar a utilizar o sistema de produtividade.</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Informação do perfil
    if st.session_state.get('active_perfil'):
        st.markdown(
            f'<div class="profile-info">👤 Você está logado com o perfil de <strong>{st.session_state.active_perfil}</strong></div>', 
            unsafe_allow_html=True
        )

# --- GATEKEEPER PRINCIPAL ---
if not st.session_state.get('is_logged_in'):
    # Se não estiver logado, mostra o formulário de login
    st.markdown("<style>[data-testid='stSidebar'] {display: none;}</style>", unsafe_allow_html=True)
    build_login_form()
else:
    # Se estiver logado, executa o aplicativo principal
    run_authenticated_app()