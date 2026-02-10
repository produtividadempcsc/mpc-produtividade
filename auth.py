import streamlit as st
import bcrypt

# Chave da API Gemini recuperada dos segredos
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except (KeyError, FileNotFoundError):
    # Fallback ou erro amigável se o segredo não existir
    st.error("Chave da API Gemini não encontrada em .streamlit/secrets.toml")
    GEMINI_API_KEY = None

from datetime import date, datetime
import secrets
import string

# Import Supabase client
from supabase_client import supabase, select_first, update_by_id, QueryBuilder

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def get_user_by_login(login: str):
    """
    Busca usuário por login via Supabase REST API.
    Retorna dict do usuário ou None.
    """
    return select_first("usuarios", "login", login)

def login_user(login, password):
    """
    Valida as credenciais do usuário contra o banco de dados.
    Se bem-sucedido, configura o session_state.
    Retorna True para sucesso, False para falha.
    """
    try:
        user = get_user_by_login(login)
        if user and bcrypt.checkpw(password.encode('utf-8'), user['senha_hash'].encode('utf-8')):
            # Verificar se usuário está ativo
            if not user.get('ativo', True):
                return False

            # Credenciais válidas, configurar a sessão
            st.session_state['is_logged_in'] = True
            st.session_state['user_id'] = user['id']
            st.session_state['user_login'] = user['login']
            st.session_state['user_nome'] = user['nome_completo']
            
            # Executa o setup pós-login para definir perfil, etc.
            post_login_setup(login)
            return True
        return False
        return False
    except Exception as e:
        print(f"[AUTH ERROR] Falha crítica de conexão ou consulta: {e}")
        import traceback
        traceback.print_exc()
        return False

def logout_user():
    """
    Limpa o session_state para deslogar o usuário.
    """
    keys_to_clear = [
        'is_logged_in', 'user_id', 'user_login', 'user_nome',
        'original_perfil', 'is_substituto', 'perfis_disponiveis',
        'active_perfil_nome', 'active_perfil', 'active_user_id',
        'authenticated' # Limpa a chave antiga também, por segurança
    ]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

def auth_guard():
    """
    Função de guarda para ser chamada no início de cada página protegida.
    Verifica se o usuário está logado. Se não, redireciona para a página de login.
    """
    if not st.session_state.get('is_logged_in'):
        st.switch_page("app.py")

def post_login_setup(username):
    """
    Configura dados adicionais da sessão após um login bem-sucedido.
    """
    try:
        user = get_user_by_login(username)
        if user:
            # Atualizar último acesso
            update_by_id("usuarios", user['id'], {"ultimo_acesso": datetime.now().isoformat()})
            
            st.session_state.original_perfil = user['perfil']
            substituicao = check_for_substitution(user['id'])
            
            if substituicao:
                # Buscar chefe titular
                chefe_titular = select_first("usuarios", "id", substituicao['id_chefe_titular'])
                if chefe_titular:
                    st.session_state.is_substituto = True
                    st.session_state.perfis_disponiveis = {
                        user['perfil']: user['id'],
                        f"Chefe de Gabinete (Substituto)": chefe_titular['id']
                    }
                    st.session_state.active_perfil_nome = f"Chefe de Gabinete (Substituto)"
                    st.session_state.active_perfil = "Chefe de Gabinete"
                    st.session_state.active_user_id = chefe_titular['id']
            else:
                st.session_state.is_substituto = False
                st.session_state.active_perfil = user['perfil']
                st.session_state.active_user_id = user['id']
    except Exception as e:
        print(f"[AUTH] Erro no post_login_setup: {e}")

def check_for_substitution(user_id):
    """
    Verifica se o usuário tem uma substituição ativa.
    """
    hoje = date.today().isoformat()
    
    substituicoes = QueryBuilder("substituicoes") \
        .eq("id_servidor_substituto", user_id) \
        .lte("data_inicio", hoje) \
        .gte("data_fim", hoje) \
        .execute()
    
    return substituicoes[0] if substituicoes else None

def generate_random_password(length=10):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

def reset_password(login: str):
    from utils.notifications import send_email_notification
    
    try:
        user = get_user_by_login(login)
        if not user:
            return False, "Login não encontrado."
        
        if not user.get('email'):
            return False, "Este usuário não possui um e-mail cadastrado. Por favor, entre em contato com o seu Chefe de Gabinete."

        new_password = generate_random_password()
        new_hash = hash_password(new_password)
        
        # Atualizar senha no banco
        update_by_id("usuarios", user['id'], {"senha_hash": new_hash})

        assunto = "Sua nova senha para o Sistema de Produtividade MPC/SC"
        corpo = f"""
        <p>Olá, {user['nome_completo']},</p>
        <p>Sua senha foi redefinida. Sua nova senha temporária é:</p>
        <p><b>{new_password}</b></p>
        <p>Por favor, faça login com esta nova senha e altere-a assim que possível na seção 'Meu Perfil'.</p>
        <br>
        <p>Atenciosamente,</p>
        <p>Sistema de Produtividade MPC/SC</p>
        """
        # Envia o e-mail diretamente
        send_email_notification(user['email'], assunto, corpo)
        
        # Return success immediately to the user
        return True, "Uma nova senha foi enviada para o e-mail cadastrado. A entrega pode levar alguns minutos."

    except Exception as e:
        return False, f"Ocorreu um erro inesperado: {e}"
