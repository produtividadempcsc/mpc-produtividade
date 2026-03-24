import streamlit as st
from datetime import date
from utils.timezone import today_brazil
from repositories.afastamento_repository import get_leaves_overlapping
from forms import display_process_history

def render_process_list(displayed_items, hoje):
    """Renderiza a lista de cartões de processos na tela."""
    for item in displayed_items:
        p = item['processo']
        pid = item['id']
        
        # Icons
        icons_html = ""
        if item['tem_nao_lidos']: icons_html += "💬 "
        if item['prioridade'] == 'Urgente': icons_html += "🔥 "
        elif item['prioridade'] == 'Prioritário': icons_html += "⚠️ "
        
        status_display = item['status_chefe'] if item['status_chefe'] != "Aguardando Análise" and item['status_chefe'] != "Revisão Atrasada" else item['status_servidor']
        if not status_display:
            status_display = item.get('status_servidor') or 'N/A'
        status_class = f"status-{status_display.lower().replace(' ', '-')}"
        
        # MPC Status Badge
        mpc_badge = ""
        if item['status_mpc'] and item['status_mpc'] != "Não se aplica":
            mpc_status = item['status_mpc']
            # Calculate remaining days for MPC
            if item.get('data_entrada_mpc') and item.get('prazo_mpc_dias'):
                from datetime import timedelta
                data_limite_mpc = item['data_entrada_mpc'] + timedelta(days=item['prazo_mpc_dias'])
                dias_restantes_mpc = (data_limite_mpc - hoje).days
                if mpc_status == "No prazo MPC":
                    mpc_badge = f'<span class="process-status" style="background-color:#28A745;color:white;margin-left:5px;">{mpc_status} ({dias_restantes_mpc} dias)</span>'
                elif mpc_status == "Atrasado MPC":
                    mpc_badge = f'<span class="process-status" style="background-color:#DC3545;color:white;margin-left:5px;">{mpc_status} ({abs(dias_restantes_mpc)} dias)</span>'
                else:
                    mpc_badge = f'<span class="process-status" style="background-color:#6c757d;color:white;margin-left:5px;opacity:0.7;">{mpc_status}</span>'
        
        # Header
        prazo_text = ""
        if item['prazo_restante'] != float('inf') and item.get('data_final'):
            prazo_text = f"Prazo: {item['prazo_restante']} dias (vence {item['data_final'].strftime('%d/%m/%Y')})"
        
        servidor_badge = f'<span style="font-size:0.85em;color:#555;padding:4px 10px;background:#f0f0f0;border-radius:6px;">👤 {item["servidor_nome"]}</span>'
        prazo_badge = ""
        if prazo_text:
            prazo_badge = f'<span style="font-size:0.85em;color:#555;padding:4px 10px;background:#f0f0f0;border-radius:6px;">📅 {prazo_text}</span>'
        
        card_class = item['prioridade'].lower() if item.get('prioridade') else ''
        
        st.markdown(f"""<div class="process-card {card_class}"><div class="process-header"><span class="process-info"><span class="priority-icons">{icons_html}</span><span class="process-number">{item['numero']}</span><span class="process-status {status_class}">{status_display}</span>{mpc_badge}</span><span style="display:flex;gap:10px;flex-wrap:wrap;padding:8px 20px 15px 20px;">{servidor_badge}{prazo_badge}</span></div>""", unsafe_allow_html=True)
        
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
            
            # Mostrar informações de afastamentos que afetam o período do processo
            if item.get('data_atribuicao') and item.get('id_servidor'):
                # Usar data_final ou data de hoje como referência
                data_fim_busca = item.get('data_final') or today_brazil()
                afastamentos = get_leaves_overlapping(
                    item['id_servidor'],
                    item['data_atribuicao'],
                    data_fim_busca
                )
                
                # Se há dias suspensos registrados ou afastamentos encontrados
                dias_susp = item.get('dias_suspensos', 0) or 0
                if afastamentos or dias_susp > 0:
                    # Calcular total de dias de afastamento no período
                    total_dias_af = 0
                    for af in afastamentos:
                        af_ini = af.get('data_inicio')
                        af_fim = af.get('data_fim')
                        if af_ini and af_fim:
                            if isinstance(af_ini, str): af_ini = date.fromisoformat(af_ini[:10])
                            if isinstance(af_fim, str): af_fim = date.fromisoformat(af_fim[:10])
                            # Calcular sobreposição
                            overlap_start = max(item['data_atribuicao'], af_ini)
                            overlap_end = min(data_fim_busca, af_fim)
                            if overlap_start <= overlap_end:
                                total_dias_af += (overlap_end - overlap_start).days + 1
                    
                    # Box de aviso unificado
                    dias_total = max(dias_susp, total_dias_af)
                    if dias_total > 0:
                        # Construir lista de afastamentos dentro do mesmo card
                        leaves_html = ""
                        if afastamentos:
                            leaves_items = ""
                            for af in afastamentos:
                                dt_ini = af.get('data_inicio', '')[:10] if af.get('data_inicio') else '-'
                                dt_fim = af.get('data_fim', '')[:10] if af.get('data_fim') else '-'
                                try:
                                    dt_ini_fmt = date.fromisoformat(dt_ini).strftime('%d/%m/%Y')
                                    dt_fim_fmt = date.fromisoformat(dt_fim).strftime('%d/%m/%Y')
                                except Exception as e:
                                    print(f"⚠️ Erro silencioso em process_list.py (format. data): {e}")
                                    dt_ini_fmt = dt_ini
                                    dt_fim_fmt = dt_fim
                                descr = af.get('descricao', 'Sem descrição')
                                leaves_items += f'<div class="leave-item">{dt_ini_fmt} a {dt_fim_fmt} — {descr}</div>'
                            leaves_html = f'<div class="leaves-header">📅 Afastamentos no período:</div>{leaves_items}'
                        
                        st.markdown(f"""
                        <div class="suspension-card">
                            <div class="suspension-title">⏸️ Prazo Afetado</div>
                            <div class="suspension-detail">{dias_total} dia(s) de afastamento no período — prazo ajustado automaticamente.</div>
                            {leaves_html}
                        </div>
                        """, unsafe_allow_html=True)
            
            # Actions
            act_c1, act_c2, act_c3 = st.columns(3)
            with act_c1:
                if st.button("✏️ Editar", key=f"edit_btn_{pid}"):
                    st.session_state.processo_para_editar_id = pid
                    st.rerun()
            with act_c2:
                # Indicador de comentários não lidos
                comment_label = "💬 Comentários" if not item['tem_nao_lidos'] else "💬 Comentários 🔴"
                if st.button(comment_label, key=f"comment_btn_{pid}"):
                    st.session_state['processo_id'] = pid
                    st.session_state['came_from'] = "pages/Processos_no_Gabinete.py"
                    st.switch_page("pages/Comentarios_Processo.py")
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
