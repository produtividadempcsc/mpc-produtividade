import auth
import streamlit as st
from datetime import date, timedelta
import os
from sidebar import build_sidebar

# Módulos do projeto
import utils.ui as ui_utils
import utils.common as common_utils
import file_utils
# Módulos do projeto
import utils.ui as ui_utils
import utils.common as common_utils
import file_utils
from forms import display_edit_processo_form
from supabase_client import select_all, QueryBuilder, insert, delete_by_id
from db_compat import (
    get_user_by_id,
    get_all_users,
    calculate_due_date_with_details,
    is_process_favorite,
    toggle_process_favorite,
    get_product_types, # ensure this exists or use select_all('tipo_produto')
    get_user_favorites
)
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

# CSS CUSTOMIZADO PARA LAYOUT PROFISSIONAL
st.markdown("""
<style>
    /* Variáveis das cores do sistema */
    :root {
        --primary-color: #9E0520;
        --background-color: #E9E3DF;
        --secondary-background: #9CAFAA;
        --text-color: #000000;
        --light-gray: #F5F5F5;
        --border-color: #D4D4D4;
        --success-color: #28A745;
        --warning-color: #FFC107;
        --danger-color: #DC3545;
        --info-color: #17A2B8;
    }

    /* Estilo geral da página */

    /* Header principal */
    .main-header {
        background: linear-gradient(135deg, var(--primary-color) 0%, #B8062A 100%);
        color: white;
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(158, 5, 32, 0.3);
    }

    .main-header h1 {
        margin: 0;
        font-size: 2.2em;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    .main-header p {
        margin: 10px 0 0 0;
        font-size: 1.1em;
        opacity: 0.9;
    }

    /* KPIs Cards */
    .kpi-container {
        display: flex;
        gap: 20px;
        margin: 25px 0;
        flex-wrap: wrap;
    }

    .kpi-card {
        background: white;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        border-left: 5px solid var(--primary-color);
        min-width: 200px;
        flex: 1;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }

    .kpi-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 5px 20px rgba(158, 5, 32, 0.2);
    }

    .kpi-value {
        font-size: 2.5em;
        font-weight: bold;
        color: var(--primary-color);
        margin: 10px 0;
    }

    .kpi-label {
        font-size: 0.9em;
        color: var(--text-color);
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Seção de formulário */
    .form-section {
        background: white;
        border-radius: 12px;
        padding: 25px;
        margin: 25px 0;
        box-shadow: 0 3px 15px rgba(0,0,0,0.1);
        border-top: 4px solid var(--secondary-background);
    }

    .form-header {
        color: var(--primary-color);
        font-size: 1.4em;
        font-weight: 600;
        margin-bottom: 20px;
        padding-bottom: 10px;
        border-bottom: 2px solid var(--background-color);
    }

    /* Filtros */
    .filters-container {
        background: white;
        border-radius: 12px;
        padding: 25px;
        margin: 25px 0;
        box-shadow: 0 3px 15px rgba(0,0,0,0.1);
        border-left: 4px solid var(--secondary-background);
    }

    .filters-header {
        color: var(--primary-color);
        font-size: 1.3em;
        font-weight: 600;
        margin-bottom: 20px;
        display: flex;
        align-items: center;
    }

    .filters-header::before {
        content: "🔍";
        margin-right: 10px;
        font-size: 1.2em;
    }

    /* Cards dos processos */
    .process-card {
        background: white;
        border-radius: 12px;
        margin: 15px 0;
        box-shadow: 0 3px 15px rgba(0,0,0,0.1);
        border-left: 5px solid var(--secondary-background);
        transition: all 0.3s ease;
    }

    .process-card:hover {
        box-shadow: 0 5px 25px rgba(0,0,0,0.15);
        transform: translateX(3px);
    }

    .process-card.urgente {
        border-left-color: var(--danger-color);
        background: linear-gradient(90deg, #FFEBEE 0%, white 50%);
    }

    .process-card.prioritario {
        border-left-color: var(--warning-color);
        background: linear-gradient(90deg, #FFF8E1 0%, white 50%);
    }

    .process-card.atrasado {
        border-left-color: var(--danger-color);
        background: linear-gradient(90deg, #FFEBEE 0%, white 50%);
        animation: pulse-red 2s infinite;
    }

    @keyframes pulse-red {
        0%, 100% { box-shadow: 0 3px 15px rgba(0,0,0,0.1); }
        50% { box-shadow: 0 5px 25px rgba(220, 53, 69, 0.3); }
    }

    /* Header do processo */
    .process-header {
        padding: 20px 25px;
        border-bottom: 1px solid var(--border-color);
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: linear-gradient(90deg, var(--background-color) 0%, white 100%);
        border-radius: 12px 12px 0 0;
    }

    .process-info {
        flex: 1;
        display: flex;
        flex-wrap: wrap;
        gap: 20px;
        align-items: center;
    }

    .process-number {
        font-size: 1.3em;
        font-weight: bold;
        color: var(--primary-color);
    }

    .process-status {
        padding: 5px 12px;
        border-radius: 20px;
        font-size: 0.85em;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .status-no-prazo {
        background-color: var(--success-color);
        color: white;
    }

    .status-atrasado {
        background-color: var(--danger-color);
        color: white;
    }

    .status-concluido {
        background-color: var(--info-color);
        color: white;
    }

    .status-devolvido {
        background-color: var(--warning-color);
        color: white;
    }

    /* Ícones de prioridade e status */
    .priority-icons {
        display: flex;
        gap: 8px;
        align-items: center;
        font-size: 1.2em;
    }

    /* Conteúdo do processo */
    .process-content {
        padding: 25px;
    }

    .process-details {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 15px;
        margin-bottom: 20px;
    }

    .detail-item {
        display: flex;
        flex-direction: column;
        gap: 5px;
    }

    .detail-label {
        font-size: 0.85em;
        color: #666;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }

    .detail-value {
        font-size: 1em;
        color: var(--text-color);
        font-weight: 500;
    }

    /* Observações */
    .observations-box {
        background: var(--background-color);
        border-radius: 8px;
        padding: 15px;
        margin: 20px 0;
        border-left: 4px solid var(--primary-color);
    }

    .observations-label {
        font-weight: 600;
        color: var(--primary-color);
        margin-bottom: 8px;
    }

    /* Botões de ação */
    .action-buttons {
        display: flex;
        gap: 10px;
        margin-top: 20px;
        flex-wrap: wrap;
        padding-top: 20px;
        border-top: 1px solid var(--border-color);
    }

    .action-button {
        padding: 8px 16px;
        border-radius: 6px;
        border: none;
        font-weight: 500;
        cursor: pointer;
        transition: all 0.3s ease;
        text-decoration: none;
        display: inline-block;
        text-align: center;
        min-width: 100px;
    }

    .btn-primary {
        background-color: var(--primary-color);
        color: white;
    }

    .btn-primary:hover {
        background-color: #7A041A;
        transform: translateY(-2px);
    }

    .btn-secondary {
        background-color: var(--secondary-background);
        color: white;
    }

    .btn-secondary:hover {
        background-color: #7A9B95;
        transform: translateY(-2px);
    }

    .btn-outline {
        background-color: white;
        border: 2px solid var(--primary-color);
        color: var(--primary-color);
    }

    .btn-outline:hover {
        background-color: var(--primary-color);
        color: white;
    }

    /* Paginação */
    .pagination-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 30px 0;
        gap: 15px;
    }

    .pagination-info {
        background: white;
        padding: 12px 20px;
        border-radius: 8px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        font-weight: 500;
    }

    /* Legenda de ícones */
    .icon-legend {
        background: white;
        border-radius: 8px;
        padding: 15px;
        margin: 20px 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    .legend-title {
        font-weight: 600;
        color: var(--primary-color);
        margin-bottom: 10px;
    }

    .legend-items {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
    }

    .legend-item {
        display: flex;
        align-items: center;
        gap: 5px;
        font-size: 0.9em;
    }

    /* Responsividade */
    @media (max-width: 768px) {
        .kpi-container {
            flex-direction: column;
        }
        
        .process-info {
            flex-direction: column;
            align-items: flex-start;
            gap: 10px;
        }
        
        .action-buttons {
            justify-content: center;
        }
        
        .process-details {
            grid-template-columns: 1fr;
        }
    }

    /* Animações */
    .fade-in {
        animation: fadeIn 0.5s ease-in;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Customização do Streamlit */
    .stExpander > div:first-child {
        background: transparent !important;
        border: none !important;
    }
    
    .stSelectbox > div > div > div {
        background-color: white;
        border: 2px solid var(--border-color);
        border-radius: 6px;
    }
    
    .stTextInput > div > div > input {
        background-color: white;
        border: 2px solid var(--border-color);
        border-radius: 6px;
    }
    
    .stDateInput > div > div > input {
        background-color: white;
        border: 2px solid var(--border-color);
        border-radius: 6px;
    }
    
    .stTextArea > div > div > textarea {
        background-color: white;
        border: 2px solid var(--border-color);
        border-radius: 6px;
    }

    /* Métricas customizadas */
    div[data-testid="metric-container"] {
        background: white;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        border-left: 5px solid var(--primary-color);
        transition: transform 0.3s ease;
    }

    div[data-testid="metric-container"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 5px 20px rgba(158, 5, 32, 0.2);
    }

    div[data-testid="metric-container"] > div:first-child {
        color: var(--primary-color) !important;
        font-weight: 600 !important;
    }

    div[data-testid="metric-container"] > div:last-child {
        color: var(--primary-color) !important;
        font-size: 2em !important;
        font-weight: bold !important;
    }
</style>
""", unsafe_allow_html=True)

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
            # query = query.filter(Processo.status_servidor.in_(filtro_status) | Processo.status_chefe.in_(filtro_status))
            # Supabase doesn't support OR across columns easily in simple builder usually, but postgrest supports it.
            # QueryBuilder wrapper might support `or_` string syntax.
            # 'status_servidor.in.(A,B),status_chefe.in.(A,B)'
            # But simpler: fetch filtered locally or separate queries?
            # Or assume logic: if "No Prazo" is selected, it matches either status.
            # Let's filter locally for status OR condition if complex.
            # But list size might be large.
            # For now, let's fetch all (or filtered by other strict criteria if possible) and filter status in Python.
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


        if filtro_numero_processo:
            processos_filtrados = common_utils.filter_by_similarity(
                search_term=filtro_numero_processo,
                items=processos_filtrados,
                key_func=lambda p: p['processo_numero'] # Dict access
            )
            
        # --- REESTRUTURAÇÃO: Pré-cálculo para otimização ---
            
        # --- REESTRUTURAÇÃO: Pré-cálculo para otimização ---
        hoje = date.today()
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

        # --- Otimização: Pré-busca de dados de favoritos e anexos ---
        # --- Otimização: Pré-busca de dados de favoritos e anexos ---
        # usuario_logado = db.query(Usuario).filter_by(id=st.session_state.user_id).one()
        # processos_favoritos_ids = {p.id for p in usuario_logado.processos_favoritos}

        
        processo_ids_pagina = [item['processo']['id'] for item in paginated_items]
        # anexos_query = db.query(AnexoProcesso.id_processo).filter(AnexoProcesso.id_processo.in_(processo_ids_pagina)).all()
        # processos_com_anexo_ids = {anexo.id_processo for anexo in anexos_query}
        if processo_ids_pagina:
             anexos_data = QueryBuilder("anexos_processos").in_list("id_processo", processo_ids_pagina).select("id_processo").execute()
             processos_com_anexo_ids = {a['id_processo'] for a in anexos_data}
        else:
             processos_com_anexo_ids = set()

        def get_priority_icon(priority):
            if priority == 'Urgente':
                return '🔥'
            elif priority == 'Prioritário': 
                return '⚠️'
            return ''



        for item in paginated_items:
            processo = item["processo"]
            
            # Access Dict API
            pid = processo.get('id')
            pnumero = processo.get('processo_numero')
            prioridade = processo.get('prioridade')
            status_serv = processo.get('status_servidor')
            status_chef = processo.get('status_chefe')
            conclusao_dt = processo.get('data_conclusao_servidor')
            nao_aplica = processo.get('nao_se_aplica_prazo_servidor')
            
            status_geral = status_chef if conclusao_dt else status_serv
            status_icon = ui_utils.get_status_emoji(status_geral)
            priority_icon = get_priority_icon(prioridade)
            tem_nao_lidos = common_utils.has_unread_comments(pid, st.session_state.user_id)
            unread_icon = "💬" if tem_nao_lidos else ""
            tem_anexo = pid in processos_com_anexo_ids
            anexo_icon = "📎" if tem_anexo else ""
            
            # Card do processo com estilo personalizado
            # Helper function card_class updated? "get_process_card_class" needs to handle dict.
            # I'll update get_process_card_class to accept dict or just rewrite it inline/before loop if complex.
            # Actually get_process_card_class was defined inside loop or before? Before loop.
            # I need to update it to use dict access.
            
            classes = ["process-card"]
            if prioridade == 'Urgente': classes.append("urgente")
            elif prioridade == 'Prioritário': classes.append("prioritario")
            if status_geral == 'Atrasado': classes.append("atrasado")
            card_class = " ".join(classes)
            
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            
            # Header do processo
            if conclusao_dt:
                if status_geral in ["Aguardando Análise", "Revisão Atrasada"]:
                    prazo_info = f"📅 {item['data_final_revisao_ajustada'].strftime('%d/%m/%Y')}"
                    servidor_info = "Em revisão"
                else:
                    prazo_info = f"👤 {item['servidor_nome']}"
                    servidor_info = status_geral
            else:
                if nao_aplica:
                    prazo_info = "⏰ Não se aplica"
                    servidor_info = f"👤 {item['servidor_nome']}"
                else:
                    prazo_restante_str = f"{item['dias_restantes']} dias"
                    prazo_info = f"⏳ {prazo_restante_str} | 📅 {item['data_final_servidor_ajustada'].strftime('%d/%m/%Y')}"
                    servidor_info = f"👤 {item['servidor_nome']}"

            st.markdown(f"""
            <div class="process-header">
                <div class="process-info">
                    <div class="priority-icons">{unread_icon} {priority_icon} {status_icon} {anexo_icon}</div>
                    <div class="process-number">{pnumero}</div>
                    <div class="process-status status-{status_geral.lower().replace(' ', '-')}">{status_geral}</div>
                    <div>{servidor_info}</div>
                    <div>{prazo_info}</div>
                    <div><span style="font-weight: 600;">Prioridade:</span> {prioridade}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Conteúdo do processo (inicialmente oculto, expandido via expander)
            with st.expander("📋 Ver detalhes e ações", expanded=False):
                st.markdown('<div class="process-content">', unsafe_allow_html=True)
                
                # Detalhes do processo
                # produto_obj already in loop above as 'produto_obj' local var? No, loop var was 'item'.
                # Need to fetch product name from item.
                
                # Parse Atribuicao Date again for display
                atrib_date_str = processo.get('data_atribuicao_servidor')
                atrib_formatted = datetime.fromisoformat(atrib_date_str).strftime('%d/%m/%Y') if atrib_date_str else ""
                
                st.markdown("""
                <div class="process-details">
                    <div class="detail-item">
                        <div class="detail-label">Tipo de Produto</div>
                        <div class="detail-value">{}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Procurador Vinculado</div>
                        <div class="detail-value">{}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Atribuído em</div>
                        <div class="detail-value">{}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Status Atual</div>
                        <div class="detail-value" style="color: {};">{}</div>
                    </div>
                </div>
                """.format(
                    item['produto_nome'],
                    item['procurador_nome'],
                    atrib_formatted,
                    ui_utils.get_status_color(status_geral),
                    status_geral
                ), unsafe_allow_html=True)

                # Informações de prazo
                if not nao_aplica and 'data_final_servidor_ajustada' in item:
                    data_final_servidor = item["data_final_servidor_ajustada"] - timedelta(days=item["ajuste_servidor"])
                    st.markdown(f"""
                    <div class="detail-item">
                        <div class="detail-label">Prazo do Servidor</div>
                        <div class="detail-value">
                            {data_final_servidor.strftime('%d/%m/%Y')} + {item['ajuste_servidor']} dias = 
                            <strong>{item['data_final_servidor_ajustada'].strftime('%d/%m/%Y')}</strong>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                if conclusao_dt and 'data_final_revisao_ajustada' in item:
                    data_final_revisao = item["data_final_revisao_ajustada"] - timedelta(days=item["ajuste_revisao"])
                    st.markdown(f"""
                    <div class="detail-item">
                        <div class="detail-label">Prazo de Revisão</div>
                        <div class="detail-value">
                            {data_final_revisao.strftime('%d/%m/%Y')} + {item['ajuste_revisao']} dias = 
                            <strong>{item['data_final_revisao_ajustada'].strftime('%d/%m/%Y')}</strong>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Observações do chefe
                obs_chefe = processo.get('observacao_chefe')
                if obs_chefe:
                    st.markdown(f"""
                    <div class="observations-box">
                        <div class="observations-label">📝 Observações do Gabinete:</div>
                        <div>{obs_chefe}</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Botões de ação
                st.markdown('<div class="action-buttons">', unsafe_allow_html=True)
                
                action_cols = st.columns([1, 2, 2, 2, 2])
                
                # Ícones de ação
                with action_cols[0]:
                    icon_col1, icon_col2 = st.columns(2)
                    with icon_col1:
                         # Need product description. Where to get?
                         # I need to fetch it in cache. Cache was just name?
                         # produtos_cache = {p['id']: p for p in all_products} (it IS dict of full obj)
                         prod_dict = produtos_cache.get(processo.get('id_tipo_produto'))
                         desc = prod_dict.get('descricao') if prod_dict else None
                         if desc:
                            with st.popover("📖", help="Ver descrição do tipo de produto"):
                                st.markdown(desc)
                         else:
                            st.button("📖", key=f"wiki_gabinete_{pid}", help="Nenhuma descrição disponível", disabled=True)
                    with icon_col2:
                        template_path = prod_dict.get('template_path') if prod_dict else None
                        template_exists = template_path and os.path.exists(template_path)
                        if template_exists:
                            with open(template_path, "rb") as f:
                                st.download_button(
                                    label="📄",
                                    data=f.read(),
                                    file_name=os.path.basename(template_path),
                                    mime="application/octet-stream",
                                    key=f"template_gabinete_{processo.get('id')}",
                                    help="Baixar modelo"
                                )
                        else:
                            st.button("📄", key=f"template_gabinete_{processo.get('id')}", help="Nenhum modelo disponível", disabled=True)

                # Botões principais
                with action_cols[1]:
                    if st.button("✏️ Editar Processo", key=f"edit_detalhe_{processo.get('id')}", width='stretch'):
                        st.session_state['processo_para_editar_id'] = processo.get('id')
                        st.rerun()
                
                with action_cols[2]:
                    button_label = "💬 Comentário Não Lido" if tem_nao_lidos else "💬 Comentários"
                    button_type = "primary" if tem_nao_lidos else "secondary"
                    if st.button(button_label, key=f"comments_proc_{processo.get('id')}", width='stretch', type=button_type):
                        st.session_state['processo_id'] = processo.get('id')
                        st.session_state['came_from'] = 'Pages/Processos_no_Gabinete.py'
                        st.switch_page('Pages/Comentarios_Processo.py')

                with action_cols[3]:
                    st.empty() # Botão 'Ver Processo' removido
                
                with action_cols[4]:
                    if "show_history" not in st.session_state:
                        st.session_state.show_history = {}
                    if st.button("📜 Histórico", key=f"hist_chefe_{processo.get('id')}", width='stretch'):
                        st.session_state.show_history[processo.get('id')] = not st.session_state.show_history.get(processo.get('id'), False)
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

                # Histórico do processo
                if st.session_state.get("show_history", {}).get(processo.get('id'), False):
                    st.markdown("---")
                    ui_utils.display_process_history(processo)

                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)

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
