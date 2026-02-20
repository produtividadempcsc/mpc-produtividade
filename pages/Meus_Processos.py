import auth
import streamlit as st
from datetime import date, timedelta
import os
from sidebar import build_sidebar

# Módulos do projeto
import utils.ui as ui_utils
import utils.common as common_utils
import file_utils
from forms import display_servidor_update_form
# Migration imports
from supabase_client import QueryBuilder, select_all
from db_compat import (
    get_user_by_id,
    get_product_type_by_id,
    calculate_due_date,
    calculate_due_date_with_details,
    get_user_bosses,
    get_prosecutors_linked_to_users
)

import auth
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
        padding: 10px 10px;
        font-family: inherit;
    }

    .process-details {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin-bottom: 20px;
        padding: 18px;
        background: #FAFAFA;
        border-radius: 10px;
        border: 1px solid #EBEBEB;
    }

    .detail-item {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }

    .detail-label {
        font-size: 0.78em;
        color: var(--primary-color);
        text-transform: uppercase;
        letter-spacing: 0.8px;
        font-weight: 700;
    }

    .detail-value {
        font-size: 0.95em;
        color: #333;
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

    /* Botões de ação (estilizar botões Streamlit dentro do expander) */
    .stExpander [data-testid="stVerticalBlock"] button {
        padding: 10px 100px !important;
        font-size: 0.95em !important;
        font-weight: 600 !important;
        border-radius: 8px !important;
        border: 2px solid var(--primary-color) !important;
        color: var(--primary-color) !important;
        background: white !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }

    .stExpander [data-testid="stVerticalBlock"] button:hover {
        background: var(--primary-color) !important;
        color: white !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(158, 5, 32, 0.3) !important;
    }

    .action-buttons {
        display: flex;
        gap: 10px;
        margin-top: 20px;
        flex-wrap: wrap;
        padding-top: 20px;
        border-top: 1px solid var(--border-color);
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

build_sidebar()

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
        all_user_processes = QueryBuilder("processos").eq("id_servidor_responsavel", user_id).execute()
    active_statuses = ['No Prazo', 'Atrasado', 'Devolvido']
    kpi_processes = [p for p in all_user_processes if p.get('status_servidor') in active_statuses]
    total_ativos = len(kpi_processes)
    no_prazo = len([p for p in kpi_processes if p.get('status_servidor') == 'No Prazo'])
    atrasados = len([p for p in kpi_processes if p.get('status_servidor') == 'Atrasado'])
    
    # KPIs com design customizado
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-value">{total_ativos}</div>
            <div class="kpi-label">Processos Ativos</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value" style="color: #28a745;">{no_prazo}</div>
            <div class="kpi-label">No Prazo</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value" style="color: #dc3545;">{atrasados}</div>
            <div class="kpi-label">Atrasados</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    


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
    
    if filtro_numero_processo:
        processos_filtrados = common_utils.filter_by_similarity(
            search_term=filtro_numero_processo,
            items=processos_filtrados,
            key_func=lambda p: p.get('processo_numero', '')
        )


    # --- SORTING ---
    hoje = date.today()
    processos_com_prazo = []
    
    # Cache all product types for efficiency
    all_product_types_map = {p.get('id'): p for p in all_tipos_produto}
    
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
            
        data_final = calculate_due_date(
            data_atrib, 
            p.get('prazo_servidor_aplicado'), 
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
        
        def get_priority_icon(priority):
            if priority == 'Urgente':
                return '🔥'
            elif priority == 'Prioritário':
                return '⚠️'
            return '📄'


        def get_process_card_class(processo_dict, status_geral):
            classes = ["process-card"]
            if processo_dict.get('prioridade') == 'Urgente':
                classes.append("urgente")
            elif processo_dict.get('prioridade') == 'Prioritário':
                classes.append("prioritario")
            if status_geral == 'Atrasado':
                classes.append("atrasado")
            return " ".join(classes)

        # Cache all users for efficiency
        all_users = select_all("usuarios")
        users_map = {u.get('id'): u for u in all_users}

        # Batch check for unread comments (optimization: 2 queries instead of N*2)
        paginated_processo_ids = [p[0].get('id') for p in paginated_items]
        unread_comments_cache = common_utils.batch_has_unread_comments(paginated_processo_ids, st.session_state.user_id)

        for processo, dias_restantes in paginated_items:
            p_id = processo.get('id')
            p_status_servidor = processo.get('status_servidor', '')
            p_prioridade = processo.get('prioridade', 'Regular')
            p_processo_numero = processo.get('processo_numero', '')
            p_nao_se_aplica_prazo = processo.get('nao_se_aplica_prazo_servidor', False)
            p_status_chefe = processo.get('status_chefe', '')
            
            status_icon = ui_utils.get_status_emoji(p_status_servidor)
            priority_icon = get_priority_icon(p_prioridade)
            tem_nao_lidos = unread_comments_cache.get(p_id, False)  # Uses batch cache
            unread_icon = "💬" if tem_nao_lidos else ""
            
            # Card do processo com estilo personalizado
            card_class = get_process_card_class(processo, p_status_servidor)
            
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            
            # Parse data_conclusao_servidor
            data_conclusao_str = processo.get('data_conclusao_servidor')
            if data_conclusao_str and isinstance(data_conclusao_str, str):
                try:
                    data_conclusao = date.fromisoformat(data_conclusao_str[:10])
                    data_entrega = data_conclusao.strftime('%d/%m/%Y')
                except:
                    data_entrega = "Data não informada"
            elif data_conclusao_str:
                data_entrega = data_conclusao_str.strftime('%d/%m/%Y')
            else:
                data_entrega = "Data não informada"
            
            # Header do processo
            if p_status_servidor == "Concluído":
                info_chefe = "Pendente de revisão pelo chefe de gabinete" if p_status_chefe == "Aguardando Análise" else "Processo com o procurador"
                prazo_info = f"Entregue em: {data_entrega}"
                servidor_info = f"Status: {info_chefe}"
            elif p_status_servidor == "Finalizado":
                prazo_info = f"Entregue em: {data_entrega}"
                servidor_info = ""
            else:
                if p_nao_se_aplica_prazo:
                    prazo_info = "⏰ Não se aplica"
                    servidor_info = ""
                else:
                    produto_obj = all_product_types_map.get(processo.get('id_tipo_produto'))
                    data_atrib_str = processo.get('data_atribuicao_servidor')
                    if data_atrib_str and isinstance(data_atrib_str, str):
                        data_atrib = date.fromisoformat(data_atrib_str)
                    else:
                        data_atrib = data_atrib_str
                    
                    data_final_calculada = calculate_due_date(
                        data_atrib, 
                        processo.get('prazo_servidor_aplicado'), 
                        produto_obj.get('tipo_contagem_prazo') if produto_obj else 'dias uteis', 
                        processo.get('id_servidor_responsavel'), 
                        dias_suspensos=processo.get('prazo_total_dias_suspenso', 0)
                    )
                    prazo_restante_str = f"{dias_restantes} dias"
                    prazo_info = f"⏳ {prazo_restante_str} | 📅 {data_final_calculada.strftime('%d/%m/%Y')}"
                    servidor_info = ""

            st.markdown(f"""
            <div class="process-header">
                <div class="process-info">
                    <div class="priority-icons">{unread_icon} {priority_icon} {status_icon}</div>
                    <div class="process-number">{p_processo_numero}</div>
                    <div class="process-status status-{p_status_servidor.lower().replace(' ', '-')}">{p_status_servidor}</div>
                    <div>{servidor_info}</div>
                    <div>{prazo_info}</div>
                    <div><span style="font-weight: 600;">Prioridade:</span> {p_prioridade}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)


            # Conteúdo do processo (inicialmente oculto, expandido via expander)
            with st.expander("📋 Ver detalhes e ações", expanded=False):
                st.markdown('<div class="process-content">', unsafe_allow_html=True)
                
                # Detalhes do processo usando dados do cache
                produto_obj = all_product_types_map.get(processo.get('id_tipo_produto'))
                chefe_user = users_map.get(processo.get('id_chefe_gabinete'), {})
                chefe_nome = chefe_user.get('nome_completo', 'N/A')
                procurador_user = users_map.get(processo.get('id_procurador'), {})
                procurador_nome = procurador_user.get('nome_completo', 'N/A')
                
                # Parse data_atribuicao_servidor para formato exibido
                data_atrib_str = processo.get('data_atribuicao_servidor')
                if data_atrib_str and isinstance(data_atrib_str, str):
                    data_atrib = date.fromisoformat(data_atrib_str)
                    data_atrib_fmt = data_atrib.strftime('%d/%m/%Y')
                elif data_atrib_str:
                    data_atrib_fmt = data_atrib_str.strftime('%d/%m/%Y')
                else:
                    data_atrib_fmt = 'N/A'
                    data_atrib = None
                
                st.markdown("""
                <div class="process-details">
                    <div class="detail-item">
                        <div class="detail-label">Tipo de Produto</div>
                        <div class="detail-value">{}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Chefe de Gabinete</div>
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
                </div>
                """.format(
                    produto_obj.get('nome_produto') if produto_obj else 'N/A',
                    chefe_nome,
                    procurador_nome,
                    data_atrib_fmt
                ), unsafe_allow_html=True)

                # Informações de prazo
                if not p_nao_se_aplica_prazo and data_atrib:
                    data_final_ajustada, ajuste = calculate_due_date_with_details(
                        start_date=data_atrib,
                        prazo_dias=processo.get('prazo_servidor_aplicado'),
                        tipo_contagem=produto_obj.get('tipo_contagem_prazo') if produto_obj else 'dias uteis',
                        id_usuario=processo.get('id_servidor_responsavel'),
                        dias_suspensos=processo.get('prazo_total_dias_suspenso', 0)
                    )
                    data_final = data_final_ajustada - timedelta(days=ajuste)
                    st.markdown(f"""
                    <div class="detail-item">
                        <div class="detail-label">Prazo para Conclusão</div>
                        <div class="detail-value">
                            {data_final.strftime('%d/%m/%Y')} + {ajuste} dias = 
                            <strong>{data_final_ajustada.strftime('%d/%m/%Y')}</strong>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Observações do chefe
                p_observacao_chefe = processo.get('observacao_chefe')
                if p_observacao_chefe:
                    st.markdown(f"""
                    <div class="observations-box">
                        <div class="observations-label">📝 Observações do Gabinete:</div>
                        <div>{p_observacao_chefe}</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Botões de ação
                st.markdown('<div class="action-buttons">', unsafe_allow_html=True)
                
                action_cols = st.columns(3)
                
                with action_cols[0]:
                    if p_status_servidor not in ["Concluído", "Finalizado"]:
                        if st.button("📄 Atualizar", key=f"update_serv_{p_id}", type="primary", width='stretch'):
                            st.session_state['processo_para_atualizar_id'] = p_id
                            st.rerun()
                
                with action_cols[1]:
                    button_label = "💬 Não Lido" if tem_nao_lidos else "💬 Comentários"
                    button_type = "primary" if tem_nao_lidos else "secondary"
                    if st.button(button_label, key=f"comments_proc_{p_id}", width='stretch', type=button_type):
                        st.session_state['processo_id'] = p_id
                        st.session_state['came_from'] = 'pages/Meus_Processos.py'
                        st.switch_page('pages/Comentarios_Processo.py')
                
                with action_cols[2]:
                    history_visible = st.session_state.history_visible.get(p_id, False)
                    button_label = "📈 Ocultar" if history_visible else "📈 Histórico"
                    if st.button(button_label, key=f"hist_serv_{p_id}", width='stretch'):
                        st.session_state.history_visible[p_id] = not history_visible
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

                if st.session_state.history_visible.get(p_id, False):
                    ui_utils.display_process_history(processo, None)
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
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