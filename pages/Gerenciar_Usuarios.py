import auth
import streamlit as st
import pandas as pd
from sidebar import build_sidebar

# Módulos do projeto
from auth import hash_password
from db_compat import (
    get_all_users, create_user, delete_user, update_user,
    update_servidor_chefes, update_chefe_procuradores, update_chefe_superiores,
    toggle_user_active_status
)
from supabase_client import select_all, QueryBuilder

auth.auth_guard()

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
allowed_profiles = ["Administrador", "Chefe de Gabinete"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Você não tem permissão para acessar esta página.")
    st.stop()
# ==============================================================================

# CSS Personalizado para Layout Profissional
st.markdown("""
<style>
    /* Importar fonte profissional */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Variáveis CSS com as cores do sistema */
    :root {
        --primary-color: #9E0520;
        --background-color: #E9E3DF;
        --secondary-bg: #9CAFAA;
        --text-color: #000000;
        --white: #FFFFFF;
        --light-gray: #F8F9FA;
        --border-color: #DEE2E6;
        --success: #28A745;
        --warning: #FFC107;
        --danger: #DC3545;
        --shadow: rgba(0, 0, 0, 0.1);
    }
    
    /* Reset e configurações base */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        font-family: 'Inter', sans-serif;
    }
    
    /* Header principal */
    .main-header {
        background: linear-gradient(135deg, var(--primary-color) 0%, #B8062A 100%);
        color: white;
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 20px rgba(158, 5, 32, 0.15);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    
    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1.1rem;
        font-weight: 300;
    }
    
    /* Cards de seção */
    .section-card {
        background: var(--white);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 10px var(--shadow);
        border: 1px solid var(--border-color);
    }
    
    .section-card h3 {
        color: var(--primary-color);
        font-weight: 600;
        margin-bottom: 1rem;
        font-size: 1.4rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Tabela de usuários */
    .users-table-container {
        background: var(--white);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 2px 10px var(--shadow);
        margin-bottom: 2rem;
    }
    
    .users-table-header {
        background: var(--secondary-bg);
        padding: 1rem 1.5rem;
        color: var(--text-color);
        font-weight: 600;
        font-size: 1.2rem;
    }
    
    /* Formulários */
    .form-container {
        background: var(--white);
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 10px var(--shadow);
        border: 1px solid var(--border-color);
        margin-bottom: 1rem;
    }
    
    .form-header {
        background: var(--primary-color);
        color: white;
        padding: 1rem 1.5rem;
        margin: -1.5rem -1.5rem 1.5rem -1.5rem;
        border-radius: 12px 12px 0 0;
        font-weight: 600;
        font-size: 1.1rem;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    /* Botões personalizados */
    .stButton > button {
        background: var(--primary-color);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.5rem;
        font-weight: 500;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 4px rgba(158, 5, 32, 0.2);
    }
    
    .stButton > button:hover {
        background: #B8062A;
        transform: translateY(-1px);
        box-shadow: 0 4px 8px rgba(158, 5, 32, 0.3);
    }
    
    /* Botão de deletar */
    .delete-button > button {
        background: var(--danger) !important;
        color: white !important;
    }
    
    .delete-button > button:hover {
        background: #C82333 !important;
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stSelectbox > div > div > div,
    .stMultiSelect > div > div > div {
        border-radius: 8px;
        border: 2px solid var(--border-color);
        transition: border-color 0.3s ease;
    }
    
    .stTextInput > div > div > input:focus,
    .stSelectbox > div > div > div:focus-within,
    .stMultiSelect > div > div > div:focus-within {
        border-color: var(--primary-color);
        box-shadow: 0 0 0 2px rgba(158, 5, 32, 0.1);
    }
    
    /* Alertas customizados */
    .custom-alert {
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid;
    }
    
    .alert-success {
        background: rgba(40, 167, 69, 0.1);
        border-left-color: var(--success);
        color: var(--success);
    }
    
    .alert-warning {
        background: rgba(255, 193, 7, 0.1);
        border-left-color: var(--warning);
        color: #856404;
    }
    
    .alert-danger {
        background: rgba(220, 53, 69, 0.1);
        border-left-color: var(--danger);
        color: var(--danger);
    }
    
    /* Métricas */
    .metric-card {
        background: var(--white);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 2px 10px var(--shadow);
        border: 1px solid var(--border-color);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: var(--primary-color);
    }
    
    .metric-label {
        color: var(--text-color);
        font-weight: 500;
        margin-top: 0.5rem;
    }
    
    /* Divisores */
    .section-divider {
        height: 2px;
        background: linear-gradient(90deg, var(--primary-color), var(--secondary-bg));
        border: none;
        margin: 2rem 0;
        border-radius: 1px;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 2rem;
        }
        
        .form-container {
            padding: 1rem;
        }
    }
</style>
""", unsafe_allow_html=True)

st.session_state.active_page = "Gerenciar Usuários"
build_sidebar()

# Header principal com design profissional
st.markdown("""
<div class="main-header">
    <h1>👥 Gerenciar Usuários</h1>
    <p>Administre usuários do sistema, gerencie permissões e vínculos organizacionais</p>
</div>
""", unsafe_allow_html=True)

# --- Seção de métricas rápidas ---
# --- Seção de métricas rápidas ---
try:
    all_users = get_all_users()
    total_users = len(all_users)
    servidores = len([u for u in all_users if u.get('perfil') == 'Servidor'])
    chefes = len([u for u in all_users if u.get('perfil') == 'Chefe de Gabinete'])
    procuradores = len([u for u in all_users if u.get('perfil') == 'Procurador'])
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    with col_m1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_users}</div>
            <div class="metric-label">Total de Usuários</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_m2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{servidores}</div>
            <div class="metric-label">Servidores</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_m3:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{chefes}</div>
            <div class="metric-label">Chefes de Gabinete</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_m4:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{procuradores}</div>
            <div class="metric-label">Procuradores</div>
        </div>
        """, unsafe_allow_html=True)

except Exception as e:
    st.error(f"Erro ao carregar métricas: {e}")



# --- Bloco para exibir a lista de todos os usuários ---
st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

st.markdown("""
<div class="users-table-container">
    <div class="users-table-header">
        📋 Lista Completa de Usuários do Sistema
    </div>
