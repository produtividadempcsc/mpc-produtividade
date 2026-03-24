import auth
import streamlit as st
import pandas as pd
from sidebar import build_sidebar

# Módulos do projeto
from auth import hash_password
from db_compat import (
    get_all_users, create_user, delete_user, update_user,
    update_servidor_chefes, update_chefe_procuradores, update_chefe_superiores
)
from supabase_client import select_all

auth.auth_guard()

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
allowed_profiles = ["Administrador", "Chefe de Gabinete"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Você não tem permissão para acessar esta página.")
    st.stop()
# ==============================================================================

# CSS Personalizado para Layout Profissional (Centralizado)
import ui_utils
ui_utils.load_css("style.css")

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
    
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-value">{total_users}</div>
            <div class="kpi-label">Total de Usuários</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value" style="color: #17a2b8;">{servidores}</div>
            <div class="kpi-label">Servidores</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value" style="color: #ffc107;">{chefes}</div>
            <div class="kpi-label">Chefes de Gabinete</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value" style="color: #28a745;">{procuradores}</div>
            <div class="kpi-label">Procuradores</div>
        </div>
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
                except Exception as e:
                    print(f"⚠️ Erro silencioso em Gerenciar_Usuarios.py (Format datetime): {e}")
            
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
                        # --- ALTERAÇÃO DE PERFIL E DADOS BÁSICOS ---
                        novo_nome = st.text_input("Nome", value=user_to_edit['nome_completo'])
                        novo_login = st.text_input("Login", value=user_to_edit['login'])
                        novo_email = st.text_input("Email", value=user_to_edit.get('email', ''))
                        
                        # Permitir alteração de perfil (nível)
                        perfil_atual = user_to_edit['perfil']
                        novo_perfil = st.selectbox(
                            "Perfil (Nível de Acesso)", 
                            ["Servidor", "Chefe de Gabinete", "Procurador", "Administrador"],
                            index=["Servidor", "Chefe de Gabinete", "Procurador", "Administrador"].index(perfil_atual),
                            help="Alterar o nível do usuário. CUIDADO: Isso altera as permissões e vínculos."
                        )

                        ativo_atual = user_to_edit.get('ativo', True)
                        novo_ativo = st.checkbox("Usuário Ativo", value=ativo_atual, help="Desmarque para desativar o usuário")
                        
                        # --- VÍNCULOS DINÂMICOS BASEADOS NO NOVO PERFIL SELECIONADO ---
                        # Se o perfil mudar, mostramos os campos do NOVO perfil.
                        # Se o perfil for mantido, mostramos os campos atuais + pré-seleção.
                        
                        # Helpers again
                        all_chefes = [u for u in all_users if u.get('perfil') == 'Chefe de Gabinete']
                        all_procs = [u for u in all_users if u.get('perfil') == 'Procurador']
                        
                        chefes_disponiveis_edit = {c['nome_completo']: c for c in all_chefes}
                        procuradores_disponiveis_edit = {p['nome_completo']: p for p in all_procs}
                        chefes_superiores_disponiveis_edit = {c['nome_completo']: c for c in all_chefes if c['id'] != user_to_edit['id']}
                        
                        chefes_selecionados_edit = []
                        procuradores_selecionados_edit = []
                        superiores_selecionados_edit = []

                        # Lógica: Se o perfil selecionado (novo_perfil) é Servidor -> Mostra campo de Chefes
                        if novo_perfil == 'Servidor':
                            st.markdown("**Vínculos (Servidor):**")
                            # Tenta preservar seleção anterior se o usuário JÁ ERA servidor
                            defaults = []
                            if perfil_atual == 'Servidor':
                                chefes_atuais = servidor_chefes_map.get(user_to_edit['id'], [])
                                defaults = [c for c in chefes_atuais if c in chefes_disponiveis_edit]

                            chefes_selecionados_edit = st.multiselect(
                                "Chefes Vinculados:", 
                                options=list(chefes_disponiveis_edit.keys()), 
                                default=defaults
                            )
                        
                        # Lógica: Se o perfil selecionado (novo_perfil) é Chefe -> Mostra Procuradores e Superiores
                        if novo_perfil == 'Chefe de Gabinete':
                            st.markdown("**Vínculos (Chefe de Gabinete):**")
                            
                            # Defaults
                            defaults_procs = []
                            defaults_sups = []

                            if perfil_atual == 'Chefe de Gabinete':
                                procuradores_atuais = chefe_procs_map.get(user_to_edit['id'], [])
                                defaults_procs = [p for p in procuradores_atuais if p in procuradores_disponiveis_edit]
                                
                                superiores_atuais = chefe_superiores_map.get(user_to_edit['id'], [])
                                defaults_sups = [s for s in superiores_atuais if s in chefes_superiores_disponiveis_edit]

                            procuradores_selecionados_edit = st.multiselect(
                                "Procuradores Vinculados:", 
                                options=list(procuradores_disponiveis_edit.keys()), 
                                default=defaults_procs, 
                                key=f"edit_procs_{user_to_edit['id']}"
                            )
                            
                            superiores_selecionados_edit = st.multiselect(
                                "Chefes Superiores Vinculados:", 
                                options=list(chefes_superiores_disponiveis_edit.keys()), 
                                default=defaults_sups, 
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
                                    "perfil": novo_perfil, # Atualiza o perfil
                                    "ativo": novo_ativo
                                }
                                
                                if nova_senha:
                                    update_data["senha_hash"] = hash_password(nova_senha)
                                
                                # Update user details
                                update_user(user_to_edit['id'], update_data)
                                
                                # --- ATUALIZAÇÃO E LIMPEZA DE RELACIONAMENTOS ---
                                # Se virou Servidor (ou continuou): Atualiza chefes, LIMPA outros
                                if novo_perfil == 'Servidor':
                                    cids = [chefes_disponiveis_edit[n]['id'] for n in chefes_selecionados_edit]
                                    update_servidor_chefes(user_to_edit['id'], cids)
                                    # Limpeza: Servidor não tem procuradores nem superiores
                                    update_chefe_procuradores(user_to_edit['id'], []) 
                                    update_chefe_superiores(user_to_edit['id'], [])

                                # Se virou Chefe (ou continuou): Atualiza procs/sups, LIMPA chefes (de servidor)
                                elif novo_perfil == 'Chefe de Gabinete':
                                    pids = [procuradores_disponiveis_edit[n]['id'] for n in procuradores_selecionados_edit]
                                    update_chefe_procuradores(user_to_edit['id'], pids)
                                    
                                    sids = [chefes_superiores_disponiveis_edit[n]['id'] for n in superiores_selecionados_edit]
                                    update_chefe_superiores(user_to_edit['id'], sids)
                                    
                                    # Limpeza: Chefe não é subordinado de outro chefe da mesma forma que servidor
                                    # (A tabela servidor_chefes é para SERVIDORES vinculados a chefes)
                                    update_servidor_chefes(user_to_edit['id'], [])
                                
                                else:
                                    # Se virou Procurador ou Admin -> Limpa tudo (por enquanto)
                                    update_servidor_chefes(user_to_edit['id'], [])
                                    update_chefe_procuradores(user_to_edit['id'], [])
                                    update_chefe_superiores(user_to_edit['id'], [])

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

# O CSS para as tabelas agora reside em style.css