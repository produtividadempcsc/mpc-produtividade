import auth
import streamlit as st
from datetime import date
from sidebar import build_sidebar
from utils.timezone import today_brazil

# Módulos do projeto
import ui_utils
import utils.common as common_utils
from forms import display_servidor_update_form
# Migration imports
from supabase_client import QueryBuilder, select_all, rpc
from db_compat import (
    get_user_by_id,
    get_user_bosses,
    get_prosecutors_linked_to_users
)
from services.prazo_service import (
    calculate_due_date
)
from components import ui_kpis
from components.process_list_servidor import render_servidor_process_list
from repositories.devolucao_repository import get_devolucoes_batch

auth.auth_guard()

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
allowed_profiles = ["Servidor", "Chefe de Gabinete"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Apenas usuários com perfil 'Servidor' ou 'Chefe de Gabinete' podem acessar esta página.")
    st.stop()
# ==============================================================================

st.session_state.active_page = "Meus Processos"

# Initialize session state for history visibility
if 'history_visible' not in st.session_state:
    st.session_state.history_visible = {}

# CSS Personalizado com as cores do sistema
# CSS Personalizado com as cores do sistema
ui_utils.load_css("style.css")

build_sidebar()

# Exibe feedback visual pendente, se houver
ui_utils.show_feedback_banner()

# ROTEADOR DE MODAL: Se um processo foi selecionado para atualização, exibe o formulário.
if 'processo_para_atualizar_id' in st.session_state:
    display_servidor_update_form(st.session_state['processo_para_atualizar_id'])
else:
    # --- CONTEÚDO PRINCIPAL DA PÁGINA ---
    st.markdown("""
    <div class="main-header">
        <h1>📋 Meus Processos</h1>
        <p>Visualize e gerencie suas tarefas de forma eficiente</p>
    </div>
    """, unsafe_allow_html=True)

    user_id = st.session_state.user_id
    
    # --- KPIs via Supabase API ---
    with st.spinner("Carregando seus processos..."):
        kpis = rpc('get_kpis_servidor', {'p_id_servidor': user_id})

    if kpis:
        total_ativos = kpis.get('total_ativos', 0)
        no_prazo = kpis.get('no_prazo', 0)
        atrasados = kpis.get('atrasados', 0)
    else:
        total_ativos = 0
        no_prazo = 0
        atrasados = 0
    
    # KPIs com design customizado
    ui_kpis.render_servidor_kpis(total_ativos, no_prazo, atrasados)


    servidor_logado = get_user_by_id(user_id)

    # --- FILTROS ---
    with st.container():
        st.markdown('<div class="filters-header">Painel de Controle da Equipe</div>', unsafe_allow_html=True)

        # Data sources for filters via Supabase API
        chefes_list = get_user_bosses(user_id)
        chefes_vinculados = {c.get('nome_completo'): c.get('id') for c in chefes_list}
        
        # Get prosecutors linked through bosses
        procuradores_vinculados = {}
        for chefe in chefes_list:
            procs = get_prosecutors_linked_to_users([chefe.get('id')])
            for p in procs:
                procuradores_vinculados[p.get('nome_completo')] = p.get('id')
        
        # Get all product types
        all_tipos_produto = select_all("tipos_produto")
        todos_tipos_produto = {}
        for p in sorted(all_tipos_produto, key=lambda x: x.get('nome_produto', '')):
            if p.get('nome_produto') not in todos_tipos_produto:
                todos_tipos_produto[p.get('nome_produto')] = p.get('id')

        # Filter UI layout
        filtro_numero_processo = st.text_input("🔍 Filtrar por Número do Processo:", key="servidor_filtro_num", placeholder="Digite o número do processo...")

        f_col1, f_col2, f_col3, f_col4 = st.columns(4)
        with f_col1:
            opcoes_status = ["No Prazo", "Atrasado", "Devolvido", "Concluído", "Finalizado"]
            default_status = ["No Prazo", "Atrasado", "Devolvido"]
            filtro_status = st.multiselect("📊 Status", options=opcoes_status, default=default_status, key="servidor_status_filter")
            st.text_input("👤 Servidor", value=servidor_logado.get('nome_completo', '') if servidor_logado else '', disabled=True)
        with f_col2:
            filtro_chefe_nomes = st.multiselect("👔 Chefe de Gabinete", options=list(chefes_vinculados.keys()), key="servidor_chefe_filter")
            filtro_procurador_nomes = st.multiselect("⚖️ Procurador", options=list(procuradores_vinculados.keys()), key="servidor_procurador_filter")
        with f_col3:
            filtro_data_inicio = st.date_input("📅 De:", key="servidor_data_inicio", value=None, format="DD/MM/YYYY")
            filtro_data_fim = st.date_input("📅 Até:", key="servidor_data_fim", value=None, format="DD/MM/YYYY")
        with f_col4:
            filtro_tipo_produto_nomes = st.multiselect("📝 Tipo de Processo", options=list(todos_tipos_produto.keys()), key="servidor_tipo_produto_filter")
            ordenar_por = st.selectbox("📈 Ordenar por", ["Mais Recentes", "Mais Antigos", "Prazo Restante (Crescente)", "Prazo Restante (Decrescente)"], key="servidor_ordenar")
    
    ui_utils.display_icon_legend()

    # --- QUERY via Supabase API ---
    all_user_processes = QueryBuilder("processos").eq("id_servidor_responsavel", user_id).execute()
    processos_filtrados = all_user_processes  # Start with all user processes
    
    # Apply filters in Python
    if filtro_status:
        processos_filtrados = [p for p in processos_filtrados if p.get('status_servidor') in filtro_status]
    if filtro_chefe_nomes:
        chefe_ids = [chefes_vinculados[n] for n in filtro_chefe_nomes]
        processos_filtrados = [p for p in processos_filtrados if p.get('id_chefe_gabinete') in chefe_ids]
    if filtro_procurador_nomes:
        proc_ids = [procuradores_vinculados[n] for n in filtro_procurador_nomes]
        processos_filtrados = [p for p in processos_filtrados if p.get('id_procurador') in proc_ids]
    if filtro_data_inicio:
        processos_filtrados = [p for p in processos_filtrados if p.get('data_atribuicao_servidor') and p.get('data_atribuicao_servidor') >= filtro_data_inicio.isoformat()]
    if filtro_data_fim:
        processos_filtrados = [p for p in processos_filtrados if p.get('data_atribuicao_servidor') and p.get('data_atribuicao_servidor') <= filtro_data_fim.isoformat()]
    if filtro_tipo_produto_nomes:
        ids_tipos_produto = [todos_tipos_produto[n] for n in filtro_tipo_produto_nomes]
        processos_filtrados = [p for p in processos_filtrados if p.get('id_tipo_produto') in ids_tipos_produto]
    
    # Refinamento local: reordena por similaridade (fuzzy matching)
    if filtro_numero_processo and processos_filtrados:
        processos_filtrados = common_utils.filter_by_similarity(
            search_term=filtro_numero_processo,
            items=processos_filtrados,
            key_func=lambda p: p.get('processo_numero', '')
        )


    # --- SORTING ---
    hoje = today_brazil()
    processos_com_prazo = []
    
    # Cache all product types for efficiency
    all_product_types_map = {p.get('id'): p for p in all_tipos_produto}
    
    # Buscar devoluções ativas em batch para todos os processos com prazo_customizado
    ids_customizados = [p.get('id') for p in processos_filtrados if p.get('prazo_customizado')]
    devolucoes_ativas = get_devolucoes_batch(ids_customizados) if ids_customizados else {}
    
    for p in processos_filtrados:
        produto_obj = all_product_types_map.get(p.get('id_tipo_produto'))
        if not produto_obj: 
            continue
        
        # Parse data_atribuicao_servidor
        data_atrib_str = p.get('data_atribuicao_servidor')
        if data_atrib_str:
            if isinstance(data_atrib_str, str):
                data_atrib = date.fromisoformat(data_atrib_str)
            else:
                data_atrib = data_atrib_str
        else:
            continue
        
        # Usar dados da devolução ativa como fonte primária
        prazo_efetivo = p.get('prazo_servidor_aplicado')
        data_inicio_efetiva = data_atrib
        
        if p.get('prazo_customizado'):
            dev = devolucoes_ativas.get(p.get('id'))
            if dev:
                prazo_efetivo = dev.get('prazo_dias', prazo_efetivo)
                dt_dev_str = dev.get('data_devolucao')
                if dt_dev_str:
                    data_inicio_efetiva = date.fromisoformat(dt_dev_str) if isinstance(dt_dev_str, str) else dt_dev_str
        
        # Se prazo está suspenso, não calcular atraso
        if p.get('prazo_status') == 'Suspenso':
            processos_com_prazo.append((p, float('inf')))
            continue

        data_final = calculate_due_date(
            data_inicio_efetiva, 
            prazo_efetivo, 
            produto_obj.get('tipo_contagem_prazo'), 
            p.get('id_servidor_responsavel'), 
            dias_suspensos=p.get('prazo_total_dias_suspenso', 0)
        )
        dias_restantes = (data_final - hoje).days if data_final else float('inf')
        processos_com_prazo.append((p, dias_restantes))
    
    # Ordena a lista de processos com base no critério selecionado
    def get_data_atribuicao(item):
        d = item[0].get('data_atribuicao_servidor')
        if isinstance(d, str):
            return date.fromisoformat(d)
        return d or date.min
    
    if ordenar_por == "Prazo Restante (Crescente)":
        processos_ordenados = sorted(processos_com_prazo, key=lambda item: item[1])
    elif ordenar_por == "Prazo Restante (Decrescente)":
        processos_ordenados = sorted(processos_com_prazo, key=lambda item: item[1], reverse=True)
    elif ordenar_por == "Mais Antigos":
        processos_ordenados = sorted(processos_com_prazo, key=get_data_atribuicao)
    else: # Mais Recentes
        processos_ordenados = sorted(processos_com_prazo, key=get_data_atribuicao, reverse=True)
    
    # --- PAGINATION ---
    st.markdown("---")
    items_per_page = st.selectbox("📊 Itens por página", [10, 25, 50, 100], index=1, key="servidor_items_per_page")
    if 'servidor_page_number' not in st.session_state: st.session_state.servidor_page_number = 0
    start_index = st.session_state.servidor_page_number * items_per_page
    end_index = start_index + items_per_page
    paginated_items = processos_ordenados[start_index:end_index]

    if not paginated_items:
        st.markdown("""
        <div style="text-align: center; padding: 3rem; background: white; border-radius: 12px; margin: 2rem 0;">
            <h3 style="color: #9E0520;">🔭 Nenhum processo encontrado</h3>
            <p style="color: #666;">Tente ajustar os filtros para encontrar processos.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        total_pages = (len(processos_ordenados) - 1) // items_per_page + 1
        
        st.markdown(f"""
        <div style="text-align: center; margin: 2rem 0;">
            <h2 style="color: #9E0520;">📊 Resultados</h2>
            <p style="color: #666; font-size: 1.1rem;">Página {st.session_state.servidor_page_number + 1} de {total_pages} • {len(processos_ordenados)} processos encontrados</p>
        </div>
        """, unsafe_allow_html=True)
        
        all_users = QueryBuilder("usuarios").select("id,nome_completo").execute()
        users_map = {u['id']: u for u in all_users}
        
        processo_ids_paginados = [p[0].get('id') for p in paginated_items]
        unread_comments_cache = common_utils.batch_has_unread_comments(processo_ids_paginados, user_id)
        
        render_servidor_process_list(paginated_items, all_product_types_map, users_map, unread_comments_cache)
        
        # Controles de paginação com estilo personalizado
        if total_pages > 1:
            st.markdown('<div class="pagination-container">', unsafe_allow_html=True)
            col_pag1, col_pag2, col_pag3 = st.columns([1, 2, 1])
            
            with col_pag1:
                if st.button("⬅️ Anterior", key="serv_prev_page", disabled=(st.session_state.servidor_page_number == 0)):
                    st.session_state.servidor_page_number -= 1
                    st.rerun()
            
            with col_pag2:
                st.markdown(f"""
                <div style="text-align: center; padding: 10px;">
                    Página <strong>{st.session_state.servidor_page_number + 1}</strong> de <strong>{total_pages}</strong>
                </div>
                """, unsafe_allow_html=True)
            
            with col_pag3:
                if st.button("Próxima ➡️", key="serv_next_page", disabled=(end_index >= len(processos_ordenados))):
                    st.session_state.servidor_page_number += 1
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)