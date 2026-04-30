import streamlit as st
from datetime import datetime, timedelta
import ui_utils
import utils.common as common_utils

def get_priority_icon(priority):
    if priority == 'Urgente':
        return '🔥'
    elif priority == 'Prioritário': 
        return '⚠️'
    return ''

def render_mpc_process_list(paginated_items):
    """Renderiza a lista de cartões de processos na tela MPC."""
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
        if processo.get('prazo_status') == 'Suspenso':
            if status_geral == "Atrasado": status_geral = "No Prazo"
            if status_geral == "Revisão Atrasada": status_geral = "Aguardando Análise"
            
        status_icon = ui_utils.get_status_emoji(status_geral)
        priority_icon = get_priority_icon(prioridade)
        tem_nao_lidos = common_utils.has_unread_comments(pid, st.session_state.user_id)
        unread_icon = "💬" if tem_nao_lidos else ""
        anexo_icon = ""
        
        classes = ["process-card"]
        if prioridade == 'Urgente': classes.append("urgente")
        elif prioridade == 'Prioritário': classes.append("prioritario")
        if status_geral == 'Atrasado': classes.append("atrasado")
        card_class = " ".join(classes)
        
        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
        
        # Header do processo
        if processo.get('prazo_status') == 'Suspenso':
            prazo_info = "⏸️ Prazo Suspenso"
            servidor_info = f"👤 {item['servidor_nome']}"
        elif conclusao_dt:
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

        with st.expander("📋 Ver detalhes e ações", expanded=False):
            st.markdown('<div class="process-content">', unsafe_allow_html=True)
            
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

            obs_chefe = processo.get('observacao_chefe')
            if obs_chefe:
                st.markdown(f"""
                <div class="observations-box">
                    <div class="observations-label">📝 Observações do Gabinete:</div>
                    <div>{obs_chefe}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('<div class="action-buttons">', unsafe_allow_html=True)
            
            action_cols = st.columns(3)
            
            with action_cols[0]:
                if st.button("✏️ Editar Processo", key=f"edit_detalhe_{processo.get('id')}", use_container_width=True):
                    st.session_state['processo_para_editar_id'] = processo.get('id')
                    st.rerun()
            
            with action_cols[1]:
                button_label = "💬 Comentário Não Lido" if tem_nao_lidos else "💬 Comentários"
                button_type = "primary" if tem_nao_lidos else "secondary"
                if st.button(button_label, key=f"comments_proc_{processo.get('id')}", use_container_width=True, type=button_type):
                    st.session_state['processo_id'] = processo.get('id')
                    st.session_state['came_from'] = 'pages/Processos_MPC.py'
                    st.switch_page('pages/Comentarios_Processo.py')
            
            with action_cols[2]:
                if "show_history" not in st.session_state:
                    st.session_state.show_history = {}
                if st.button("📜 Histórico", key=f"hist_chefe_{processo.get('id')}", use_container_width=True):
                    st.session_state.show_history[processo.get('id')] = not st.session_state.show_history.get(processo.get('id'), False)
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

            if st.session_state.get("show_history", {}).get(processo.get('id'), False):
                st.markdown("---")
                ui_utils.display_process_history(processo)

            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
