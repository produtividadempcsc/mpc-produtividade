import streamlit as st
from datetime import timedelta
import ui_utils

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

def render_revisao_process_list(processos_ordenados, unread_comments_cache):
    """Renderiza a lista de cartões de processos na tela de Revisão."""
    for item in processos_ordenados:
        processo = item["processo"]
        p_id = processo['id']
        status_geral = processo.get('status_chefe')
        if processo.get('prazo_status') == 'Suspenso':
            if status_geral == "Revisão Atrasada": status_geral = "Aguardando Análise"
            
        status_icon = ui_utils.get_status_emoji(status_geral)
        priority_icon = get_priority_icon(processo.get('prioridade'))
        tem_nao_lidos = unread_comments_cache.get(p_id, False)
        unread_icon = "💬" if tem_nao_lidos else ""
        anexo_icon = ""
        
        card_class = get_process_card_class(processo, status_geral)
        
        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
        
        if processo.get('prazo_status') == 'Suspenso':
            prazo_info = "⏸️ Prazo Suspenso"
        else:
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

            if item["data_final_ajustada"] is not None:
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
            else:
                st.markdown("""
                <div class="detail-item">
                    <div class="detail-label">Prazo de Revisão</div>
                    <div class="detail-value">⏸️ Prazo Suspenso</div>
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