</div>
""", unsafe_allow_html=True)

try:
    # Fetch relations manually to build display
    # 1. Fetch linkage tables
    gab_serv = select_all("gabinete_servidores")
    proc_chefe = select_all("procurador_chefes")
    chefe_sub = select_all("chefe_subordinado_chefe")
    
    # 2. Map IDs to Names
    user_map = {u['id']: u.get('nome_completo', 'Unknown') for u in all_users}
    
    # 3. Build Relation Maps: UserID -> List of Rel Names
    servidor_chefes_map = {}
    for r in gab_serv:
        sid = r['servidor_id']
        cid = r['chefe_id']
        servidor_chefes_map.setdefault(sid, []).append(user_map.get(cid, str(cid)))
        
    chefe_procs_map = {}
    for r in proc_chefe:
        cid = r['chefe_id']
        pid = r['procurador_id']
        chefe_procs_map.setdefault(cid, []).append(user_map.get(pid, str(pid)))
        
    chefe_superiores_map = {}
    for r in chefe_sub:
        sub_id = r['chefe_subordinado_id']
        sup_id = r['chefe_superior_id']
        chefe_superiores_map.setdefault(sub_id, []).append(user_map.get(sup_id, str(sup_id)))

    # all_users_data = db.query(Usuario).order_by(Usuario.id).all()
    # Sort all_users by ID
    all_users.sort(key=lambda x: x['id'])
    
    if all_users:
        df_data = []
        for u in all_users:
            uid = u['id']
            perfil = u.get('perfil')
            vinculos = []
            
            if perfil == 'Servidor':
                chefs = servidor_chefes_map.get(uid, [])
                if chefs:
                    vinculos = [f"Chefes: {', '.join(chefs)}"]
            elif perfil == 'Chefe de Gabinete':
                procs = chefe_procs_map.get(uid, [])
                sups = chefe_superiores_map.get(uid, [])
                if sups:
                    vinculos.append(f"Superiores: {', '.join(sups)}")
                if procs:
                    vinculos.append(f"Procuradores: {', '.join(procs)}")
            
            # Format datetime
            ua_str = u.get('ultimo_acesso')
            ua_formatted = "Nunca"
            if ua_str:
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(ua_str)
                    ua_formatted = dt.strftime('%d/%m/%Y %H:%M')
                except:
                    pass
            
            status_ativo = "✅ Ativo" if u.get('ativo', True) else "❌ Inativo"

            df_data.append({
                "ID": uid, 
                "Nome": u.get('nome_completo'), 
                "Login": u.get('login'), 
                "Perfil": perfil, 
                "Status": status_ativo,
                "Email": u.get('email'), 
                "Vinculado a": ", ".join(vinculos),
                "Último Acesso": ua_formatted
            })
        
        st.dataframe(
            pd.DataFrame(df_data), 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                "Nome": st.column_config.TextColumn("Nome", width="medium"),
                "Login": st.column_config.TextColumn("Login", width="small"),
                "Perfil": st.column_config.TextColumn("Perfil", width="medium"),
                "Status": st.column_config.TextColumn("Status", width="small"),
                "Email": st.column_config.TextColumn("Email", width="medium"),
                "Vinculado a": st.column_config.TextColumn("Vínculos", width="large"),
                "Último Acesso": st.column_config.TextColumn("Último Acesso", width="medium")
            }
        )
    else:
        st.markdown("""
        <div class="custom-alert alert-warning">
            <strong>ℹ️ Informação:</strong> Nenhum usuário cadastrado no sistema.
        </div>
        """, unsafe_allow_html=True)
except Exception as e:
    st.markdown(f"""
    <div class="custom-alert alert-danger">
        <strong>❌ Erro:</strong> Erro ao carregar usuários: {e}
    </div>
    """, unsafe_allow_html=True)
# finally:
#     db.close()

st.markdown('<hr class="section-divider">', unsafe_allow_html=True)

# Layout em duas colunas para formulários
col1, col2 = st.columns([1, 1], gap="large")

# --- Coluna para Adicionar Usuário ---
with col1:
    st.markdown("""
    <div class="form-container">
        <div class="form-header">
            ➕ Adicionar Novo Usuário
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        with st.form("add_user", clear_on_submit=True):
            nome = st.text_input("Nome Completo", placeholder="Digite o nome completo do usuário")
            login = st.text_input("Login", placeholder="Digite o login único")
            senha = st.text_input("Senha", type="password", placeholder="Digite uma senha segura")
            perfil = st.selectbox("Perfil", ["Servidor", "Chefe de Gabinete", "Procurador", "Administrador"])
            email = st.text_input("E-mail", placeholder="usuario@email.com")

            # cached helpers
            all_chefes = [u for u in all_users if u.get('perfil') == 'Chefe de Gabinete']
            all_procs = [u for u in all_users if u.get('perfil') == 'Procurador']

            chefes_disponiveis = {c['nome_completo']: c for c in all_chefes}
            procuradores_disponiveis = {p['nome_completo']: p for p in all_procs}
            
            chefes_selecionados_add = []
            if perfil == 'Servidor' and chefes_disponiveis:
                st.markdown("**Vínculos Hierárquicos:**")
                chefes_selecionados_add = st.multiselect(
                    "Vincular aos Chefes de Gabinete:", 
                    options=list(chefes_disponiveis.keys()), 
                    key="add_chefes",
                    help="Selecione os chefes aos quais este servidor estará vinculado"
                )
            
            procuradores_selecionados_add = []
            superiores_selecionados_add = []
            
            chefes_superiores_disponiveis = chefes_disponiveis # same poll
            
            if perfil == 'Chefe de Gabinete':
                st.markdown("**Vínculos Organizacionais:**")
                if procuradores_disponiveis:
                    procuradores_selecionados_add = st.multiselect(
                        "Vincular aos Procuradores:", 
                        options=list(procuradores_disponiveis.keys()), 
                        key="add_procs",
                        help="Procuradores sob a supervisão deste chefe"
                    )
                
                if chefes_superiores_disponiveis:
                    superiores_selecionados_add = st.multiselect(
                        "Vincular aos Chefes Superiores:", 
                        options=list(chefes_superiores_disponiveis.keys()), 
                        key="add_superiores",
                        help="Chefes hierarquicamente superiores"
                    )

            submitted = st.form_submit_button("📝 Cadastrar Usuário", use_container_width=True)
            
            if submitted:
                if all([nome, login, senha, perfil]):
                    # Check duplication
                    exists = any(u['login'] == login for u in all_users)
                    if exists:
                        st.markdown(f"""
                        <div class="custom-alert alert-danger">
                            <strong>❌ Erro:</strong> Login '{login}' já existe. Escolha outro login.
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        new_user_data = {
                            "nome_completo": nome, 
                            "login": login, 
                            "senha_hash": hash_password(senha), 
                            "perfil": perfil, 
                            "email": email
                        }
                        
                        # Create User and get ID
                        new_user = create_user(new_user_data)
                        
                        # create_user retorna dicionário do usuário inserido ou None
                        if new_user and isinstance(new_user, dict) and 'id' in new_user:
                             uid = new_user['id']
                             
                             # Handle Relations
                             if chefes_selecionados_add:
                                 cids = [chefes_disponiveis[n]['id'] for n in chefes_selecionados_add]
                                 update_servidor_chefes(uid, cids)
                                 
                             if procuradores_selecionados_add:
                                 pids = [procuradores_disponiveis[n]['id'] for n in procuradores_selecionados_add]
                                 update_chefe_procuradores(uid, pids)
                                 
                             if superiores_selecionados_add:
                                 sids = [chefes_superiores_disponiveis[n]['id'] for n in superiores_selecionados_add]
                                 update_chefe_superiores(uid, sids)
                             
                             st.success(f"✅ Usuário '{nome}' cadastrado com sucesso!")
                             st.rerun()
                        else:
                            st.error("Erro ao criar usuário no banco de dados.")

                else:
                    st.markdown("""
                    <div class="custom-alert alert-warning">
                        <strong>⚠️ Atenção:</strong> Todos os campos obrigatórios devem ser preenchidos.
                    </div>
                    """, unsafe_allow_html=True)
    except Exception as e:
         st.error(f"Erro no formulário: {e}")

# --- Coluna para Editar/Deletar Usuário ---
with col2:
    st.markdown("""
    <div class="form-container">
        <div class="form-header">
            ✏️ Editar ou Remover Usuário
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        all_users_data_edit = sorted(all_users, key=lambda x: x.get('nome_completo',''))
        
        if all_users_data_edit:
            selected_user_name_edit = st.selectbox(
                "Selecione um usuário para gerenciar:", 
                options=[u['nome_completo'] for u in all_users_data_edit if u['login'] != 'admin'],
                index=None,
                placeholder="Clique para selecionar...",
                help="Escolha um usuário da lista para editar ou remover"
            )
            
            if selected_user_name_edit:
                # user_to_edit = db.query(Usuario).filter(Usuario.nome_completo == selected_user_name_edit).first()
                user_to_edit = next((u for u in all_users_data_edit if u['nome_completo'] == selected_user_name_edit), None)
                
                if user_to_edit:
                    with st.form("edit_user_form"):
                        st.markdown(f"**Editando:** {user_to_edit['nome_completo']} ({user_to_edit['perfil']})")
                        
                        novo_login = st.text_input("Login", value=user_to_edit['login'])
                        novo_nome = st.text_input("Nome", value=user_to_edit['nome_completo'])
                        novo_email = st.text_input("Email", value=user_to_edit.get('email', ''))
                        
                        ativo_atual = user_to_edit.get('ativo', True)
                        novo_ativo = st.checkbox("Usuário Ativo", value=ativo_atual, help="Desmarque para desativar o usuário (bloqueia login e novas atribuições)")
                        
                        # Helpers again
                        all_chefes = [u for u in all_users if u.get('perfil') == 'Chefe de Gabinete']
                        all_procs = [u for u in all_users if u.get('perfil') == 'Procurador']
                        
                        chefes_disponiveis_edit = {c['nome_completo']: c for c in all_chefes}
                        procuradores_disponiveis_edit = {p['nome_completo']: p for p in all_procs}
                        chefes_superiores_disponiveis_edit = {c['nome_completo']: c for c in all_chefes if c['id'] != user_to_edit['id']}
                        
                        chefes_selecionados_edit = []
                        procuradores_selecionados_edit = []
                        superiores_selecionados_edit = []

                        if user_to_edit['perfil'] == 'Servidor':
                            st.markdown("**Vínculos Atuais:**")
                            # chefes_atuais = [c.nome_completo for c in user_to_edit.chefes]
                            chefes_atuais = servidor_chefes_map.get(user_to_edit['id'], [])
                            chefes_selecionados_edit = st.multiselect(
                                "Chefes Vinculados:", 
                                options=list(chefes_disponiveis_edit.keys()), 
                                default=[c for c in chefes_atuais if c in chefes_disponiveis_edit] # safe filtering
                            )
                        
                        if user_to_edit['perfil'] == 'Chefe de Gabinete':
                            st.markdown("**Vínculos Organizacionais:**")
                            # procuradores_atuais = [p.nome_completo for p in user_to_edit.procuradores]
                            procuradores_atuais = chefe_procs_map.get(user_to_edit['id'], [])
                            procuradores_selecionados_edit = st.multiselect(
                                "Procuradores Vinculados:", 
                                options=list(procuradores_disponiveis_edit.keys()), 
                                default=[p for p in procuradores_atuais if p in procuradores_disponiveis_edit], 
                                key=f"edit_procs_{user_to_edit['id']}"
                            )
                            
                            # superiores_atuais = [s.nome_completo for s in user_to_edit.superiores]
                            superiores_atuais = chefe_superiores_map.get(user_to_edit['id'], [])
                            superiores_selecionados_edit = st.multiselect(
                                "Chefes Superiores Vinculados:", 
                                options=list(chefes_superiores_disponiveis_edit.keys()), 
                                default=[s for s in superiores_atuais if s in chefes_superiores_disponiveis_edit], 
                                key=f"edit_superiores_{user_to_edit['id']}"
                            )
    
                        nova_senha = st.text_input(
                            "Nova Senha", 
                            type="password", 
                            help="Deixe em branco para não alterar a senha atual",
                            placeholder="Digite apenas se quiser alterar"
                        )
                        
                        if st.form_submit_button("💾 Salvar Alterações", use_container_width=True):
                            login_exists = any(u['login'] == novo_login and u['id'] != user_to_edit['id'] for u in all_users)
                            
                            if login_exists:
                                st.markdown(f"""
                                <div class="custom-alert alert-danger">
                                    <strong>❌ Erro:</strong> O login '{novo_login}' já pertence a outro usuário.
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                update_data = {
                                    "login": novo_login,
                                    "nome_completo": novo_nome,
                                    "email": novo_email,
                                    "ativo": novo_ativo
                                }
                                
                                if nova_senha:
                                    update_data["senha_hash"] = hash_password(nova_senha)
                                
                                # Update user details
                                update_user(user_to_edit['id'], update_data)
                                
                                # Update relations
                                if user_to_edit['perfil'] == 'Servidor':
                                    cids = [chefes_disponiveis_edit[n]['id'] for n in chefes_selecionados_edit]
                                    update_servidor_chefes(user_to_edit['id'], cids)
                                
                                if user_to_edit['perfil'] == 'Chefe de Gabinete':
                                    pids = [procuradores_disponiveis_edit[n]['id'] for n in procuradores_selecionados_edit]
                                    update_chefe_procuradores(user_to_edit['id'], pids)
                                    
                                    sids = [chefes_superiores_disponiveis_edit[n]['id'] for n in superiores_selecionados_edit]
                                    update_chefe_superiores(user_to_edit['id'], sids)

                                st.markdown("""
                                <div class="custom-alert alert-success">
                                    <strong>✅ Sucesso:</strong> Usuário atualizado com sucesso!
                                </div>
                                """, unsafe_allow_html=True)
                                st.rerun()
    
                    # Lógica de deleção fora do formulário de edição
                    if selected_user_name_edit:
                        st.markdown('<hr style="margin: 2rem 0;">', unsafe_allow_html=True)
                        st.markdown("""
                        <div class="custom-alert alert-danger">
                            <strong>⚠️ ATENÇÃO:</strong> A exclusão do usuário é uma ação <strong>permanente e irreversível</strong>. 
                            Todos os dados e históricos associados serão removidos definitivamente.
                        </div>
                        """, unsafe_allow_html=True)
                        
                        confirm_delete = st.checkbox(
                            "✅ Sim, eu compreendo os riscos e quero deletar este usuário permanentemente.", 
                            key=f"del_user_{user_to_edit['id']}"
                        )
                        
                        delete_col1, delete_col2 = st.columns([1, 1])
                        with delete_col2:
                            if st.button(
                                "🗑️ Deletar Usuário", 
                                disabled=(not confirm_delete),
                                help="Esta ação não pode ser desfeita",
                                use_container_width=True,
                                key="delete_button_styling"
                            ):
                                # delete_user já remove todos os relacionamentos internamente
                                result = delete_user(user_to_edit['id'])
                                
                                if result:
                                    st.success(f"✅ Usuário '{user_to_edit['nome_completo']}' foi removido do sistema.")
                                else:
                                    st.error("❌ Erro ao deletar usuário. Verifique se há processos vinculados a este usuário.")
                                st.rerun()
        else:
            st.markdown("""
            <div class="custom-alert alert-warning">
                <strong>ℹ️ Informação:</strong> Nenhum usuário disponível para gerenciamento.
            </div>
            """, unsafe_allow_html=True)
    except Exception as e:
         st.error(f"Erro no gerenciamento: {e}")

# Adicionar estilo específico para o botão de deletar
st.markdown("""
<style>
    [data-testid="stButton"][data-baseweb="button"] button[key="delete_button_styling"] {
        background-color: #DC3545 !important;
        color: white !important;
        border: none !important;
    }
    
    [data-testid="stButton"][data-baseweb="button"] button[key="delete_button_styling"]:hover {
        background-color: #C82333 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 8px rgba(220, 53, 69, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)