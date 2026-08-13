import streamlit as st
from datetime import datetime, date
from utils.timezone import today_brazil, now_brazil
import ui_utils
from supabase_client import update_by_id
import db_compat
from repositories.devolucao_procurador_chefe_repository import registrar_devolucao_procurador_chefe

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

def render_procurador_process_list(processos_com_procurador, usuarios_cache, produtos_cache, unread_comments_cache):
    """Renderiza a lista de cartões de processos na tela do Procurador."""
    
    for p in processos_com_procurador:
        card_class = get_process_card_class(p)
        status_geral = "Processo com o Procurador"
        status_icon = ui_utils.get_status_emoji(status_geral)
        priority_icon = get_priority_icon(p.get('prioridade'))
        tem_nao_lidos = unread_comments_cache.get(p['id'], False)
        unread_icon = "💬" if tem_nao_lidos else ""
        anexo_icon = ""
        
        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
        
        # Header do processo
        servidor_nome = usuarios_cache.get(p.get('id_servidor_responsavel'), "N/A")
        dt_conc = p.get('data_conclusao_chefe')
        data_envio = date.fromisoformat(dt_conc[:10]).strftime('%d/%m/%Y') if dt_conc else "N/A"

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
                if st.button("✅ Finalizar", key=f"procurador_concluiu_{p['id']}", use_container_width=True, type="primary"):
                    update_by_id("processos", p['id'], {
                        "status_chefe": "Finalizado",  
                        "status_servidor": "Finalizado",
                        "data_finalizacao": now_brazil().isoformat()
                    })
                    import ui_utils
                    ui_utils.set_success_feedback(f"Processo {p.get('processo_numero')} finalizado!", "success")
                    st.rerun()
            
            with b_col2:
                if st.button("↩️ Devolver Chefe de Gabinete", key=f"procurador_devolve_{p['id']}", use_container_width=True):
                    update_by_id("processos", p['id'], {
                        "status_chefe": "Aguardando Análise", 
                        "status_servidor": "Concluído",
                        "data_atribuicao_chefe": now_brazil().isoformat()
                    })
                    
                    registrar_devolucao_procurador_chefe(
                        id_processo=p['id'],
                        data_devolucao=today_brazil(),
                        prazo_dias=p.get('prazo_chefe_aplicado', 0),
                        observacao=f"Devolvido pelo Procurador.",
                        id_usuario_devolucao=st.session_state.active_user_id
                    )
                    
                    db_compat.add_process_history(
                        process_id=p['id'],
                        action="Devolvido para Revisão pelo Procurador",
                        user_id=st.session_state.active_user_id,
                        details="O processo foi devolvido pelo Procurador para análise do Chefe de Gabinete."
                    )
                    import ui_utils
                    ui_utils.set_success_feedback(f"Devolvido para revisão!", "warning", "↩️")
                    st.rerun()
            
            with b_col3:
                button_label = "💬 Comentário Não Lido" if tem_nao_lidos else "💬 Comentários"
                button_type = "primary" if tem_nao_lidos else "secondary"
                if st.button(button_label, key=f"comments_proc_{p['id']}", use_container_width=True, type=button_type):
                    st.session_state['processo_id'] = p['id']
                    st.session_state['came_from'] = 'pages/Processos_com_Procurador.py'
                    st.switch_page('pages/Comentarios_Processo.py')
            
            with b_col4:
                if st.button("📜 Histórico", key=f"hist_proc_{p['id']}", use_container_width=True):
                    st.session_state.history_visible_procurador[p['id']] = not st.session_state.history_visible_procurador.get(p['id'], False)
                    st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)

            if st.session_state.history_visible_procurador.get(p['id'], False):
                st.markdown("---")
                ui_utils.display_process_history(p, None)

            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
