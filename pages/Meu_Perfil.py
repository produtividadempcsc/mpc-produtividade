import streamlit as st
import bcrypt
from sidebar import build_sidebar

# Módulos do projeto
import auth
from db_compat import get_user_by_id, update_user, hash_password

auth.auth_guard()

# CSS personalizado para layout profissional
st.markdown("""
<style>
    /* Reset e configurações gerais */
    .main > div {
        padding-top: 2rem;
    }
    
    /* Título principal */
    .profile-title {
        color: #9E0520;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-align: center;
        border-bottom: 3px solid #9E0520;
        padding-bottom: 1rem;
        margin-bottom: 2rem;
    }
    
    /* Subtítulo */
    .profile-subtitle {
        color: #666;
        font-size: 1.1rem;
        text-align: center;
        margin-bottom: 3rem;
        font-style: italic;
    }
    
    /* Containers das seções */
    .section-container {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        border: 2px solid #9CAFAA;
        border-radius: 15px;
        padding: 2rem;
        margin: 2rem 0;
        box-shadow: 0 4px 12px rgba(158, 5, 32, 0.1);
        transition: all 0.3s ease;
    }
    
    .section-container:hover {
        box-shadow: 0 6px 20px rgba(158, 5, 32, 0.15);
        transform: translateY(-2px);
    }
    
    /* Cabeçalhos das seções */
    .section-header {
        color: #9E0520;
        font-size: 1.5rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .section-icon {
        background: linear-gradient(135deg, #9E0520, #c41e3a);
        color: white;
        width: 40px;
        height: 40px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.2rem;
    }
    
    /* Formulários */
    .stForm {
        background: #ffffff;
        border: 1px solid #9CAFAA;
        border-radius: 10px;
        padding: 1.5rem;
        margin-top: 1rem;
    }
    
    /* Inputs */
    .stTextInput > div > div > input {
        border: 2px solid #9CAFAA;
        border-radius: 8px;
        padding: 0.75rem;
        font-size: 1rem;
        transition: all 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #9E0520;
        box-shadow: 0 0 0 2px rgba(158, 5, 32, 0.1);
    }
    
    /* Labels */
    .stTextInput > label {
        color: #333;
        font-weight: 500;
        font-size: 1rem;
        margin-bottom: 0.5rem;
    }
    
    /* Botões */
    .stFormSubmitButton > button {
        background: linear-gradient(135deg, #9E0520, #c41e3a);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
        cursor: pointer;
        width: 100%;
    }
    
    .stFormSubmitButton > button:hover {
        background: linear-gradient(135deg, #c41e3a, #9E0520);
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(158, 5, 32, 0.3);
    }
    
    /* Checkboxes */
    .stCheckbox > label {
        color: #333;
        font-weight: 500;
    }
    
    .stCheckbox > label > span[data-baseweb="checkbox"] {
        border-color: #9CAFAA;
    }
    
    .stCheckbox > label > span[data-baseweb="checkbox"][data-checked="true"] {
        background-color: #9E0520;
        border-color: #9E0520;
    }
    
    /* Alertas e mensagens */
    .stAlert {
        border-radius: 10px;
        border: none;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }
    
    .stSuccess {
        background: linear-gradient(135deg, #28a745, #20c997);
        color: white;
    }
    
    .stError {
        background: linear-gradient(135deg, #dc3545, #e74c3c);
        color: white;
    }
    
    .stWarning {
        background: linear-gradient(135deg, #ffc107, #fd7e14);
        color: #212529;
    }
    
    .stInfo {
        background: linear-gradient(135deg, #17a2b8, #6f42c1);
        color: white;
    }
    
    /* Separadores */
    .section-divider {
        height: 2px;
        background: linear-gradient(to right, transparent, #9CAFAA, transparent);
        margin: 2rem 0;
        border: none;
    }
    
    /* Grupos de notificação */
    .notification-group {
        background: #f8f9fa;
        border: 1px solid #9CAFAA;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    .notification-group-title {
        color: #9E0520;
        font-weight: 600;
        font-size: 1.1rem;
        margin-bottom: 0.5rem;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .section-container {
            padding: 1rem;
            margin: 1rem 0;
        }
        
        .profile-title {
            font-size: 2rem;
        }
        
        .section-header {
            font-size: 1.3rem;
        }
    }
</style>
""", unsafe_allow_html=True)

