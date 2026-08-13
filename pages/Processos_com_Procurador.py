import auth
import streamlit as st
from sidebar import build_sidebar

# Módulos do projeto
import ui_utils
import utils.common as common_utils
from supabase_client import select_all, QueryBuilder
from components.process_list_procurador import render_procurador_process_list

auth.auth_guard()

# Inicialização do estado da sessão para visibilidade do histórico
if 'history_visible_procurador' not in st.session_state:
    st.session_state.history_visible_procurador = {}

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
allowed_profiles = ["Chefe de Gabinete"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Apenas usuários com perfil 'Chefe de Gabinete' podem acessar esta página.")
    st.stop()
# ==============================================================================

# CSS Personalizado com as cores do sistema
ui_utils.load_css("style.css")

st.session_state.active_page = "Processos com o Procurador"
build_sidebar()

# Exibe feedback visual pendente, se houver
ui_utils.show_feedback_banner()

# Header Principal
st.markdown("""
<div class="main-header">
    <h1>➡️ Processos com o Procurador</h1>
    <p>Processos aprovados por você e que estão em análise pelo Procurador de Contas</p>
</div>
""", unsafe_allow_html=True)

db = None # Removed db session usage
user_id = st.session_state.user_id

# Removed auxiliary functions that are now in the component

try:

    with st.expander("🔍 Filtros de Busca", expanded=True):
        filtro_numero_processo_proc = st.text_input("Filtrar por Número do Processo:", key="proc_filtro_num", placeholder="Digite o número do processo...")

    # Legenda de ícones
    st.markdown("""
    <div class="icon-legend">
        <div class="legend-title">📖 Legenda de Ícones</div>
        <div class="legend-items">
            <div class="legend-item"><span>💬</span> Comentários não lidos</div>
            <div class="legend-item"><span>📎</span> Possui anexos</div>
            <div class="legend-item"><span>🔥</span> Urgente</div>
            <div class="legend-item"><span>⚠️</span> Prioritário</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Query para buscar processos
    with st.spinner("Carregando processos com procurador..."):
        qb = QueryBuilder("processos")\
            .eq("id_chefe_gabinete", st.session_state.active_user_id)\
            .eq("status_chefe", "Processo com o Procurador")\
            .order("data_conclusao_chefe", desc=True)

        processos_com_procurador = qb.execute()

    # Refinamento local: reordena por similaridade (fuzzy matching)
    if filtro_numero_processo_proc and processos_com_procurador:
        processos_com_procurador = common_utils.filter_by_similarity(
            search_term=filtro_numero_processo_proc,
            items=processos_com_procurador,
            key_func=lambda p: p.get('processo_numero', '')
        )

    if not processos_com_procurador:
        st.markdown("""
        <div style="text-align: center; padding: 50px; background: white; border-radius: 12px; box-shadow: 0 3px 15px rgba(0,0,0,0.1);">
            <h3 style="color: var(--primary-color);">📋 Nenhum processo encontrado</h3>
            <p>Nenhum processo com o Procurador no momento ou correspondente ao filtro aplicado.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="pagination-info">📊 Encontrados: {len(processos_com_procurador)} processos</div>', unsafe_allow_html=True)

        processo_ids_pagina = [p['id'] for p in processos_com_procurador]
        
        all_types = select_all("tipos_produto")
        produtos_cache = {p['id']: p for p in all_types}
        
        all_users = select_all("usuarios", "id, nome_completo")
        usuarios_cache = {u['id']: u['nome_completo'] for u in all_users}

        # Batch check for unread comments (optimization: 2 queries instead of N*2)
        unread_comments_cache = common_utils.batch_has_unread_comments(processo_ids_pagina, st.session_state.user_id)

        render_procurador_process_list(processos_com_procurador, usuarios_cache, produtos_cache, unread_comments_cache)



except Exception as e:
    st.error(f"Ocorreu um erro ao carregar a página: {e}")