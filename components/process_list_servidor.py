import streamlit as st
from datetime import date, timedelta
from utils.timezone import today_brazil
import ui_utils
from services.prazo_service import calculate_due_date, calculate_due_date_with_details
from repositories.devolucao_repository import get_ultima_devolucao

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

def render_servidor_process_list(paginated_items, all_product_types_map, users_map, unread_comments_cache):
    """Renderiza a lista de cartões de processos na tela do Servidor."""
    for processo, dias_restantes in paginated_items:
        p_id = processo.get('id')
        p_status_servidor = processo.get('status_servidor', '')
        p_prioridade = processo.get('prioridade', 'Regular')
        p_processo_numero = processo.get('processo_numero', '')
        p_nao_se_aplica_prazo = processo.get('nao_se_aplica_prazo_servidor', False)
        p_status_chefe = processo.get('status_chefe', '')
        
        status_icon = ui_utils.get_status_emoji(p_status_servidor)
        priority_icon = get_priority_icon(p_prioridade)
        tem_nao_lidos = unread_comments_cache.get(p_id, False)
        unread_icon = "💬" if tem_nao_lidos else ""
        
        card_class = get_process_card_class(processo, p_status_servidor)
        
        st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
        
        data_conclusao_str = processo.get('data_conclusao_servidor')
        if data_conclusao_str and isinstance(data_conclusao_str, str):
            try:
                data_conclusao = date.fromisoformat(data_conclusao_str[:10])
                data_entrega = data_conclusao.strftime('%d/%m/%Y')
            except Exception as e:
                print(f"⚠️ Erro silencioso em Meus_Processos.py (parse data_conclusao_servidor): {e}")
                data_entrega = "Data não informada"
        elif data_conclusao_str:
            data_entrega = data_conclusao_str.strftime('%d/%m/%Y')
        else:
            data_entrega = "Data não informada"
        
        if p_status_servidor == "Concluído":
            info_chefe = "Pendente de revisão pelo chefe de gabinete" if p_status_chefe == "Aguardando Análise" else "Processo com o procurador"
            prazo_info = f"Entregue em: {data_entrega}"
            servidor_info = f"Status: {info_chefe}"
            devolucao_info = None  # Não precisa buscar devolução para processos concluídos
        elif p_status_servidor == "Finalizado":
            prazo_info = f"Entregue em: {data_entrega}"
            servidor_info = ""
            devolucao_info = None
        else:
            if p_nao_se_aplica_prazo:
                prazo_info = "⏰ Não se aplica"
                servidor_info = ""
                devolucao_info = None
            elif processo.get('prazo_status') == 'Suspenso':
                prazo_info = "⏸️ Prazo Suspenso"
                servidor_info = ""
                devolucao_info = None
            else:
                produto_obj = all_product_types_map.get(processo.get('id_tipo_produto'))
                data_atrib_str = processo.get('data_atribuicao_servidor')
                if data_atrib_str and isinstance(data_atrib_str, str):
                    data_atrib = date.fromisoformat(data_atrib_str)
                else:
                    data_atrib = data_atrib_str
                
                # Verificar se há devolução ativa para usar como fonte primária
                devolucao_info = None
                prazo_efetivo = processo.get('prazo_servidor_aplicado')
                data_inicio_efetiva = data_atrib
                
                if processo.get('prazo_customizado'):
                    devolucao_info = get_ultima_devolucao(p_id)
                    if devolucao_info:
                        prazo_efetivo = devolucao_info.get('prazo_dias', prazo_efetivo)
                        dt_dev_str = devolucao_info.get('data_devolucao')
                        if dt_dev_str:
                            if isinstance(dt_dev_str, str):
                                data_inicio_efetiva = date.fromisoformat(dt_dev_str)
                            else:
                                data_inicio_efetiva = dt_dev_str
                
                data_final_calculada = calculate_due_date(
                    data_inicio_efetiva, 
                    prazo_efetivo, 
                    produto_obj.get('tipo_contagem_prazo') if produto_obj else 'dias uteis', 
                    processo.get('id_servidor_responsavel'), 
                    dias_suspensos=processo.get('prazo_total_dias_suspenso', 0)
                )
                hoje = today_brazil()
                dias_rest_calc = (data_final_calculada - hoje).days
                prazo_restante_str = f"{dias_rest_calc} dias"
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

        with st.expander("📋 Ver detalhes e ações", expanded=False):
            st.markdown('<div class="process-content">', unsafe_allow_html=True)
            
            produto_obj = all_product_types_map.get(processo.get('id_tipo_produto'))
            chefe_user = users_map.get(processo.get('id_chefe_gabinete'), {})
            chefe_nome = chefe_user.get('nome_completo', 'N/A')
            procurador_user = users_map.get(processo.get('id_procurador'), {})
            procurador_nome = procurador_user.get('nome_completo', 'N/A')
            
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

            if not p_nao_se_aplica_prazo and data_atrib:
                # Usar dados da devolução ativa como fonte primária, se existir
                prazo_efetivo = processo.get('prazo_servidor_aplicado')
                data_inicio_efetiva = data_atrib
                
                if processo.get('prazo_customizado') and devolucao_info is None:
                    devolucao_info = get_ultima_devolucao(p_id)
                
                if devolucao_info:
                    prazo_efetivo = devolucao_info.get('prazo_dias', prazo_efetivo)
                    dt_dev_str = devolucao_info.get('data_devolucao')
                    if dt_dev_str:
                        if isinstance(dt_dev_str, str):
                            data_inicio_efetiva = date.fromisoformat(dt_dev_str)
                        else:
                            data_inicio_efetiva = dt_dev_str
                
                data_final_ajustada, ajuste = calculate_due_date_with_details(
                    start_date=data_inicio_efetiva,
                    prazo_dias=prazo_efetivo,
                    tipo_contagem=produto_obj.get('tipo_contagem_prazo') if produto_obj else 'dias uteis',
                    id_usuario=processo.get('id_servidor_responsavel'),
                    dias_suspensos=processo.get('prazo_total_dias_suspenso', 0)
                )
                
                # Mostrar info de devolução se for prazo customizado
                if devolucao_info:
                    dt_dev = devolucao_info.get('data_devolucao', '')
                    if isinstance(dt_dev, str) and dt_dev:
                        dt_dev_fmt = date.fromisoformat(dt_dev).strftime('%d/%m/%Y')
                    elif hasattr(dt_dev, 'strftime'):
                        dt_dev_fmt = dt_dev.strftime('%d/%m/%Y')
                    else:
                        dt_dev_fmt = 'N/A'
                    prazo_dev = devolucao_info.get('prazo_dias', '')
                    st.markdown(f"""
                    <div class="observations-box" style="border-left-color: #FF9800;">
                        <div class="observations-label">↩️ Prazo de Devolução (prazo vigente):</div>
                        <div>Devolvido em <strong>{dt_dev_fmt}</strong> com prazo de <strong>{prazo_dev} dias</strong></div>
                        <div>Vencimento: <strong>{data_final_ajustada.strftime('%d/%m/%Y')}</strong></div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
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

            p_observacao_chefe = processo.get('observacao_chefe')
            if p_observacao_chefe:
                st.markdown(f"""
                <div class="observations-box">
                    <div class="observations-label">📝 Observações do Gabinete:</div>
                    <div>{p_observacao_chefe}</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown('<div class="action-buttons">', unsafe_allow_html=True)
            
            action_cols = st.columns(3)
            
            with action_cols[0]:
                if p_status_servidor not in ["Concluído", "Finalizado"]:
                    if st.button("📄 Atualizar", key=f"update_serv_{p_id}", type="primary", use_container_width=True):
                        st.session_state['processo_para_atualizar_id'] = p_id
                        st.rerun()
            
            with action_cols[1]:
                button_label = "💬 Não Lido" if tem_nao_lidos else "💬 Comentários"
                button_type = "primary" if tem_nao_lidos else "secondary"
                if st.button(button_label, key=f"comments_proc_{p_id}", use_container_width=True, type=button_type):
                    st.session_state['processo_id'] = p_id
                    st.session_state['came_from'] = 'pages/Meus_Processos.py'
                    st.switch_page('pages/Comentarios_Processo.py')
            
            with action_cols[2]:
                history_visible = st.session_state.history_visible.get(p_id, False)
                button_label = "📈 Ocultar" if history_visible else "📈 Histórico"
                if st.button(button_label, key=f"hist_serv_{p_id}", use_container_width=True):
                    st.session_state.history_visible[p_id] = not history_visible
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

            if st.session_state.history_visible.get(p_id, False):
                ui_utils.display_process_history(processo, None)
            
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