st.session_state.active_page = "Meu Perfil"
build_sidebar()

# Título principal com estilo
st.markdown('<h1 class="profile-title">👤 Meu Perfil</h1>', unsafe_allow_html=True)
st.markdown('<p class="profile-subtitle">Gerencie suas informações pessoais, altere sua senha e configure suas preferências de notificação.</p>', unsafe_allow_html=True)

# Busca os dados do usuário logado (pelo ID original, não o de substituto)
user_data = get_user_by_id(st.session_state.user_id)
if not user_data:
    st.error("Usuário não encontrado no banco de dados.")
    st.stop()

try:
    # --- SEÇÃO 1: SUAS INFORMAÇÕES ---
    st.markdown("""
    <div class="section-container">
        <div class="section-header">
            <div class="section-icon">📋</div>
            Informações Pessoais
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("update_user_info_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            novo_nome = st.text_input("👤 Nome Completo", value=user_data.get('nome_completo') or "", help="Digite seu nome completo")
            novo_email = st.text_input("📧 E-mail", value=user_data.get('email') or "", help="Endereço de e-mail para notificações")
        
        with col2:
            novo_telefone = st.text_input("📱 Telefone", value=user_data.get('telefone') or "", help="Número de telefone para contato")
            st.write("")  # Espaçamento
            st.write("")  # Espaçamento
        
        if st.form_submit_button("💾 Salvar Informações Pessoais"):
            if not novo_nome.strip():
                st.warning("⚠️ O nome completo é obrigatório.")
            elif not novo_email.strip():
                st.warning("⚠️ O e-mail é obrigatório.")
            else:
                update_user(st.session_state.user_id, {
                    "nome_completo": novo_nome.strip(),
                    "email": novo_email.strip(),
                    "telefone": novo_telefone.strip()
                })
                st.session_state.user_nome = novo_nome.strip()  # Atualiza o nome na sidebar
                st.success("✅ Informações atualizadas com sucesso!")
                st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

    # --- SEÇÃO 2: ALTERAR SENHA ---
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="section-container">
        <div class="section-header">
            <div class="section-icon">🔒</div>
            Alterar Senha
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("update_password_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            senha_atual = st.text_input("🔐 Senha Atual", type="password", help="Digite sua senha atual para confirmar")
            nova_senha = st.text_input("🆕 Nova Senha", type="password", help="Mínimo de 6 caracteres")
        
        with col2:
            confirmar_nova_senha = st.text_input("✅ Confirmar Nova Senha", type="password", help="Digite novamente a nova senha")
            
            # Indicador de força da senha
            if nova_senha:
                forca = len(nova_senha)
                if forca < 6:
                    st.markdown("🔴 **Senha muito fraca** (mínimo 6 caracteres)")
                elif forca < 8:
                    st.markdown("🟡 **Senha fraca**")
                elif forca < 12:
                    st.markdown("🟢 **Senha boa**")
                else:
                    st.markdown("💚 **Senha forte**")
        
        if st.form_submit_button("🔄 Alterar Senha"):
            if not all([senha_atual, nova_senha, confirmar_nova_senha]):
                st.warning("⚠️ Preencha todos os campos da senha.")
            elif not bcrypt.checkpw(senha_atual.encode('utf-8'), user_data.get('senha_hash', '').encode('utf-8')):
                st.error("❌ A 'Senha Atual' está incorreta.")
            elif nova_senha != confirmar_nova_senha:
                st.error("❌ A 'Nova Senha' e a 'Confirmação' não são iguais.")
            elif len(nova_senha) < 6:
                st.warning("⚠️ A nova senha deve ter no mínimo 6 caracteres.")
            else:
                update_user(st.session_state.user_id, {"senha_hash": hash_password(nova_senha)})
                st.success("✅ Senha alterada com sucesso!")
                st.info("ℹ️ Você pode continuar navegando normalmente.")
    
    st.markdown('</div>', unsafe_allow_html=True)

    # --- SEÇÃO 3: PREFERÊNCIAS DE NOTIFICAÇÃO ---
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    
    st.markdown("""
    <div class="section-container">
        <div class="section-header">
            <div class="section-icon">🔔</div>
            Preferências de Notificação por E-mail
        </div>
        <p style="color: #666; margin-bottom: 1.5rem;">Escolha quais notificações você deseja receber em seu e-mail cadastrado.</p>
    """, unsafe_allow_html=True)
    
    with st.form("update_notification_prefs_form"):
        # Eventos de Processos
        st.markdown('<div class="notification-group-title">📨 Eventos de Processos</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            pref_novo = st.checkbox("📥 Novo processo atribuído a mim", 
                                  value=user_data.get('notifica_email_novo_processo', True),
                                  help="Receber notificação quando um novo processo for atribuído")
        with col2:
            pref_devolvido = st.checkbox("🔄 Processo devolvido para ajustes", 
                                       value=user_data.get('notifica_email_processo_devolvido', True),
                                       help="Receber notificação quando um processo for devolvido")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Notificações para Gestores
        st.markdown('<div class="notification-group-title">👥 Notificações para Gestores</div>', unsafe_allow_html=True)
        
        # Desabilita checkboxes para quem não tem o perfil relevante
        user_perfil = user_data.get('perfil', '')
        is_gestor = user_perfil in ["Chefe de Gabinete", "Administrador"]
        is_procurador = user_perfil in ["Procurador", "Administrador"]

        col1, col2 = st.columns(2)
        with col1:
            pref_concluido = st.checkbox("✅ Processo concluído pela equipe", 
                                       value=user_data.get('notifica_email_processo_concluido', True), 
                                       help="Apenas para Chefes de Gabinete - Notificação quando servidor da equipe conclui processo", 
                                       disabled=not is_gestor)
        with col2:
            pref_analise = st.checkbox("📊 Processo pronto para análise final", 
                                     value=user_data.get('notifica_email_pronto_analise', True), 
                                     help="Apenas para Procuradores - Notificação quando processo está pronto para análise", 
                                     disabled=not is_procurador)
        
        if not is_gestor:
            st.info("ℹ️ Notificações de gestão disponíveis apenas para Chefes de Gabinete")
        if not is_procurador:
            st.info("ℹ️ Notificações de análise disponíveis apenas para Procuradores")
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Lembretes Automáticos
        st.markdown('<div class="notification-group-title">⏰ Lembretes Automáticos</div>', unsafe_allow_html=True)
        
        pref_prazos = st.checkbox("🚨 Lembretes de prazos (hoje/atrasados)", 
                                value=user_data.get('notifica_email_prazos', True),
                                help="Receber lembretes automáticos sobre prazos que vencem hoje ou estão atrasados")
        
        st.markdown('</div>', unsafe_allow_html=True)

        if st.form_submit_button("💾 Salvar Preferências de Notificação"):
            update_user(st.session_state.user_id, {
                "notifica_email_novo_processo": pref_novo,
                "notifica_email_processo_devolvido": pref_devolvido,
                "notifica_email_processo_concluido": pref_concluido,
                "notifica_email_pronto_analise": pref_analise,
                "notifica_email_prazos": pref_prazos
            })
            st.success("✅ Suas preferências de notificação foram salvas!")
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"❌ Ocorreu um erro ao carregar a página: {e}")