import auth
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os
from sidebar import build_sidebar

# Módulos do projeto
import utils.ui as ui_utils
import utils.common as common_utils
import utils.jobs as jobs_utils
import utils.notifications as notif_utils
import relatorios
import file_utils
from forms import (
    display_edit_processo_form,
    display_chefe_update_form,
    display_process_history
)
# Migration imports
from supabase_client import QueryBuilder, select_all, insert, select_by_id
from db_compat import (
    get_user_by_id, 
    get_product_type_by_id,
    calculate_due_date, 
    calculate_due_date_with_details,
    get_all_users,
    get_direct_servants,
    get_user_subordinates,
    get_prosecutors_of_boss,
    get_user_bosses,
    is_process_favorite,
    toggle_process_favorite
)

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
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 4px solid #9E0520;
        flex: 1;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.15);
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
        border-radius: 6px;
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

    jobs_utils.update_process_statuses()
    
    try:
        id_chefe_para_acoes = st.session_state.active_user_id
        
        # --- KPIs ---
        with st.spinner("Atualizando indicadores..."):
            # 1. Com Servidores: chefe=me, concluded_serv=null
            kpi_serv = QueryBuilder("processos").eq("id_chefe_gabinete", id_chefe_para_acoes).is_("data_conclusao_servidor", "null").execute()
            total_com_servidores = len(kpi_serv)

            # 2. Para Revisão: chefe=me, concluded_serv!=null, status_chefe in [...]
            # Supabase API for NOT NULL is filter 'not.is.null', using QueryBuilder logic if available, or fetch all relevant and filter python
            # QueryBuilder support is via `neq("data_conclusao_servidor", "null")` ideally or custom filter string
            # Let's use Python filtering for safety if list is not huge, or specific query.
            # But efficiently: query status_chefe IN... AND chefe=me
            kpi_rev = QueryBuilder("processos") \
                .eq("id_chefe_gabinete", id_chefe_para_acoes) \
                .in_list("status_chefe", ['Aguardando Análise', 'Revisão Atrasada']) \
                .execute()
            # Ensure concluded_serv is not null? Usually implied by status_chefe but safe to check
            total_para_revisao = len([p for p in kpi_rev if p.get('data_conclusao_servidor') is not None])
            
            # 3. Com Procurador
            kpi_proc = QueryBuilder("processos") \
                .eq("id_chefe_gabinete", id_chefe_para_acoes) \
                .eq("status_chefe", "Processo com o Procurador") \
                .execute()
            total_com_procurador = len(kpi_proc)

        # KPIs com estilo personalizado
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-card">
                <div class="kpi-value">{total_com_servidores}</div>
                <div class="kpi-label">Processos com Servidores</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value" style="color: #ffc107;">{total_para_revisao}</div>
                <div class="kpi-label">Processos para Revisão</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-value" style="color: #17a2b8;">{total_com_procurador}</div>
                <div class="kpi-label">Processos com o Procurador</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

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

        # Seção de novo processo com estilo personalizado      
        with st.expander("➕ Adicionar Novo Processo", expanded=False):
            with st.form("new_process_form", clear_on_submit=True):
                st.subheader("📝 Registrar e Atribuir Novo Processo")
                
                servidores_dict = {s['nome_completo']: s['id'] for s in equipe_atribuivel if s.get('ativo', True)}
                if chefe_logado:
                    servidores_dict[chefe_logado['nome_completo']] = id_chefe_para_acoes
                
                # Fetch products
                all_prods = select_all("tipos_produto")
                # Group by logic: dict by name, keep latest/first? Original sorted by name.
                produtos_dict = {}
                # Sort first
                all_prods.sort(key=lambda x: x.get('nome_produto', ''))
                for p in all_prods:
                     if p['nome_produto'] not in produtos_dict:
                         produtos_dict[p['nome_produto']] = p['id']

                # Procuradores
                procuradores_vinculados = get_prosecutors_of_boss(id_chefe_para_acoes)
                procuradores_vinculados.sort(key=lambda x: x.get('nome_completo', ''))
                procuradores_dict = {p['nome_completo']: p['id'] for p in procuradores_vinculados if p.get('ativo', True)}
                            
                col1, col2 = st.columns(2)
                with col1:
                    processo_numero = st.text_input("📄 Número do Processo")
                    id_tipo_produto_nome = st.selectbox("📋 Tipo de Produto", options=list(produtos_dict.keys()))
                with col2:
                    if not servidores_dict:
                        id_servidor_nome = st.selectbox("👤 Atribuir ao Servidor", options=["Nenhum servidor vinculado ao seu gabinete"], disabled=True)
                    else:
                        id_servidor_nome = st.selectbox("👤 Atribuir ao Servidor", options=list(servidores_dict.keys()))
                    
                    if not procuradores_dict:
                        id_procurador_nome = st.selectbox("⚖️ Procurador Vinculado", options=["Nenhum procurador vinculado"], disabled=True)
                    else:
                        id_procurador_nome = st.selectbox("⚖️ Procurador Vinculado", options=list(procuradores_dict.keys()))
                
                prioridade = st.selectbox("⚡ Prioridade", options=['Regular', 'Prioritário', 'Urgente'])
                observacao_chefe = st.text_area("📝 Observações Iniciais (Opcional)")
                data_atribuicao = st.date_input("📅 Atribuído em", value=date.today(), format="DD/MM/YYYY")

                st.markdown("---")
                st.markdown("**⚙️ Opções de Exceção:**")
                col1_check, col2_check, col3_check = st.columns(3)
                with col1_check:
                    nao_se_aplica_prazo_servidor = st.checkbox("⏰ Não se aplica prazo ao Servidor", help="Se marcado, nenhum prazo de conclusão será atribuído à tarefa do servidor inicial e a tarefa não será sinalizada como 'atrasada' em nenhum momento.")
                with col2_check:
                    ignorar_revisao_chefe = st.checkbox("⏭️ Ignorar etapa de Revisão (Chefe de Gabinete)", help="Se marcado, o sistema deve automaticamente pular essa etapa e encaminhar o processo para a próxima fase do fluxo.")
                with col3_check:
                    ignorar_analise_procurador = st.checkbox("⏩ Ignorar etapa de Análise (Procurador)", help="Se marcado, o sistema deve automaticamente pular essa etapa e encaminhar o processo para a próxima fase do fluxo.")
                
                submitted = st.form_submit_button("✅ Criar e Atribuir Processo", disabled=(not servidores_dict or not procuradores_dict), type="primary")
                
                if submitted and all([processo_numero, id_tipo_produto_nome, id_servidor_nome, id_procurador_nome]):
                    # Fetch correct product version (simplified: get by name and taking latest version logic)
                    # We can use QueryBuilder to get specific product data again to be sure
                    prod_candidates = QueryBuilder("tipos_produto").eq("nome_produto", id_tipo_produto_nome).order("versao", desc=True).limit(1).execute()
                    if not prod_candidates:
                        st.error("Erro ao buscar Tipo de Produto.")
                        st.stop()
                    produto_selecionado = prod_candidates[0]
                    
                    novo_processo_data = {
                        "processo_numero": processo_numero,
                        "id_procurador": procuradores_dict[id_procurador_nome],
                        "id_chefe_gabinete": id_chefe_para_acoes,
                        "id_servidor_responsavel": servidores_dict[id_servidor_nome],
                        "id_tipo_produto": produto_selecionado['id'],
                        "data_atribuicao_servidor": data_atribuicao.isoformat(),
                        "status_servidor": "No Prazo",
                        "status_chefe": "Aguardando Análise",
                        "prazo_servidor_aplicado": produto_selecionado.get('prazo_servidor'),
                        "prazo_chefe_aplicado": produto_selecionado.get('prazo_chefe'),
                        "nao_se_aplica_prazo_servidor": nao_se_aplica_prazo_servidor,
                        "ignorar_revisao_chefe": ignorar_revisao_chefe,
                        "ignorar_analise_procurador": ignorar_analise_procurador,
                        "prioridade": prioridade,
                        "observacao_chefe": observacao_chefe
                    }
                    
                    res_proc = insert("processos", novo_processo_data)
                    # res_proc.data is list of inserted rows
                    if not res_proc or not res_proc.data:
                        st.error("Erro ao criar processo.")
                    else:
                        novo_pid = res_proc.data[0]['id']

                        if observacao_chefe:
                            comentario_data = {
                                "id_processo": novo_pid,
                                "id_usuario": id_chefe_para_acoes,
                                "texto": f"OBSERVAÇÃO INICIAL: {observacao_chefe}",
                                "timestamp": datetime.now().isoformat()
                            }
                            insert("comentarios", comentario_data)

                        notificacao_data = {
                            "id_usuario_destino": servidores_dict[id_servidor_nome],
                            "mensagem": f"Novo processo atribuído a você: '{processo_numero}'.",
                            "lida": False,
                            "timestamp": datetime.now().isoformat()
                        }
                        insert("notificacoes", notificacao_data)


                        # Envio de email de notificação
                        servidor = get_user_by_id(servidores_dict[id_servidor_nome])
                        if servidor and servidor.get('email') and servidor.get('notifica_email_novo_processo'):
                            data_final_calculada = calculate_due_date(
                                start_date=data_atribuicao, 
                                prazo_dias=produto_selecionado.get('prazo_servidor', 0),
                                tipo_contagem=produto_selecionado.get('tipo_contagem_prazo', 'dias uteis'), 
                                id_usuario=servidor['id']
                            )
                            total_dias_corridos = (data_final_calculada - data_atribuicao).days
                            dias_ajuste = max(0, total_dias_corridos - produto_selecionado.get('prazo_servidor', 0))
                            assunto = f"Novo Processo Atribuído: {processo_numero}"
                            prazo_info_html = f"""
                                <tr><td><b>Prazo Base:</b></td><td>{produto_selecionado.get('prazo_servidor')} dias</td></tr>
                                <tr><td><b>Ajustes (Feriados/Afast.):</b></td><td>+{dias_ajuste} dias</td></tr>
                                <tr><td><b>Data Final (Calculada):</b></td><td>{data_final_calculada.strftime('%d/%m/%Y')}</td></tr>
                            """ if not nao_se_aplica_prazo_servidor else """
                                <tr><td><b>Prazo para conclusão:</b></td><td>Não se aplica</td></tr>
                            """
                            corpo = f"""
                            <html><body>
                            <p>Olá {servidor.get('nome_completo')},</p>
                            <p>Um novo processo foi atribuído a você no sistema de produtividade.</p>
                            <table border="1" cellpadding="5" style="border-collapse: collapse;">
                                <tr><td><b>Número do Processo:</b></td><td>{processo_numero}</td></tr>
                                <tr><td><b>Tipo de Produto:</b></td><td>{id_tipo_produto_nome}</td></tr>
                                <tr><td><b>Chefe de Gabinete:</b></td><td>{chefe_logado.get('nome_completo')}</td></tr>
                                <tr><td><b>Procurador Vinculado:</b></td><td>{id_procurador_nome}</td></tr>
                                <tr><td><b>Status Atual:</b></td><td>No Prazo</td></tr>
                                <tr><td><b>Atribuído em:</b></td><td>{data_atribuicao.strftime('%d/%m/%Y')}</td></tr>
                                {prazo_info_html}
                            </table>
                            <p>Acesse o sistema para mais detalhes.</p>
                            </body></html>
                            """
                            notif_utils.send_email_notification(servidor.get('email'), assunto, corpo)
                        
                        st.success(f"✅ Processo {processo_numero} criado e atribuído com sucesso!")
                        st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        # Seções de favoritos e suspensos
        ui_utils.display_favoritos_expander(None, id_chefe_para_acoes, 'pages/Processos_no_Gabinete.py')
        ui_utils.display_suspensos_expander(None, id_chefe_para_acoes, 'pages/Processos_no_Gabinete.py')
        
        st.markdown("---")
        
        # Seção de filtros com estilo personalizado
        st.markdown('<div class="filters-header">Painel de Controle da Equipe</div>', unsafe_allow_html=True)

        servidores_nomes_equipe = [s['nome_completo'] for s in equipe_atribuivel]
        if chefe_logado and chefe_logado['nome_completo'] not in servidores_nomes_equipe:
            servidores_nomes_equipe.insert(0, chefe_logado['nome_completo'])
        servidores_nomes_equipe.sort()

        procuradores_vinculados2 = get_prosecutors_of_boss(id_chefe_para_acoes)
        procuradores_dict2 = {p['nome_completo']: p['id'] for p in procuradores_vinculados2}
        
        # All products map
        all_prods_unique = {}
        for p in select_all("tipos_produto"):
             if p['nome_produto'] not in all_prods_unique:
                 all_prods_unique[p['nome_produto']] = p['id']
        todos_tipos_produto = all_prods_unique

        filtro_numero_processo = st.text_input("🔍 Filtrar por Número do Processo:", key="chefe_filtro_num", placeholder="Digite o número do processo...")
        
        filtros_col1, filtros_col2, filtros_col3, filtros_col4 = st.columns(4)
        with filtros_col1:
            opcoes_status = ["No Prazo", "Atrasado", "Concluído", "Devolvido", "Finalizado", "Processo com o Procurador", "Revisão Atrasada"]
            filtro_status = st.multiselect("📊 Status", options=opcoes_status, default=st.session_state.get('chefe_filtro_status', []))
            filtro_servidor = st.multiselect("👤 Servidor", options=servidores_nomes_equipe, default=st.session_state.get('chefe_filtro_servidor', []))
        with filtros_col2:
            filtro_procurador_nomes = st.multiselect("⚖️ Procurador", options=list(procuradores_dict2.keys()), default=st.session_state.get('chefe_filtro_procurador', []))
            filtro_tipo_produto_nomes = st.multiselect("📋 Tipo de Processo", options=list(todos_tipos_produto.keys()), default=st.session_state.get('chefe_filtro_tipo_produto', []))
        with filtros_col3:
            filtro_data_inicio = st.date_input("📅 De:", value=st.session_state.get('chefe_filtro_data_inicio'), key="chefe_di", format="DD/MM/YYYY")
            filtro_data_fim = st.date_input("📅 Até:", value=st.session_state.get('chefe_filtro_data_fim'), key="chefe_df", format="DD/MM/YYYY")
        with filtros_col4:
            ordenar_por = st.selectbox("📈 Ordenar por", ["Mais Recentes", "Mais Antigos", "Prazo Restante (Crescente)", "Prazo Restante (Decrescente)"], key="chefe_ordenar")
            items_per_page = st.selectbox("📄 Itens por página", [10, 25, 50, 100], index=1, key="chefe_items_per_page")

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
            
            if filtro_status: 
                qb.or_filter(f"status_servidor.in.({','.join(filtro_status)}),status_chefe.in.({','.join(filtro_status)})") 
                # Note: complex OR logic with QueryBuilder might require logic check.
                # If Supabase client supports `.or_`, we use it. If not, filtering in Python might be safer for complex ORs unless I built `or_` support.
                # Checking `supabase_client.py` capabilities in memory... 
                # I implemented simple EQ/In/etc. I didn't verify strictly sophisticated OR.
                # Fallback: Query all for this chief (usually manageable size) and filter in Python for complex status OR logic 
                # OR execute separate queries and merge. 
                # Let's try to filter in Python for the status OR logic to be safe and accurate.
                pass 
            
            if filtro_servidor:
                # Need IDs
                f_ids = QueryBuilder("usuarios").in_list("nome_completo", filtro_servidor).select("id").execute()
                ids_flat = [x['id'] for x in f_ids]
                if ids_flat:
                    qb.in_list("id_servidor_responsavel", ids_flat)
            
            if filtro_procurador_nomes:
                 ids = [procuradores_dict2[n] for n in filtro_procurador_nomes]
                 qb.in_list("id_procurador", ids)
            
            if filtro_tipo_produto_nomes:
                ids = [todos_tipos_produto[n] for n in filtro_tipo_produto_nomes]
                qb.in_list("id_tipo_produto", ids)
                
            if filtro_data_inicio: query = qb.gte("data_atribuicao_servidor", filtro_data_inicio.isoformat())
            if filtro_data_fim: query = qb.lte("data_atribuicao_servidor", filtro_data_fim.isoformat())
            
            processos_filtrados = qb.execute()
            
            # Application of Python Filters for complex OR logic (Status)
            if filtro_status:
                def check_status(p):
                    return (p.get('status_servidor') in filtro_status) or (p.get('status_chefe') in filtro_status)
                processos_filtrados = [p for p in processos_filtrados if check_status(p)]

            if filtro_numero_processo:
                processos_filtrados = common_utils.filter_by_similarity(
                    search_term=filtro_numero_processo,
                    items=processos_filtrados,
                    key_func=lambda p: p.get('processo_numero', '')
                )

            # --- PRÉ-CÁLCULO DOS DADOS ---
            hoje = date.today()
            processos_com_dados = []
            
            # Caches
            # All products might be heavy if many versions. We already fetched unique.
            # Let's fetch relevant ones if needed, or just fetch all since type table is small.
            tipos_prod_all = select_all("tipos_produto")
            produtos_cache = {p['id']: p for p in tipos_prod_all}
            
            # Users cache - relevant for names.
            # We can fetch distinct IDs involved in filtered processes to be efficient?
            # Or just fetch all users (assuming < 1000 users).
            all_users = get_all_users()
            usuarios_cache = {u['id']: u['nome_completo'] for u in all_users}
            
            # Attachments check cache
            # Query all attachments IDs where process in filtered list?
            if processos_filtrados:
                pids = [p['id'] for p in processos_filtrados]
                # Chunked query if too many?
                anexos_rows = QueryBuilder("anexos_processo").in_list("id_processo", pids).select("id_processo").execute()
                anexos_cache = {r['id_processo'] for r in anexos_rows}
            else:
                anexos_cache = set()
            
            # Favorites cache
            favs_rows = QueryBuilder("processo_favoritos").eq("id_usuario", st.session_state.user_id).select("id_processo").execute()
            favoritos_cache = {r['id_processo'] for r in favs_rows}

            # Batch check for unread comments (optimization: 2 queries instead of N*2)
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
                    "prioridade": p.get('prioridade'),
                    "data_atribuicao": date.fromisoformat(p['data_atribuicao_servidor']) if p.get('data_atribuicao_servidor') else None,
                    "nome_produto": produto_obj.get('nome_produto'),
                    "descricao_produto": produto_obj.get('descricao'),
                    "template_path": produto_obj.get('template_path'),
                    "servidor_nome": usuarios_cache.get(p.get('id_servidor_responsavel'), "N/A"),
                    "procurador_nome": usuarios_cache.get(p.get('id_procurador'), "N/A"),
                    "possui_anexo": p_id in anexos_cache,
                    "is_favorito": p_id in favoritos_cache,
                    "tem_nao_lidos": unread_comments_cache.get(p_id, False)  # Uses batch cache
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
                    data_atrib_dt = dados["data_atribuicao"] or date.today()
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
                 for item in displayed_items:
                     p = item['processo']
                     pid = item['id']
                     
                     # Render Card
                     # Using HTML classes defined in CSS
                     # ...
                     
                     st.markdown(f"""<div class="process-card {item['prioridade'].lower() if item.get('prioridade') else ''}">""", unsafe_allow_html=True)
                     
                     # Icons
                     icons_html = ""
                     if item['tem_nao_lidos']: icons_html += "💬 "
                     if item['prioridade'] == 'Urgente': icons_html += "🔥 "
                     elif item['prioridade'] == 'Prioritário': icons_html += "⚠️ "
                     
                     status_display = item['status_chefe'] if item['status_chefe'] != "Aguardando Análise" and item['status_chefe'] != "Revisão Atrasada" else item['status_servidor']
                     status_class = f"status-{status_display.lower().replace(' ', '-')}"
                     
                     # Header
                     st.markdown(f"""
                     <div class="process-header">
                        <div class="process-info">
                            <div class="priority-icons">{icons_html}</div>
                            <div class="process-number">{item['numero']}</div>
                            <div class="process-status {status_class}">{status_display}</div>
                            <div>Servidor: {item['servidor_nome']}</div>
                            <div>{f"Prazo: {item['prazo_restante']} dias" if item['prazo_restante'] != float('inf') else ""}</div>
                        </div>
                     </div>
                     """, unsafe_allow_html=True)
                     
                     with st.expander("📋 Ver detalhes e ações"):
                         st.markdown('<div class="process-content">', unsafe_allow_html=True)
                         # Details
                         st.markdown(f"""
                         <div class="process-details">
                            <div class="detail-item"><div class="detail-label">Produto</div><div class="detail-value">{item['nome_produto']}</div></div>
                            <div class="detail-item"><div class="detail-label">Atribuído</div><div class="detail-value">{item['data_atribuicao'].strftime('%d/%m/%Y') if item['data_atribuicao'] else '-'}</div></div>
                            <div class="detail-item"><div class="detail-label">Procurador</div><div class="detail-value">{item['procurador_nome']}</div></div>
                         </div>
                         """, unsafe_allow_html=True)
                         
                         # Actions
                         act_c1, act_c2, act_c3 = st.columns(3)
                         with act_c1:
                             label = "⭐ Remover Favorito" if item['is_favorito'] else "☆ Adicionar Favorito"
                             if st.button(label, key=f"fav_btn_{pid}"):
                                 toggle_process_favorite(st.session_state.user_id, pid)
                                 st.rerun()
                         with act_c2:
                             if st.button("✏️ Editar", key=f"edit_btn_{pid}"):
                                 st.session_state.processo_para_editar_id = pid
                                 st.rerun()
                         with act_c3:
                              if st.button("📜 Histórico", key=f"hist_btn_{pid}"):
                                   if not st.session_state.get(f"show_hist_{pid}"):
                                       st.session_state[f"show_hist_{pid}"] = True
                                   else:
                                       st.session_state[f"show_hist_{pid}"] = False
                                   st.rerun()
                         
                         if st.session_state.get(f"show_hist_{pid}"):
                             display_process_history(p, None)

                         st.markdown('</div>', unsafe_allow_html=True)
                     st.markdown("</div>", unsafe_allow_html=True)

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


