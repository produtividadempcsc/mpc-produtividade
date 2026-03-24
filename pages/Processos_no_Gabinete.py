import auth
import streamlit as st
from datetime import date, datetime, timedelta
from sidebar import build_sidebar
from utils.timezone import today_brazil, now_brazil

# Módulos do projeto
import ui_utils
import utils.common as common_utils
import utils.jobs as jobs_utils
import components.ui_kpis as ui_kpis
import components.process_forms as process_forms
import components.process_list as process_list
from forms import (
    display_edit_processo_form,
    display_chefe_update_form
)
# Migration imports
from supabase_client import QueryBuilder, rpc
from db_compat import (
    get_user_by_id, 
    get_all_users_cached, 
    get_all_product_types_cached,
    get_direct_servants,
    get_user_subordinates,
    get_prosecutors_of_boss
)
from services.prazo_service import calculate_due_date

auth.auth_guard()

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
allowed_profiles = ["Chefe de Gabinete"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Apenas usuários com perfil 'Chefe de Gabinete' podem acessar esta página.")
    st.stop()
# ==============================================================================

# CSS Personalizado com conf inicial da UI
ui_utils.load_css("style.css")

st.session_state.active_page = "Processos no Gabinete"
build_sidebar()

# --- ROTEADOR DE MODAL ---
if 'processo_para_editar_id' in st.session_state and st.session_state.processo_para_editar_id:
    display_edit_processo_form(st.session_state.processo_para_editar_id)

elif 'processo_para_atualizar_id' in st.session_state and st.session_state.processo_para_atualizar_id:
    display_chefe_update_form(st.session_state.processo_para_atualizar_id)

# --- CONTEÚDO PRINCIPAL DA PÁGINA ---
else:
    
    # Header principal
    st.markdown("""
    <div class="main-header">
        <h1>📋 Processos no Gabinete</h1>
        <p>Visão geral e gerenciamento de todos os processos da sua equipe</p>
    </div>
    """, unsafe_allow_html=True)

    # --- JOB DE ATUALIZAÇÃO (Debounced) ---
    # Evita rodar a cada rerun, apenas a cada 10 minutos
    last_run = st.session_state.get('last_update_job_run')
    should_run = True
    if last_run:
        if now_brazil() - last_run < timedelta(minutes=10):
            should_run = False
    
    if should_run:
        jobs_utils.update_process_statuses()
        st.session_state['last_update_job_run'] = now_brazil()

    
    try:
        id_chefe_para_acoes = st.session_state.active_user_id
        
        # =======================================================================
        # CACHE CENTRALIZADO - Evita múltiplas queries duplicadas
        # =======================================================================
        # Cache de usuários (usado em múltiplos lugares da página)
        all_users_list = get_all_users_cached()
        usuarios_cache = {u['id']: u for u in all_users_list}
        
        # Cache de tipos de produto (era carregado 3x antes)
        all_prods_cached = get_all_product_types_cached()
        produtos_cache = {p['id']: p for p in all_prods_cached}
        
        # Procuradores (era carregado 2x antes)
        procuradores_vinculados = get_prosecutors_of_boss(id_chefe_para_acoes)
        procuradores_vinculados.sort(key=lambda x: x.get('nome_completo', ''))
        procuradores_dict = {p['nome_completo']: p['id'] for p in procuradores_vinculados if p.get('ativo', True)}
        
        # --- KPIs (Consolidado em uma única query) ---
        # Busca super rápida via SQL Procedure (RPC) direto no Supabase
        kpis = rpc('get_kpis_chefe', {'p_id_chefe': id_chefe_para_acoes})
        
        if kpis:
            total_com_servidores = kpis.get('total_com_servidores', 0)
            total_para_revisao = kpis.get('total_para_revisao', 0)
            total_com_procurador = kpis.get('total_com_procurador', 0)
            total_atrasados_mpc = kpis.get('total_atrasados_mpc', 0)
        else:
            total_com_servidores = 0
            total_para_revisao = 0
            total_com_procurador = 0
            total_atrasados_mpc = 0

        # KPIs renderizados pelo component atualizado
        ui_kpis.render_gabinete_kpis(
            total_com_servidores=total_com_servidores,
            total_para_revisao=total_para_revisao,
            total_com_procurador=total_com_procurador,
            total_atrasados_mpc=total_atrasados_mpc
        )


        chefe_logado = get_user_by_id(id_chefe_para_acoes)
        
        # Equipe Atribuível
        equipe_atribuivel = []
        if chefe_logado:
            servidores_diretos = get_direct_servants(id_chefe_para_acoes)
            chefes_subordinados = get_user_subordinates(id_chefe_para_acoes)
            # Merge lists
            equipe_atribuivel.extend(servidores_diretos)
            equipe_atribuivel.extend(chefes_subordinados)
            # Deduplicate by ID just in case
            equipe_atribuivel = list({u['id']: u for u in equipe_atribuivel}.values())
            # Sort by name
            equipe_atribuivel.sort(key=lambda x: x.get('nome_completo', ''))

        # Renderiza Formulário de Novo Processo (Extraído para component)
        process_forms.render_add_process_form(
            id_chefe_para_acoes=id_chefe_para_acoes,
            chefe_logado=chefe_logado,
            equipe_atribuivel=equipe_atribuivel,
            all_prods_cached=all_prods_cached,
            procuradores_dict=procuradores_dict
        )

        st.markdown('</div>', unsafe_allow_html=True)

        # Seções de favoritos e suspensos (passando cache de usuários para evitar N+1)

        ui_utils.display_suspensos_expander(None, id_chefe_para_acoes, 'pages/Processos_no_Gabinete.py', usuarios_cache=usuarios_cache)
        
        st.markdown("---")
        
        # Seção de filtros com estilo personalizado
        st.markdown('<div class="filters-header">Painel de Controle da Equipe</div>', unsafe_allow_html=True)

        servidores_nomes_equipe = [s['nome_completo'] for s in equipe_atribuivel]
        if chefe_logado and chefe_logado['nome_completo'] not in servidores_nomes_equipe:
            servidores_nomes_equipe.insert(0, chefe_logado['nome_completo'])
        servidores_nomes_equipe.sort()

        # Usando cache de procuradores já carregado (evita query duplicada)
        # procuradores_dict já foi definido no cache centralizado
        
        # Usando cache de produtos já carregado (evita 3ª query duplicada)
        todos_tipos_produto = {}
        for p in all_prods_cached:
             if p['nome_produto'] not in todos_tipos_produto:
                 todos_tipos_produto[p['nome_produto']] = p['id']

        filtro_numero_processo = st.text_input("🔍 Filtrar por Número do Processo:", key="chefe_filtro_num", placeholder="Digite o número do processo...")
        
        filtros_col1, filtros_col2, filtros_col3, filtros_col4 = st.columns(4)
        with filtros_col1:
            opcoes_status = ["No Prazo", "Atrasado", "Concluído", "Devolvido", "Finalizado", "Processo com o Procurador", "Revisão Atrasada"]
            filtro_status = st.multiselect("📊 Status", options=opcoes_status, default=st.session_state.get('chefe_filtro_status', []))
            filtro_servidor = st.multiselect("👤 Servidor", options=servidores_nomes_equipe, default=st.session_state.get('chefe_filtro_servidor', []))
        with filtros_col2:
            filtro_procurador_nomes = st.multiselect("⚖️ Procurador", options=list(procuradores_dict.keys()), default=st.session_state.get('chefe_filtro_procurador', []))
            filtro_tipo_produto_nomes = st.multiselect("📋 Tipo de Processo", options=list(todos_tipos_produto.keys()), default=st.session_state.get('chefe_filtro_tipo_produto', []))
        with filtros_col3:
            filtro_data_inicio = st.date_input("📅 De:", value=st.session_state.get('chefe_filtro_data_inicio'), key="chefe_di", format="DD/MM/YYYY")
            filtro_data_fim = st.date_input("📅 Até:", value=st.session_state.get('chefe_filtro_data_fim'), key="chefe_df", format="DD/MM/YYYY")
        with filtros_col4:
            ordenar_por = st.selectbox("📈 Ordenar por", ["Mais Recentes", "Mais Antigos", "Prazo Restante (Crescente)", "Prazo Restante (Decrescente)"], key="chefe_ordenar")
            items_per_page = st.selectbox("📄 Itens por página", [10, 25, 50, 100], index=1, key="chefe_items_per_page")
        
        # Filtro de Status MPC (nova linha)
        opcoes_status_mpc = ["No prazo MPC", "Atrasado MPC", "Não se aplica"]
        filtro_status_mpc = st.multiselect("📆 Status MPC", options=opcoes_status_mpc, default=st.session_state.get('chefe_filtro_status_mpc', []))

        st.markdown('</div>', unsafe_allow_html=True)


        # Legenda de ícones
        st.markdown("""
        <div class="icon-legend">
            <div class="legend-title">📖 Legenda de Ícones</div>
            <div class="legend-items">
                <div class="legend-item"><span>💬</span> Comentários não lidos</div>
                <div class="legend-item"><span>📎</span> Possui anexos</div>
                <div class="legend-item"><span>⭐</span> Favorito</div>
                <div class="legend-item"><span>📖</span> Descrição disponível</div>
                <div class="legend-item"><span>📄</span> Modelo disponível</div>
                <div class="legend-item"><span>🔥</span> Urgente</div>
                <div class="legend-item"><span>⚠️</span> Prioritário</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.spinner("🔄 Carregando processos..."):
            qb = QueryBuilder("processos").eq("id_chefe_gabinete", id_chefe_para_acoes)

            # Filtro server-side por número do processo (busca em TODO o banco)
            if filtro_numero_processo:
                search_clean = filtro_numero_processo.strip()
                qb.ilike_all_words("processo_numero", search_clean)
            
            # Note: complex OR logic (status_servidor OR status_chefe) is handled in Python below (lines 846-849)
            # The QueryBuilder doesn't support or_filter, so we fetch all and filter in Python
            
            if filtro_servidor:
                # Need IDs
                f_ids = QueryBuilder("usuarios").in_list("nome_completo", filtro_servidor).select("id").execute()
                ids_flat = [x['id'] for x in f_ids]
                if ids_flat:
                    qb.in_list("id_servidor_responsavel", ids_flat)
            
            if filtro_procurador_nomes:
                 ids = [procuradores_dict[n] for n in filtro_procurador_nomes]
                 qb.in_list("id_procurador", ids)
            
            if filtro_tipo_produto_nomes:
                ids = [todos_tipos_produto[n] for n in filtro_tipo_produto_nomes]
                qb.in_list("id_tipo_produto", ids)
                
            if filtro_data_inicio: qb.gte("data_atribuicao_servidor", filtro_data_inicio.isoformat())
            if filtro_data_fim: qb.lte("data_atribuicao_servidor", filtro_data_fim.isoformat())
            
            processos_filtrados = qb.execute()
            
            # Application of Python Filters for complex OR logic (Status)
            if filtro_status:
                def check_status(p):
                    return (p.get('status_servidor') in filtro_status) or (p.get('status_chefe') in filtro_status)
                processos_filtrados = [p for p in processos_filtrados if check_status(p)]

            # Refinamento local: reordena por similaridade (fuzzy matching)
            if filtro_numero_processo and processos_filtrados:
                processos_filtrados = common_utils.filter_by_similarity(
                    search_term=filtro_numero_processo,
                    items=processos_filtrados,
                    key_func=lambda p: p.get('processo_numero', '')
                )
            
            # Filtro de Status MPC
            if filtro_status_mpc:
                processos_filtrados = [p for p in processos_filtrados if p.get('status_mpc') in filtro_status_mpc]


            # --- PRÉ-CÁLCULO DOS DADOS ---
            hoje = today_brazil()
            processos_com_dados = []
            
            # Usando caches já carregados no início da página (evita queries duplicadas):
            # - produtos_cache: {id: produto_dict}
            # - usuarios_cache: {id: usuario_dict}
            
            # Batch check for unread comments (optimization: 2 queries instead of N*2)
            pids = [p['id'] for p in processos_filtrados]
            unread_comments_cache = common_utils.batch_has_unread_comments(pids, st.session_state.user_id) if processos_filtrados else {}

            for p in processos_filtrados:
                produto_obj = produtos_cache.get(p['id_tipo_produto'])
                if not produto_obj: continue

                p_id = p['id']
                dados = {
                    "processo": p,
                    "id": p_id,
                    "numero": p.get('processo_numero'),
                    "status_servidor": p.get('status_servidor'),
                    "status_chefe": p.get('status_chefe'),
                    "status_mpc": p.get('status_mpc', 'Não se aplica'),
                    "prazo_mpc_dias": p.get('prazo_mpc_dias'),
                    "data_entrada_mpc": date.fromisoformat(p['data_entrada_mpc']) if p.get('data_entrada_mpc') else None,
                    "prioridade": p.get('prioridade'),
                    "data_atribuicao": date.fromisoformat(p['data_atribuicao_servidor']) if p.get('data_atribuicao_servidor') else None,
                    "nome_produto": produto_obj.get('nome_produto'),
                    "descricao_produto": produto_obj.get('descricao'),
                    "template_path": produto_obj.get('template_path'),
                    "servidor_nome": usuarios_cache.get(p.get('id_servidor_responsavel'), {}).get('nome_completo', 'N/A'),
                    "procurador_nome": usuarios_cache.get(p.get('id_procurador'), {}).get('nome_completo', 'N/A'),

                    "tem_nao_lidos": unread_comments_cache.get(p_id, False),  # Uses batch cache
                    "dias_suspensos": p.get('prazo_total_dias_suspenso', 0),
                    "id_servidor": p.get('id_servidor_responsavel')
                }

                
                # Prazo calc
                if p.get('nao_se_aplica_prazo_servidor'):
                    dados["prazo_restante"] = float('inf')
                    dados["data_final"] = None
                    dados["prazo_status"] = "N/A"
                elif p.get('status_servidor') in ["Concluído", "Finalizado"]:
                     dados["prazo_restante"] = float('inf')
                     dados["data_final"] = None
                     # Conclusão logic if needed
                else:
                    data_atrib_dt = dados["data_atribuicao"] or today_brazil()
                    dt_final = calculate_due_date(
                        data_atrib_dt,
                        p.get('prazo_servidor_aplicado', 0),
                        produto_obj.get('tipo_contagem_prazo', 'dias uteis'),
                        p.get('id_servidor_responsavel'),
                        dias_suspensos=p.get('prazo_total_dias_suspenso', 0)
                    )
                    dados["data_final"] = dt_final
                    dados["prazo_restante"] = (dt_final - hoje).days
                
                processos_com_dados.append(dados)
            
            # --- SORTING ---
            ordenar_por = st.session_state.get("chefe_ordenar") # getting from widget session key directly or var
            if ordenar_por == "Prazo Restante (Crescente)":
                processos_ordenados = sorted(processos_com_dados, key=lambda x: x["prazo_restante"])
            elif ordenar_por == "Prazo Restante (Decrescente)":
                processos_ordenados = sorted(processos_com_dados, key=lambda x: x["prazo_restante"], reverse=True)
            elif ordenar_por == "Mais Antigos":
                processos_ordenados = sorted(processos_com_dados, key=lambda x: x["data_atribuicao"] or date.min)
            else: # Mais Recentes
                processos_ordenados = sorted(processos_com_dados, key=lambda x: x["data_atribuicao"] or date.min, reverse=True)

            # --- PAGINATION ---
            st.markdown("---")
            total_items = len(processos_ordenados)
            if 'chefe_page_number' not in st.session_state: st.session_state.chefe_page_number = 0
            
            # Adjust page number if out of bounds
            # ... logic ...
            
            start_idx = st.session_state.chefe_page_number * items_per_page
            end_idx = start_idx + items_per_page
            displayed_items = processos_ordenados[start_idx:end_idx]
            
            if not displayed_items:
                st.info("Nenhum processo encontrado.")
            else:
                 # Display logic...
                 # Delega a renderização para o component
                 process_list.render_process_list(displayed_items, hoje)

            # Pagination controls
            # ...
            if (len(processos_ordenados) > items_per_page):
                 c1, c2, c3 = st.columns([1,2,1])
                 if c1.button("⬅️ Anterior", disabled=st.session_state.chefe_page_number==0):
                     st.session_state.chefe_page_number -= 1
                     st.rerun()
                 c3.button("Próxima ➡️", disabled=end_idx>=total_items, key="next_pg_btn", on_click=lambda: st.session_state.update(chefe_page_number=st.session_state.chefe_page_number+1))



    except Exception as e:
        st.error(f"Erro ao carregar dashboard: {e}")
        import traceback
        st.code(traceback.format_exc())

