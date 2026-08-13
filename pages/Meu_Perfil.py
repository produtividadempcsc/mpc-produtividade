import streamlit as st
import bcrypt
from sidebar import build_sidebar

# Módulos do projeto
import auth
from db_compat import get_user_by_id, update_user, hash_password

auth.auth_guard()

# Importando a função de carregar CSS no topo ou chamando-a aqui
import ui_utils
ui_utils.load_css("style.css")

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