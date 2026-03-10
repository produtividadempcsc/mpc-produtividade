import auth
import streamlit as st
from datetime import datetime, date
from sidebar import build_sidebar

# Módulos do projeto
import utils.ui as ui_utils
import utils.common as common_utils
from supabase_client import select_all, QueryBuilder, update_by_id

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

st.session_state.active_page = "Processos com o Procurador"
build_sidebar()

# Header Principal
st.markdown("""
<div class="main-header">
    <h1>➡️ Processos com o Procurador</h1>
    <p>Processos aprovados por você e que estão em análise pelo Procurador de Contas</p>
</div>
""", unsafe_allow_html=True)

db = None # Removed db session usage
user_id = st.session_state.user_id

def get_priority_icon(priority):
    if priority == 'Urgente': return '🔥'
    elif priority == 'Prioritário': return '⚠️'
    return ''

def get_process_card_class(processo):
    classes = ["process-card"]
    prioridade = processo.get('prioridade')
    if prioridade == 'Urgente':
        classes.append("urgente")
    elif prioridade == 'Prioritário':
        classes.append("prioritario")
    return " ".join(classes)

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

        # Filtro server-side por número do processo (busca em TODO o banco)
        if filtro_numero_processo_proc:
            search_clean = filtro_numero_processo_proc.strip()
            qb.ilike("processo_numero", f"%{search_clean}%")

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
        
        anexos_rows = select_all("anexos_processo", "id_processo")
        anexos_cache = {r['id_processo'] for r in anexos_rows}
        
        all_types = select_all("tipos_produto")
        produtos_cache = {p['id']: p for p in all_types}
        
        all_users = select_all("usuarios", "id, nome_completo")
        usuarios_cache = {u['id']: u['nome_completo'] for u in all_users}

        # Batch check for unread comments (optimization: 2 queries instead of N*2)
        unread_comments_cache = common_utils.batch_has_unread_comments(processo_ids_pagina, st.session_state.user_id)

        for p in processos_com_procurador:
            card_class = get_process_card_class(p)
            status_geral = "Processo com o Procurador"
            status_icon = ui_utils.get_status_emoji(status_geral)
            priority_icon = get_priority_icon(p.get('prioridade'))
            tem_nao_lidos = unread_comments_cache.get(p['id'], False)  # Uses batch cache
            unread_icon = "💬" if tem_nao_lidos else ""
            tem_anexo = p['id'] in anexos_cache
            anexo_icon = "📎" if tem_anexo else ""
            
            st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
            
            # Header do processo
            servidor_nome = usuarios_cache.get(p.get('id_servidor_responsavel'), "N/A")
            dt_conc = p.get('data_conclusao_chefe')
            data_envio = date.fromisoformat(dt_conc).strftime('%d/%m/%Y') if dt_conc else "N/A"

            st.markdown(f"""
            <div class="process-header">
                <div class="process-info">
                    <div class="priority-icons">{unread_icon} {priority_icon} {status_icon} {anexo_icon}</div>
                    <div class="process-number">{p.get('processo_numero')}</div>
                    <div class="process-status status-concluido">{status_geral}</div>
                    <div>👤 {servidor_nome}</div>
                    <div>📅 Enviado em: {data_envio}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Conteúdo do processo (expander)
            with st.expander("📋 Ver detalhes e ações"):
                st.markdown('<div class="process-content">', unsafe_allow_html=True)
                
                produto_obj = produtos_cache.get(p.get('id_tipo_produto'))
                procurador_nome = usuarios_cache.get(p.get('id_procurador'), "N/A")

                st.markdown("""
                <div class="process-details">
                    <div class="detail-item">
                        <div class="detail-label">Servidor Responsável</div>
                        <div class="detail-value">{}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Tipo de Produto</div>
                        <div class="detail-value">{}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Procurador</div>
                        <div class="detail-value">{}</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-label">Enviado em</div>
                        <div class="detail-value">{}</div>
                    </div>
                </div>
                """.format(
                    servidor_nome,
                    produto_obj['nome_produto'] if produto_obj else 'N/A',
                    procurador_nome,
                    data_envio
                ), unsafe_allow_html=True)
                
                if p.get('observacao_chefe'):
                    st.markdown(f"""
                    <div class="observations-box">
                        <div class="observations-label">📝 Observações do Gabinete:</div>
                        <div>{p.get('observacao_chefe')}</div>
                    </div>
                    """, unsafe_allow_html=True)

                # Botões de ação
                st.markdown('<div class="action-buttons">', unsafe_allow_html=True)
                
                b_col1, b_col2, b_col3, b_col4 = st.columns(4)
                
                with b_col1:
                    if st.button("✅ Marcar como Finalizado", key=f"procurador_concluiu_{p['id']}", width='stretch', type="primary"):
                        update_by_id("processos", p['id'], {
                            "status_chefe": "Finalizado",  
                            "status_servidor": "Finalizado",
                            "data_finalizacao": datetime.now().isoformat()
                        })
                        st.success(f"✅ Processo {p.get('processo_numero')} finalizado!")
                        st.rerun()
                
                with b_col2:
                    if st.button("↩️ Devolver para o Gabinete", key=f"procurador_devolve_{p['id']}", width='stretch'):
                        update_by_id("processos", p['id'], {"status_chefe": "Aguardando Análise", "status_servidor": "Concluído"})
                        st.warning(f"↩️ Processo {p.get('processo_numero')} devolvido para revisão!")
                        st.rerun()
                
                with b_col3:
                    button_label = "💬 Comentário Não Lido" if tem_nao_lidos else "💬 Comentários"
                    button_type = "primary" if tem_nao_lidos else "secondary"
                    if st.button(button_label, key=f"comments_proc_{p['id']}", width='stretch', type=button_type):
                        st.session_state['processo_id'] = p['id']
                        st.session_state['came_from'] = 'pages/Processos_com_Procurador.py'
                        st.switch_page('pages/Comentarios_Processo.py')
                
                with b_col4:
                    if st.button("📜 Histórico", key=f"hist_proc_{p['id']}", width='stretch'):
                        st.session_state.history_visible_procurador[p['id']] = not st.session_state.history_visible_procurador.get(p['id'], False)
                        st.rerun()


                st.markdown('</div>', unsafe_allow_html=True)

                if st.session_state.history_visible_procurador.get(p['id'], False):
                    st.markdown("---")
                    ui_utils.display_process_history(p, None)

                st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)



except Exception as e:
    st.error(f"Ocorreu um erro ao carregar a página: {e}")
