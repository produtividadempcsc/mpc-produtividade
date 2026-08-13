import auth
import streamlit as st
from datetime import date
from utils.timezone import today_brazil
from sidebar import build_sidebar

# Módulos do projeto
import ui_utils
import utils.common as common_utils
from forms import display_edit_processo_form
from supabase_client import select_all, QueryBuilder
from db_compat import get_all_users
from services.prazo_service import calculate_due_date_with_details
from components.process_list_mpc import render_mpc_process_list
# Inicializa a conexão com o banco de dados

auth.auth_guard()

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
allowed_profiles = ["Procurador", "Administrador"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Você não tem permissão para acessar esta página.")
    st.stop()
# ==============================================================================

st.session_state.active_page = "Processos MPC"
build_sidebar()

# Exibe feedback visual pendente, se houver
ui_utils.show_feedback_banner()

# CSS CUSTOMIZADO PARA LAYOUT PROFISSIONAL
# CSS CUSTOMIZADO PARA LAYOUT PROFISSIONAL
ui_utils.load_css("style.css")

# ROTEADOR DE MODAL: Se um processo foi selecionado para edição, exibe o formulário.
if 'processo_para_editar_id' in st.session_state:
    display_edit_processo_form(st.session_state['processo_para_editar_id'])
else:
    # --- CONTEÚDO PRINCIPAL DA PÁGINA ---
    st.markdown("""
    <div class="main-header">
        <h1>⚖️ Processos MPC</h1>
        <p>Visualize e gerencie todos os processos registrados no sistema com interface profissional</p>
    </div>
    """, unsafe_allow_html=True)

    user_id = st.session_state.user_id


    # Inicialização do estado da sessão para o histórico
    if 'history_visible_for' not in st.session_state:
        st.session_state['history_visible_for'] = None
        
    # --- FILTROS ---
    st.markdown("""
    <div class="filter-container">
        <div class="filter-title">Filtros Avançados</div>
    """, unsafe_allow_html=True)
        
    # Data sources for filters
    # todos_servidores = {s.nome_completo: s.id for s in db.query(Usuario).filter(Usuario.perfil == 'Servidor').order_by(Usuario.nome_completo).all()}
    all_users = get_all_users()
    all_users.sort(key=lambda x: x.get('nome_completo', ''))
    
    todos_servidores = {s['nome_completo']: s['id'] for s in all_users if s.get('perfil') == 'Servidor'}
    todos_chefes = {c['nome_completo']: c['id'] for c in all_users if c.get('perfil') == 'Chefe de Gabinete'}
    todos_procuradores = {p['nome_completo']: p['id'] for p in all_users if p.get('perfil') == 'Procurador'}
    all_products = select_all("tipos_produto")
    all_products.sort(key=lambda x: x.get('nome_produto', ''))
    todos_tipos_produto = {p['nome_produto']: p['id'] for p in all_products}

    # Filter UI layout
    filtro_numero_processo = st.text_input("🔍 Filtrar por Número do Processo:", key="proc_filtro_num")

    f_col1, f_col2, f_col3, f_col4 = st.columns(4)
    with f_col1:
        status_opts = ["No Prazo", "Atrasado", "Devolvido", "Concluído", "Revisão Atrasada", "Processo com o Procurador", "Finalizado"]
        filtro_status = st.multiselect("📊 Status", options=status_opts, key="procurador_status_filter")
        filtro_servidor_nomes = st.multiselect("👤 Servidor", options=list(todos_servidores.keys()), key="procurador_servidor_filter")
    with f_col2:
        filtro_chefe_nomes = st.multiselect("👔 Chefe de Gabinete", options=list(todos_chefes.keys()), key="procurador_chefe_filter")
        filtro_procurador_nomes = st.multiselect("⚖️ Procurador", options=list(todos_procuradores.keys()), key="procurador_procurador_filter")
    with f_col3:
        filtro_data_inicio = st.date_input("📅 De:", key="procurador_data_inicio", value=None, format="DD/MM/YYYY")
        filtro_data_fim = st.date_input("📅 Até:", key="procurador_data_fim", value=None, format="DD/MM/YYYY")
    with f_col4:
        filtro_tipo_produto_nomes = st.multiselect("📋 Tipo de Processo", options=list(todos_tipos_produto.keys()), key="procurador_tipo_produto_filter")
        ordenar_por = st.selectbox("🔄 Ordenar por", ["Mais Recentes", "Mais Antigos", "Prazo Restante (Crescente)", "Prazo Restante (Decrescente)"], key="procurador_ordenar")

    st.markdown("</div>", unsafe_allow_html=True)

    ui_utils.display_icon_legend()

    with st.spinner("🔄 Carregando e processando... Por favor, aguarde."):
        # --- QUERY ---
        # query = db.query(Processo)
        query = QueryBuilder("processos")

        if filtro_status:
            pass 
        
        if filtro_servidor_nomes:
            sids = [todos_servidores[n] for n in filtro_servidor_nomes]
            query.in_list("id_servidor_responsavel", sids)
            
        if filtro_chefe_nomes:
            cids = [todos_chefes[n] for n in filtro_chefe_nomes]
            query.in_list("id_chefe_gabinete", cids)
            
        if filtro_procurador_nomes:
            pids = [todos_procuradores[n] for n in filtro_procurador_nomes]
            query.in_list("id_procurador", pids)
            
        if filtro_data_inicio:
            query.gte("data_atribuicao_servidor", filtro_data_inicio.isoformat())
            
        if filtro_data_fim:
            query.lte("data_atribuicao_servidor", filtro_data_fim.isoformat())
            
        if filtro_tipo_produto_nomes:
            ids_tipos_produto = [todos_tipos_produto[n] for n in filtro_tipo_produto_nomes]
            query.in_list("id_tipo_produto", ids_tipos_produto)

        processos_filtrados = query.execute()

        # Handle 'OR' status filter in Python
        if filtro_status:
            allowed = set(filtro_status)
            processos_filtrados = [p for p in processos_filtrados if p.get('status_servidor') in allowed or p.get('status_chefe') in allowed]


        # Refinamento local: reordena por similaridade (fuzzy matching)
        if filtro_numero_processo and processos_filtrados:
            processos_filtrados = common_utils.filter_by_similarity(
                search_term=filtro_numero_processo,
                items=processos_filtrados,
                key_func=lambda p: p['processo_numero']
            )
            
        # --- REESTRUTURAÇÃO: Pré-cálculo para otimização ---
            
        # --- REESTRUTURAÇÃO: Pré-cálculo para otimização ---
        hoje = today_brazil()
        processos_com_dados = []
        # produtos_cache = {p.id: p for p in db.query(TipoProduto).all()}
        # usuarios_cache = {u.id: u.nome_completo for u in db.query(Usuario).all()}
        produtos_cache = {p['id']: p for p in all_products}
        usuarios_cache = {u['id']: u.get('nome_completo', 'N/A') for u in all_users}

        from datetime import datetime

        for p in processos_filtrados:
            pid_prod = p.get('id_tipo_produto')
            produto_obj = produtos_cache.get(pid_prod)
            if not produto_obj: continue

            dados = {
                "processo": p, 
                "servidor_nome": usuarios_cache.get(p.get('id_servidor_responsavel'), "N/A"), 
                "chefe_nome": usuarios_cache.get(p.get('id_chefe_gabinete'), "N/A"), 
                "procurador_nome": usuarios_cache.get(p.get('id_procurador'), "N/A"), 
                "produto_nome": produto_obj.get('nome_produto')
            }
            
            # Helper to parse dates
            def get_dt(iso_str):
                return datetime.fromisoformat(iso_str).date() if iso_str else None

            atribuicao_dt = get_dt(p.get('data_atribuicao_servidor'))
            conclusao_dt = get_dt(p.get('data_conclusao_servidor'))
            status_sv = p.get('status_servidor')
            status_ch = p.get('status_chefe')
            prazo_chefe = p.get('prazo_chefe_aplicado')
            prazo_servidor = p.get('prazo_servidor_aplicado')
            # id_chefe = p.get('id_chefe_gabinete')
            id_serv = p.get('id_servidor_responsavel')
            id_chefe_p = p.get('id_chefe_gabinete') # use local var
            
            tipo_contagem = produto_obj.get('tipo_contagem_prazo')
            dias_suspensos = p.get('prazo_total_dias_suspenso', 0)

            # Define qual prazo é o "ativo" para ordenação
            if status_sv == "Concluído" and status_ch in ["Aguardando Análise", "Revisão Atrasada"]:
                data_inicio = conclusao_dt
                prazo = prazo_chefe
                id_usuario = id_chefe_p
            else:
                data_inicio = atribuicao_dt
                prazo = prazo_servidor
                id_usuario = id_serv
            
            # Se prazo está suspenso, não calcular atraso
            if p.get('prazo_status') == 'Suspenso':
                dados["dias_restantes"] = float('inf')
            else:
                data_final, ajuste = calculate_due_date_with_details(data_inicio, prazo, tipo_contagem, id_usuario, dias_suspensos=dias_suspensos)
                dados["dias_restantes"] = (data_final - hoje).days if data_final else float('inf')
            
            # Armazena também os dados detalhados para não recalcular na exibição
            if not p.get('nao_se_aplica_prazo_servidor'):
                df_servidor_ajustada, ajuste_servidor = calculate_due_date_with_details(atribuicao_dt, prazo_servidor, tipo_contagem, id_serv, dias_suspensos=dias_suspensos)
                dados["data_final_servidor_ajustada"] = df_servidor_ajustada
                dados["ajuste_servidor"] = ajuste_servidor
            
            if conclusao_dt:
                df_revisao_ajustada, ajuste_revisao = calculate_due_date_with_details(conclusao_dt, prazo_chefe, tipo_contagem, id_chefe_p, dias_suspensos=dias_suspensos)
                dados["data_final_revisao_ajustada"] = df_revisao_ajustada
                dados["ajuste_revisao"] = ajuste_revisao

            processos_com_dados.append(dados)

        # --- Lógica de Ordenação ---
        # --- Lógica de Ordenação ---
        # Helper to get sort key since data is nested now
        if ordenar_por == "Prazo Restante (Crescente)": 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["dias_restantes"])
        elif ordenar_por == "Prazo Restante (Decrescente)": 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["dias_restantes"], reverse=True)
        elif ordenar_por == "Mais Antigos": 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["processo"].get('data_atribuicao_servidor') or "")
        else: 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["processo"].get('data_atribuicao_servidor') or "", reverse=True)
        
    # --- PAGINAÇÃO ---
    items_per_page = st.selectbox("📄 Itens por página", [10, 25, 50, 100], index=1, key="procurador_items_per_page")
    if 'procurador_page_number' not in st.session_state: st.session_state.procurador_page_number = 0
    start_index = st.session_state.procurador_page_number * items_per_page
    end_index = start_index + items_per_page
    paginated_items = processos_ordenados[start_index:end_index]

    if not paginated_items:
        st.warning("⚠️ Nenhum processo encontrado com os filtros selecionados.")
    else:
        total_pages = (len(processos_ordenados) - 1) // items_per_page + 1
        
        st.markdown(f"""
        <div class="pagination-container">
            <div class="page-info">Página {st.session_state.procurador_page_number + 1} de {total_pages}</div>
        </div>
        """, unsafe_allow_html=True)

        render_mpc_process_list(paginated_items)

        # --- CONTROLES DE PAGINAÇÃO ---
        if total_pages > 1:
            st.markdown('<div class="pagination-container">', unsafe_allow_html=True)
            col_pag1, col_pag2, col_pag3 = st.columns([1, 2, 1])
            
            with col_pag1:
                if st.button("⬅️ Anterior", key="chefe_prev_page", disabled=(st.session_state.procurador_page_number == 0)):
                    st.session_state.procurador_page_number -= 1
                    st.rerun()
            
            with col_pag2:
                st.markdown(f"""
                <div style="text-align: center; padding: 10px;">
                    Página <strong>{st.session_state.procurador_page_number + 1}</strong> de <strong>{total_pages}</strong>
                </div>
                """, unsafe_allow_html=True)
            
            with col_pag3:
                if st.button("Próxima ➡️", key="chefe_next_page", disabled=(end_index >= len(processos_ordenados))):
                    st.session_state.procurador_page_number += 1
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
