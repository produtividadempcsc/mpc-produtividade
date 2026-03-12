import streamlit as st
import auth
from sidebar import build_sidebar
from utils.ui import load_logo

# --- INICIALIZAÇÃO DO SUPABASE ---
# O banco de dados já existe no Supabase, não precisa de create_database()
from supabase_client import is_client_initialized

st.set_page_config(
    page_title="MPC/SC Produtividade", 
    page_icon="⚖️", 
    layout="wide",
)

# --- WORKER EM BACKGROUND (DESATIVADO) ---
# Os jobs foram migrados para Supabase Edge Functions + pg_cron.
# update-statuses: a cada 1h | notify-deadlines: 08:00 | auto-backup: 23:00
# NÃO é necessário iniciar scheduler aqui.

from ui_utils import load_css

# CSS Profissional para o Sistema MPC/SC
def apply_professional_styling():
    load_css("style.css")

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