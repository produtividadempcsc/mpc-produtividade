import auth
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
from sidebar import build_sidebar

# Módulos do projeto
import utils.ui as ui_utils
import utils.common as common_utils
import relatorios
import file_utils
from supabase_client import select_all, QueryBuilder, insert, delete_by_id
from db_compat import get_user_by_id, calculate_due_date_with_details, toggle_process_favorite, is_process_favorite
from forms import display_analise_form # Importa o formulário de análise

auth.auth_guard()

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
allowed_profiles = ["Chefe de Gabinete"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Apenas usuários com perfil 'Chefe de Gabinete' podem acessar esta página.")
    st.stop()
# ==============================================================================

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

st.session_state.active_page = "Processos para Revisão"
build_sidebar()

# ROTEADOR DE MODAL: Se um processo foi selecionado para análise, exibe o formulário.
if 'processo_em_analise_id' in st.session_state:
    display_analise_form(st.session_state['processo_em_analise_id'])
else:
    # --- CONTEÚDO PRINCIPAL DA PÁGINA ---
    st.markdown("""
    <div class="main-header">
        <h1>👀 Processos para Revisão</h1>
        <p>Processos concluídos pelos servidores e que aguardam sua análise</p>
    </div>
    """, unsafe_allow_html=True)

    
    user_id = st.session_state.user_id

    
    try:
        id_chefe = st.session_state.active_user_id
        
        # --- INTERFACE DE FILTROS ---
        st.markdown('<div class="filters-header">Painel de Controle da Equipe</div>', unsafe_allow_html=True)

        # Popula a lista de servidores para o filtro
        all_servidores_raw = QueryBuilder("usuarios").eq("perfil", "Servidor").order("nome_completo").execute()
        servidores_equipe = all_servidores_raw
        
        servidores_nomes = [s['nome_completo'] for s in servidores_equipe]
        
        filtro_numero_processo_rev = st.text_input("🔍 Filtrar por Número do Processo:", key="rev_filtro_num", placeholder="Digite o número do processo...")

        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            opcoes_status_revisao = ["Aguardando Análise", "Revisão Atrasada"]
            filtro_status_revisao = st.multiselect("📊 Status da Revisão", options=opcoes_status_revisao)
        with f_col2:
            filtro_servidor = st.multiselect("👤 Filtrar por Servidor", options=servidores_nomes, key="rev_servidor")
        with f_col3:
            ordenar_por_revisao = st.selectbox("📈 Ordenar por", ["Mais Recentes", "Mais Antigos", "Prazo de Revisão (Crescente)", "Prazo de Revisão (Decrescente)"], key="rev_ordem")

        # Legenda de ícones
        st.markdown("""
        <div class="icon-legend">
            <div class="legend-title">📖 Legenda de Ícones</div>
            <div class="legend-items">
                <div class="legend-item"><span>💬</span> Comentários não lidos</div>
                <div class="legend-item"><span>📎</span> Possui anexos</div>
                <div class="legend-item"><span>📖</span> Descrição disponível</div>
                <div class="legend-item"><span>📄</span> Modelo disponível</div>
                <div class="legend-item"><span>🔥</span> Urgente</div>
                <div class="legend-item"><span>⚠️</span> Prioritário</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- LÓGICA DE QUERY ---
        with st.spinner("Carregando revisões..."):
            qb = QueryBuilder("processos").eq("id_chefe_gabinete", id_chefe).eq("status_servidor", "Concluído")

            # Filtro server-side por número do processo (busca em TODO o banco)
            if filtro_numero_processo_rev:
                search_clean = filtro_numero_processo_rev.strip()
                qb.ilike("processo_numero", f"%{search_clean}%")
            
            if filtro_status_revisao:
                 qb.in_list("status_chefe", filtro_status_revisao)
            else:
                 qb.in_list("status_chefe", ["Aguardando Análise", "Revisão Atrasada"])

            if filtro_servidor:
                # Get IDs for names
                ids_servidores_filtrados = [s['id'] for s in servidores_equipe if s['nome_completo'] in filtro_servidor]
                if ids_servidores_filtrados:
                     qb.in_list("id_servidor_responsavel", ids_servidores_filtrados)
            
            processos_para_analise = qb.execute()

        # Refinamento local: reordena por similaridade (fuzzy matching)
        if filtro_numero_processo_rev and processos_para_analise:
            processos_para_analise = common_utils.filter_by_similarity(
                search_term=filtro_numero_processo_rev,
                items=processos_para_analise,
                key_func=lambda p: p.get('processo_numero', '')
            )
        
        # --- REESTRUTURAÇÃO: Pré-cálculo dos dados para evitar recálculos no loop ---
        hoje = date.today()
        processos_com_dados = []
        # Cache para objetos já buscados
        all_types = select_all("tipos_produto")
        produtos_cache = {p['id']: p for p in all_types}
        
        all_users_cache = select_all("usuarios", "id, nome_completo")
        usuarios_cache = {u['id']: u['nome_completo'] for u in all_users_cache}
        
        # Anexos cache - optimizing to fetch only relevant? Or select distinct id_processo.
        # select id_processo from anexos_processo ...
        anexos_rows = select_all("anexos_processo", "id_processo")
        anexos_cache = {r['id_processo'] for r in anexos_rows}

        for p in processos_para_analise:
            produto_obj = produtos_cache.get(p.get('id_tipo_produto'))
            dt_conclusao_str = p.get('data_conclusao_servidor')
            
            if not produto_obj or not dt_conclusao_str: continue
            
            dt_conclusao_servidor = date.fromisoformat(dt_conclusao_str)
            
            data_final_ajustada, ajuste = calculate_due_date_with_details(
                dt_conclusao_servidor, 
                p.get('prazo_chefe_aplicado', 0), 
                produto_obj.get('tipo_contagem_prazo', 'dias uteis'), 
                p.get('id_chefe_gabinete'), 
                dias_suspensos=p.get('prazo_total_dias_suspenso', 0)
            )
            dias_restantes = (data_final_ajustada - hoje).days
            
            processos_com_dados.append({
                "processo": p,
                "dias_restantes": dias_restantes,
                "data_final_ajustada": data_final_ajustada,
                "ajuste": ajuste,
                "servidor_nome": usuarios_cache.get(p.get('id_servidor_responsavel'), "N/A"),
                "produto_nome": produto_obj.get('nome_produto'),
                "procurador_nome": usuarios_cache.get(p.get('id_procurador'), "N/A"),
                "dt_ref": dt_conclusao_servidor
            })

        # --- Lógica de Ordenação ---
        if ordenar_por_revisao == "Prazo de Revisão (Crescente)": 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["dias_restantes"])
        elif ordenar_por_revisao == "Prazo de Revisão (Decrescente)": 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["dias_restantes"], reverse=True)
        elif ordenar_por_revisao == "Mais Antigos": 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["dt_ref"])
        else: 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["dt_ref"], reverse=True)
        
        st.markdown("---")
        
        # --- EXIBIÇÃO DOS RESULTADOS ---
        if not processos_ordenados:
            st.markdown("""
            <div style="text-align: center; padding: 50px; background: white; border-radius: 12px; box-shadow: 0 3px 15px rgba(0,0,0,0.1);">
                <h3 style="color: var(--primary-color);">🔍 Nenhum processo encontrado</h3>
                <p>Tente ajustar os filtros para encontrar os processos desejados.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info(f"Mostrando {len(processos_ordenados)} processos aguardando revisão.")

            # Otimização: Pré-busca de dados de favoritos e anexos
            # Fetch favs for current user


            # Fetch attachment info for processes
            processo_ids_ordenados = [item["processo"]['id'] for item in processos_ordenados]
            anexos_rows = QueryBuilder("anexos_processos").in_list("id_processo", processo_ids_ordenados).select("id_processo").execute()
            anexos_cache = {r['id_processo'] for r in anexos_rows}

            # Batch check for unread comments (optimization: 2 queries instead of N*2)
            unread_comments_cache = common_utils.batch_has_unread_comments(processo_ids_ordenados, st.session_state.user_id)

            if 'history_visible_rev' not in st.session_state:
                st.session_state.history_visible_rev = {}

            def get_priority_icon(priority):
                if priority == 'Urgente': return '🔥'
                elif priority == 'Prioritário': return '⚠️'
                return ''

            def get_process_card_class(processo, status_geral):
                classes = ["process-card"]
                prioridade = processo.get('prioridade')
                if prioridade == 'Urgente':
                    classes.append("urgente")
                elif prioridade == 'Prioritário':
                    classes.append("prioritario")
                if status_geral == 'Revisão Atrasada':
                    classes.append("atrasado")
                return " ".join(classes)

            for item in processos_ordenados:
                processo = item["processo"]
                p_id = processo['id']
                status_geral = processo.get('status_chefe')
                status_icon = ui_utils.get_status_emoji(status_geral)
                priority_icon = get_priority_icon(processo.get('prioridade'))
                tem_nao_lidos = unread_comments_cache.get(p_id, False)  # Uses batch cache
                unread_icon = "💬" if tem_nao_lidos else ""
                tem_anexo = p_id in anexos_cache
                anexo_icon = "📎" if tem_anexo else ""
                
                # Card do processo com estilo personalizado
                card_class = get_process_card_class(processo, status_geral)
                
                st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
                
                # Header do processo
                prazo_info = f"📅 {item['data_final_ajustada'].strftime('%d/%m/%Y')}"
                servidor_info = f"👤 {item['servidor_nome']}"
                
                st.markdown(f"""
                <div class="process-header">
                    <div class="process-info">
                        <div class="priority-icons">{unread_icon} {priority_icon} {status_icon} {anexo_icon}</div>
                        <div class="process-number">{processo.get('processo_numero')}</div>
                        <div class="process-status status-{status_geral.lower().replace(' ', '-')}">{status_geral}</div>
                        <div>{servidor_info}</div>
                        <div>{prazo_info}</div>
                        <div><span style="font-weight: 600;">Prioridade:</span> {processo.get('prioridade')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.expander("📋 Ver detalhes e ações", expanded=False):
                    st.markdown('<div class="process-content">', unsafe_allow_html=True)
                    
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
                            <div class="detail-label">Concluído pelo Servidor</div>
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
                        item['dt_ref'].strftime('%d/%m/%Y'),
                        ui_utils.get_status_color(status_geral),
                        status_geral
                    ), unsafe_allow_html=True)

                    data_final_revisao = item["data_final_ajustada"] - timedelta(days=item["ajuste"])
                    st.markdown(f"""
                    <div class="detail-item">
                        <div class="detail-label">Prazo de Revisão</div>
                        <div class="detail-value">
                            {data_final_revisao.strftime('%d/%m/%Y')} + {item['ajuste']} dias = 
                            <strong>{item['data_final_ajustada'].strftime('%d/%m/%Y')}</strong>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if processo.get('observacao_chefe'):
                        st.markdown(f"""
                        <div class="observations-box">
                            <div class="observations-label">📝 Observações do Gabinete:</div>
                            <div>{processo.get('observacao_chefe')}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown('<div class="action-buttons">', unsafe_allow_html=True)
                    
                    action_cols = st.columns(3)
                    
                    with action_cols[0]:
                        if st.button("🔍 Analisar", key=f"analisar_rev_{p_id}", width='stretch'):
                            st.session_state['processo_em_analise_id'] = p_id
                            st.rerun()

                    with action_cols[1]:
                        button_label = "💬 Comentários" + (" (Não Lido)" if tem_nao_lidos else "")
                        button_type = "primary" if tem_nao_lidos else "secondary"
                        if st.button(button_label, key=f"comments_proc_{p_id}", width='stretch', type=button_type):
                            st.session_state['processo_id'] = p_id
                            st.session_state['came_from'] = 'pages/Processos_para_Revisao.py'
                            st.switch_page('Pages/Comentarios_Processo.py')
                    
                    with action_cols[2]:
                        if st.button("📜 Histórico", key=f"hist_rev_{p_id}", width='stretch'):
                            st.session_state.history_visible_rev[p_id] = not st.session_state.history_visible_rev.get(p_id, False)
                            st.rerun()

                    st.markdown('</div>', unsafe_allow_html=True)

                    if st.session_state.history_visible_rev.get(p_id, False):
                        st.markdown("---")
                        ui_utils.display_process_history(processo, None)
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)


            
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar a página: {e}")