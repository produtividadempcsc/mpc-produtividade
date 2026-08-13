
import streamlit as st
import base64
import os
from PIL import Image
from datetime import date, datetime, time
from utils.timezone import today_brazil
import pytz
from supabase_client import QueryBuilder
from db_compat import (
    get_user_by_id, get_process_history, get_product_type_by_id,
    get_historico_servidores
)
from services.prazo_service import calculate_due_date
from com_utils import convert_docx_to_pdf_threaded

# --- CONFIGURAÇÃO E ASSETS ---

def load_logo():
    """Carrega o logo da aplicação."""
    logo_path = "logo_mpcsc.jpg"
    if os.path.exists(logo_path):
        return Image.open(logo_path)
    else:
        st.error("Arquivo de logo 'logo_mpcsc.jpg' não encontrado.")
        return None

# --- HELPERS VISUAIS (CORES E ÍCONES) ---

def get_status_color(status):
    """Retorna um código de cor hexadecimal com base no status do processo."""
    if status in ["Atrasado", "Revisão Atrasada"]: return "#D32F2F"
    elif status == "No Prazo": return "#388E3C"
    elif status == "Devolvido": return "#E65100"
    elif status == "Processo com o Procurador": return "#5E35B1"
    elif status == "Concluído": return "#616161"
    elif status in ["Finalizado", "Aguardando Análise"]: return "#0D47A1"
    else: return "black"

def get_status_emoji(status):
    """Retorna um ícone de status (emoji) com base no status do processo."""
    if status in ["Atrasado", "Revisão Atrasada"]: return "🔴"
    elif status == "No Prazo": return "🟢"
    elif status == "Devolvido": return "🟠"
    elif status == "Processo com o Procurador": return "🟣"
    elif status == "Concluído": return "⚫"
    elif status in ["Finalizado", "Aguardando Análise"]: return "🔵"
    else: return "⚪"

def display_icon_legend():
    """Exibe a legenda de status e ícones."""
    with st.expander("**LEGENDA DE STATUS E ÍCONES**", expanded=False):
        st.markdown("##### Legenda de Status")
        
        status_definitions = {
            "No Prazo": ("🟢", "#388E3C"),
            "Atrasado": ("🔴", "#D32F2F"),
            "Devolvido": ("🟠", "#E65100"),
            "Concluído": ("⚫", "#616161"),
            "Processo com o Procurador": ("🟣", "#5E35B1"),
            "Finalizado": ("🔵", "#0D47A1")
        }

        col1, col2, col3 = st.columns(3)
        with col1:
            for status, (emoji, color) in list(status_definitions.items())[:2]:
                st.markdown(f'<span style="color:{color};">{emoji} {status}</span>', unsafe_allow_html=True)
        with col2:
            for status, (emoji, color) in list(status_definitions.items())[2:4]:
                st.markdown(f'<span style="color:{color};">{emoji} {status}</span>', unsafe_allow_html=True)
        with col3:
            for status, (emoji, color) in list(status_definitions.items())[4:]:
                st.markdown(f'<span style="color:{color};">{emoji} {status}</span>', unsafe_allow_html=True)

        st.markdown("##### Legenda de Ícones")
        st.markdown(
            """
            - **Prioridade:**
                - 🔥 Urgente
                - ⚠️ Prioritário
            - 💬 **Comentários:** Indica a presença de comentários não lidos.
            - 📎 **Anexos:** Indica que o processo possui arquivos anexados.
            """
        )

# --- VISUALIZAÇÃO DE ARQUIVOS ---

def display_file(file_content: bytes, file_name: str):
    """
    Exibe um arquivo. Para PDFs, prioriza um botão de download.
    """
    if not file_content:
        st.error(f"Não foi possível processar '{file_name}' porque o conteúdo está vazio.")
        return

    file_extension = os.path.splitext(file_name)[1].lower()
    
    try:
        if file_extension == ".pdf":
            st.download_button(
                label=f"⬇️ Baixar {file_name}",
                data=file_content,
                file_name=file_name,
                mime="application/pdf",
                use_container_width=True,
                type="primary",
                help="Clique aqui para baixar o arquivo PDF."
            )
            st.info("Se a pré-visualização abaixo estiver em branco, por favor, utilize o botão de download acima.")
            base64_pdf = base64.b64encode(file_content).decode('utf-8')
            pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"/>'
            st.markdown(pdf_display, unsafe_allow_html=True)

        elif file_extension == ".docx":
            st.download_button(
                label=f"⬇️ Baixar {file_name} (original)",
                data=file_content,
                file_name=file_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                type="primary"
            )
            st.info("Tentando gerar uma pré-visualização do documento. Se falhar, use o download.")

            with st.spinner("Convertendo .docx para PDF para visualização..."):
                temp_docx_path = "temp_viewer.docx"
                temp_pdf_path = "temp_viewer.pdf"
                try:
                    with open(temp_docx_path, "wb") as f: f.write(file_content)
                    convert_docx_to_pdf_threaded(temp_docx_path, temp_pdf_path)

                    if not os.path.exists(temp_pdf_path) or os.path.getsize(temp_pdf_path) == 0:
                        st.warning("A conversão para PDF não produziu um arquivo visualizável.")
                    else:
                        with open(temp_pdf_path, "rb") as f: pdf_bytes = f.read()
                        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
                        pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"/>'
                        st.markdown(pdf_display, unsafe_allow_html=True)
                except Exception as e:
                    st.warning(f"Não foi possível gerar a pré-visualização: {e}")
                finally:
                    if os.path.exists(temp_docx_path): os.remove(temp_docx_path)
                    if os.path.exists(temp_pdf_path): os.remove(temp_pdf_path)
        
        elif file_extension in [".png", ".jpg", ".jpeg"]:
            st.image(file_content)

        elif file_extension == ".txt":
            st.text(file_content.decode("utf-8"))
            
        else:
            st.warning(f"Visualização não suportada para '{file_extension}'. Baixe o arquivo.")
            st.download_button(
                label=f"⬇️ Baixar {file_name}",
                data=file_content,
                file_name=file_name,
                use_container_width=True
            )
            
    except Exception as e:
        st.error(f"Erro ao processar arquivo '{file_name}': {e}")


# --- COMPONENTES DE EXPANSÃO (FAVORITOS / SUSPENSOS) ---




def display_suspensos_expander(db=None, user_id=None, current_page_path=None, usuarios_cache=None):
    """
    Cria um expander com a lista de processos suspensos do usuário.
    
    Args:
        usuarios_cache: Dict {user_id: user_dict} para evitar queries N+1
    """
    from utils.common import batch_has_unread_comments
    
    if 'history_visible_susp' not in st.session_state:
        st.session_state.history_visible_susp = {}

    suspensos = QueryBuilder("processos") \
        .eq("id_chefe_gabinete", user_id) \
        .eq("prazo_status", "Suspenso") \
        .execute()

    if not suspensos:
        with st.expander("🚫 Processos Suspensos (0)", expanded=False):
            st.info("Não há processos suspensos no momento.")
        return

    # Batch de comentários não lidos
    susp_ids = [p.get('id') for p in suspensos]
    unread_cache = batch_has_unread_comments(susp_ids, user_id) if susp_ids else {}

    with st.expander(f"🚫 Processos Suspensos ({len(suspensos)})", expanded=False):
        for processo in suspensos:
            pid = processo.get('id')
            status_chefe = processo.get('status_chefe')
            status_serv = processo.get('status_servidor')

            status_geral = status_chefe if status_chefe not in ["Aguardando Análise", "Devolvido"] else status_serv
            status_icon = get_status_emoji(status_geral)
            prio = processo.get('prioridade')
            priority_icon = '🔥' if prio == 'Urgente' else '⚠️' if prio == 'Prioritário' else ''

            expander_label = f"{priority_icon}{status_icon} **{processo.get('processo_numero')}** | Prioridade: **{prio}**"

            with st.container(border=True):
                st.markdown(expander_label)
                cor_status = get_status_color(status_geral)
                
                # Usar cache se disponível, senão query individual
                if usuarios_cache:
                    chefe = usuarios_cache.get(processo.get('id_chefe_gabinete'))
                    proc = usuarios_cache.get(processo.get('id_procurador'))
                    serv = usuarios_cache.get(processo.get('id_servidor_responsavel'))
                else:
                    chefe = get_user_by_id(processo.get('id_chefe_gabinete'))
                    proc = get_user_by_id(processo.get('id_procurador'))
                    serv = get_user_by_id(processo.get('id_servidor_responsavel'))
                
                chefe_nome = chefe.get('nome_completo') if chefe else "N/A"
                procurador_nome = proc.get('nome_completo') if proc else "N/A"
                servidor_nome = serv.get('nome_completo') if serv else "N/A"
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Chefe de Gabinete:** {chefe_nome}")
                    st.markdown(f"**Procurador Vinculado:** {procurador_nome}")
                    st.markdown(f"**Servidor Responsável:** {servidor_nome}")
                with c2:
                    st.markdown(f'**Status:** <b style="color:{cor_status};">{status_geral}</b>', unsafe_allow_html=True)
                    dt_atrib = processo.get('data_atribuicao_servidor')
                    if dt_atrib:
                        dt_str = dt_atrib if isinstance(dt_atrib, str) else dt_atrib.strftime('%d/%m/%Y')
                        st.markdown(f"**Atribuído em:** {dt_str}")

                st.markdown("---")
                
                b1, b2, b3 = st.columns(3)
                active_perfil = st.session_state.get("active_perfil")

                with b1:
                    if active_perfil in ["Servidor", "Chefe de Gabinete"] and current_page_path.lower() == 'pages/meus_processos.py':
                        if status_serv not in ["Concluído", "Finalizado"]:
                            if st.button("Atualizar Andamento", key=f"susp_update_serv_{pid}", type="primary", use_container_width=True):
                                st.session_state['processo_para_atualizar_id'] = pid
                                st.rerun()
                    elif active_perfil in ["Procurador", "Administrador"] and current_page_path.lower() == 'pages/processos_mpc.py':
                        if st.button("Editar Processo", key=f"susp_edit_mpc_{pid}", use_container_width=True):
                            st.session_state['processo_para_editar_id'] = pid
                            st.rerun()
                    elif active_perfil == "Chefe de Gabinete" and current_page_path.lower() == 'pages/processos_para_revisao.py':
                         if st.button("Analisar Processo", key=f"susp_analise_rev_{pid}", type="primary", use_container_width=True):
                            st.session_state['processo_em_analise_id'] = pid
                            st.rerun()
                    elif active_perfil == "Chefe de Gabinete" and current_page_path.lower() == 'pages/processos_no_gabinete.py':
                        if st.button("Editar Processo", key=f"susp_edit_gab_{pid}", use_container_width=True):
                            st.session_state['processo_para_editar_id'] = pid
                            st.rerun()

                with b2:
                    # Usar cache de unread
                    tem_nao_lidos = unread_cache.get(pid, False)
                    lbl = "Comentário Não Lido" if tem_nao_lidos else "Comentários"
                    typ = "primary" if tem_nao_lidos else "secondary"
                    if st.button(lbl, key=f"susp_comments_{pid}", use_container_width=True, type=typ):
                        st.session_state['processo_id'] = pid
                        st.session_state['came_from'] = current_page_path
                        st.switch_page('pages/Comentarios_Processo.py')

                with b3:
                    if st.button("Ver Histórico", key=f"susp_hist_{pid}", use_container_width=True):
                        st.session_state.history_visible_susp[pid] = not st.session_state.history_visible_susp.get(pid, False)
                        st.rerun()

                if st.session_state.history_visible_susp.get(pid, False):
                    display_process_history(processo, db)


def display_process_history(processo, db=None):
    """
    Exibe a timeline visual de histórico de um processo com CSS estilizado.
    """
    # Ler CSS para inline (st.html renderiza em iframe isolado)
    css_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "styles", "timeline.css")
    timeline_css = ""
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            timeline_css = f.read()
    
    # Helper polyfill
    def get_val(obj, attr, default=None):
        if isinstance(obj, dict): return obj.get(attr, default)
        return getattr(obj, attr, default)

    pid = get_val(processo, 'id')
    status_serv = get_val(processo, 'status_servidor')
    status_chefe = get_val(processo, 'status_chefe')
    
    st.subheader("📋 Histórico do Processo")
    
    # ── Stepper Bar ──
    dt_atrib = get_val(processo, 'data_atribuicao_servidor')
    dt_concl_serv = get_val(processo, 'data_conclusao_servidor')
    dt_concl_chefe = get_val(processo, 'data_conclusao_chefe')
    
    def parse_dt(d):
        if isinstance(d, str): return date.fromisoformat(d)
        return d
    
    dt_atrib = parse_dt(dt_atrib)
    dt_concl_serv = parse_dt(dt_concl_serv)
    dt_concl_chefe = parse_dt(dt_concl_chefe)
    
    # Determinar estados do stepper
    serv_state = "completed" if dt_concl_serv else ("active" if dt_atrib else "pending")
    
    # Se o chefe estiver revisando, o estado dele deve ser ativo (mesmo que já tenha data de conclusão anterior)
    if status_chefe in ["Aguardando Análise", "Revisão Atrasada"]:
        chefe_state = "active"
        proc_state = "pending"
    else:
        chefe_state = "completed" if dt_concl_chefe else ("active" if dt_concl_serv else "pending")
        proc_state = "completed" if status_chefe == "Finalizado" else ("active" if dt_concl_chefe else "pending")

    
    conn1_state = "completed" if serv_state == "completed" else "pending"
    conn2_state = "completed" if chefe_state == "completed" else "pending"
    
    stepper_html = f"""
    <div class="process-stepper">
        <div class="stepper-step">
            <div class="stepper-icon {serv_state}">{"✓" if serv_state == "completed" else "1"}</div>
            <div class="stepper-label {serv_state}">Servidor</div>
        </div>
        <div class="stepper-connector {conn1_state}"></div>
        <div class="stepper-step">
            <div class="stepper-icon {chefe_state}">{"✓" if chefe_state == "completed" else "2"}</div>
            <div class="stepper-label {chefe_state}">Chefe</div>
        </div>
        <div class="stepper-connector {conn2_state}"></div>
        <div class="stepper-step">
            <div class="stepper-icon {proc_state}">{"✓" if proc_state == "completed" else "3"}</div>
            <div class="stepper-label {proc_state}">Procurador</div>
        </div>
    </div>
    """
    st.html(f"<style>{timeline_css}</style>{stepper_html}")
    
    # ── Coletar Eventos ──
    timeline_events = []
    
    servidor_id = get_val(processo, 'id_servidor_responsavel')
    chefe_id = get_val(processo, 'id_chefe_gabinete')
    
    serv_user = get_user_by_id(servidor_id) if servidor_id else None
    chefe_user = get_user_by_id(chefe_id) if chefe_id else None
    
    servidor_nome = serv_user.get('nome_completo') if serv_user else "N/A"
    chefe_nome = chefe_user.get('nome_completo') if chefe_user else "N/A"
    
    prod_id = get_val(processo, 'id_tipo_produto')
    produto_obj = get_product_type_by_id(prod_id) if prod_id else None

    if dt_atrib:
        timeline_events.append({
            "date": dt_atrib,
            "description": f"Processo atribuído ao servidor {servidor_nome}.",
            "tipo": "atribuicao"
        })
    
    if dt_concl_serv:
        tipo_ev = "conclusao"
        desc = "Etapa do servidor concluída."
        if produto_obj:
            dias_susp = get_val(processo, 'prazo_total_dias_suspenso', 0)
            prazo_serv = get_val(processo, 'prazo_servidor_aplicado')
            tipo_cont = produto_obj.get('tipo_contagem_prazo')
            
            data_final_servidor = calculate_due_date(
                start_date=dt_atrib, prazo_dias=prazo_serv,
                tipo_contagem=tipo_cont, id_usuario=servidor_id,
                dias_suspensos=dias_susp
            )
            if dt_concl_serv > data_final_servidor:
                status = "⚠️ Atrasado"
                tipo_ev = "atraso"
            else:
                status = "✅ No prazo"
            desc = f"Etapa do servidor concluída. Status: {status}"
            
        timeline_events.append({
            "date": dt_concl_serv,
            "description": desc,
            "tipo": tipo_ev
        })

    if dt_concl_chefe:
        tipo_ev = "conclusao"
        desc = "Revisão do Chefe de Gabinete concluída."
        if produto_obj and dt_concl_serv:
            dias_susp = get_val(processo, 'prazo_total_dias_suspenso', 0)
            prazo_chefe = get_val(processo, 'prazo_chefe_aplicado')
            tipo_cont = produto_obj.get('tipo_contagem_prazo')
            
            dt_inicio_chefe = get_val(processo, 'data_atribuicao_chefe')
            if dt_inicio_chefe:
                dt_inicio_chefe = parse_dt(dt_inicio_chefe)
            else:
                dt_inicio_chefe = dt_concl_serv

            data_final_revisao = calculate_due_date(
                start_date=dt_inicio_chefe, prazo_dias=prazo_chefe,
                tipo_contagem=tipo_cont, id_usuario=chefe_id,
                dias_suspensos=dias_susp
            )
            if dt_concl_chefe > data_final_revisao:
                status = "⚠️ Atrasado"
                tipo_ev = "atraso"
            else:
                status = "✅ No prazo"
            desc = f"Revisão do Chefe concluída. Status: {status}"

        timeline_events.append({
            "date": dt_concl_chefe,
            "description": desc,
            "tipo": tipo_ev
        })

    sao_paulo_tz = pytz.timezone('America/Sao_Paulo')
    
    historico_list = get_process_history(pid)
    
    for evento in historico_list:
        nome_usuario = "Sistema"
        uid_acao = evento.get('id_usuario_acao')
        if uid_acao:
            u = get_user_by_id(uid_acao)
            if u: nome_usuario = u.get('nome_completo')
            
        full_description = f"{evento.get('evento')} por {nome_usuario}."
        if evento.get('observacao'):
            full_description += f" Obs: {evento.get('observacao')}"
        
        # Determinar tipo do evento
        evento_texto = (evento.get('evento') or '').lower()
        if 'devol' in evento_texto:
            tipo_ev = "devolucao"
        elif 'conclu' in evento_texto:
            tipo_ev = "conclusao"
        else:
            tipo_ev = "historico"
        
        ts = evento.get('timestamp')
        if isinstance(ts, str):
            try:
                ts = ts.replace('Z', '+00:00')
                utc_timestamp = datetime.fromisoformat(ts)
            except Exception as e:
                print(f"⚠️ Erro silencioso em ui.py (timestamp): {e}")
                from utils.timezone import now_brazil
                utc_timestamp = now_brazil()
        else:
            utc_timestamp = ts

        if utc_timestamp.tzinfo is None:
            utc_timestamp = utc_timestamp.replace(tzinfo=pytz.utc)

        sao_paulo_timestamp = utc_timestamp.astimezone(sao_paulo_tz)
        
        timeline_events.append({
            "date": sao_paulo_timestamp.date(),
            "time": sao_paulo_timestamp.strftime('%H:%M:%S'),
            "description": full_description,
            "original_timestamp": sao_paulo_timestamp.replace(tzinfo=None),
            "tipo": tipo_ev
        })

    def add_leave_events(user_id, start_p, end_p, user_name, type_desc):
        if not user_id or not start_p: return
        start_str = start_p.isoformat()
        end_str = end_p.isoformat() if end_p else today_brazil().isoformat()
        
        afastamentos = QueryBuilder("afastamentos") \
            .eq("id_usuario", user_id) \
            .lte("data_inicio", end_str) \
            .gte("data_fim", start_str) \
            .execute()
            
        for af in afastamentos:
            ad_start = parse_dt(af['data_inicio'])
            ad_end = parse_dt(af['data_fim'])
            
            timeline_events.append({
                "date": ad_start,
                "description": f"Prazo {type_desc} suspenso — Afastamento de {user_name} ({af.get('descricao')}).",
                "tipo": "suspensao"
            })
            dias_suspensao = (ad_end - ad_start).days + 1
            timeline_events.append({
                "date": ad_end,
                "description": f"Prazo {type_desc} retomado para {user_name}. Suspensão: {dias_suspensao} dia(s).",
                "tipo": "retomada"
            })

    if dt_atrib:
        p_fim = dt_concl_serv if dt_concl_serv else today_brazil()
        add_leave_events(servidor_id, dt_atrib, p_fim, servidor_nome, "")

    if dt_concl_serv and chefe_id:
        p_fim = dt_concl_chefe if dt_concl_chefe else today_brazil()
        add_leave_events(chefe_id, dt_concl_serv, p_fim, chefe_nome, "de revisão")

    # ── Eventos de Troca de Servidor ──
    hist_servidores = get_historico_servidores(pid)
    for i_hs, hs in enumerate(hist_servidores):
        if hs.get('data_fim'):  # Vínculo encerrado = houve troca
            hs_serv = get_user_by_id(hs['id_servidor'])
            hs_serv_nome = hs_serv.get('nome_completo') if hs_serv else 'Desconhecido'
            d_inicio = parse_dt(hs['data_inicio'])
            d_fim = parse_dt(hs['data_fim'])
            dias = (d_fim - d_inicio).days
            
            # Identificar próximo servidor
            prox_serv_nome = 'Desconhecido'
            if i_hs + 1 < len(hist_servidores):
                prox_hs = hist_servidores[i_hs + 1]
                prox_u = get_user_by_id(prox_hs['id_servidor'])
                if prox_u:
                    prox_serv_nome = prox_u.get('nome_completo', 'Desconhecido')
            
            timeline_events.append({
                "date": d_fim,
                "description": f"Servidor {hs_serv_nome} ({dias} dia{'s' if dias != 1 else ''} com o processo) substituído por {prox_serv_nome}.",
                "tipo": "troca_servidor"
            })

    if not timeline_events:
        st.info("Nenhum evento registrado para este processo.")
        return
    
    # ── Renderizar Timeline ──
    TIPO_BADGES = {
        "atribuicao": ("Atribuição", "badge-atribuicao"),
        "conclusao": ("Conclusão", "badge-conclusao"),
        "atraso": ("Atrasado", "badge-atraso"),
        "devolucao": ("Devolução", "badge-devolucao"),
        "suspensao": ("Suspensão", "badge-suspensao"),
        "retomada": ("Retomada", "badge-retomada"),
        "historico": ("Histórico", "badge-historico"),
        "troca_servidor": ("Troca de Servidor", "badge-devolucao"),
    }
    
    sorted_events = sorted(timeline_events, key=lambda x: x.get('original_timestamp') or datetime.combine(x['date'], time.min))
    
    html_parts = ['<div class="tl-container">']
    
    for i, event in enumerate(sorted_events):
        date_str = event['date'].strftime('%d/%m/%Y')
        event_time = event.get("time")
        display_date = f"{date_str} às {event_time}" if event_time else date_str
        
        tipo = event.get("tipo", "historico")
        badge_label, badge_class = TIPO_BADGES.get(tipo, ("Evento", "badge-historico"))
        
        html_parts.append(f"""
        <div class="tl-event tl-{tipo}">
            <div class="tl-header">
                <span class="tl-date">📅 {display_date}</span>
                <span class="tl-badge {badge_class}">{badge_label}</span>
            </div>
            <div class="tl-desc">{event['description']}</div>
        </div>
        """)
        
        # Adicionar indicador de duração entre eventos
        if i < len(sorted_events) - 1:
            next_event = sorted_events[i + 1]
            current_dt = event.get('original_timestamp') or datetime.combine(event['date'], time.min)
            next_dt = next_event.get('original_timestamp') or datetime.combine(next_event['date'], time.min)
            
            diff = next_dt - current_dt
            if diff.days > 0:
                duration_text = f"{diff.days} dia{'s' if diff.days > 1 else ''}"
            elif diff.seconds > 3600:
                duration_text = f"{diff.seconds // 3600}h"
            elif diff.seconds > 60:
                duration_text = f"{diff.seconds // 60}min"
            else:
                duration_text = ""
            
            if duration_text:
                html_parts.append(f"""
                <div class="tl-duration">
                    <span class="tl-duration-badge">⏱ {duration_text}</span>
                </div>
                """)
    
    html_parts.append('</div>')
    
    full_html = f"<style>{timeline_css}</style>" + '\n'.join(html_parts)
    st.html(full_html)

# --- FEEDBACK VISUAL ANIMADO ---

def set_success_feedback(message, type="success", icon="✅"):
    """
    Define a mensagem de feedback visual para ser exibida após o próximo st.rerun().
    Tipos suportados: success, error, warning, info
    """
    st.session_state['visual_feedback'] = {
        "message": message,
        "type": type,
        "icon": icon
    }

def show_feedback_banner():
    """
    Exibe o banner animado de feedback caso haja uma mensagem na sessão.
    Remove a mensagem da sessão em seguida.
    """
    if 'visual_feedback' in st.session_state and st.session_state['visual_feedback']:
        feedback = st.session_state['visual_feedback']
        msg = feedback.get('message', '')
        tipo = feedback.get('type', 'success')
        icon = feedback.get('icon', '✅')
        
        banner_html = f"""
        <style>
        @keyframes feedback-lifecycle {{
          0%   {{ opacity: 0; transform: translate(-50%, -20px); }}
          10%  {{ opacity: 1; transform: translate(-50%, 0); }}
          85%  {{ opacity: 1; transform: translate(-50%, 0); }}
          100% {{ opacity: 0; transform: translate(-50%, -20px); visibility: hidden; }}
        }}
        
        .feedback-banner-container {{
            position: fixed;
            top: 60px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 999999;
            pointer-events: none;
            animation: feedback-lifecycle 2.5s ease forwards;
        }}
        
        .feedback-banner {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 24px;
            border-radius: 14px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
            font-weight: 500;
            font-size: 1.1rem;
        }}
        .feedback-banner.success {{ background-color: #E8F5E9; color: #2E7D32; border: 1px solid #C8E6C9; }}
        .feedback-banner.warning {{ background-color: #FFF3E0; color: #EF6C00; border: 1px solid #FFE0B2; }}
        .feedback-banner.error {{ background-color: #FFEBEE; color: #C62828; border: 1px solid #FFCDD2; }}
        .feedback-banner.info {{ background-color: #E3F2FD; color: #1565C0; border: 1px solid #BBDEFB; }}
        </style>
        <div class="feedback-banner-container">
            <div class="feedback-banner {tipo}">
                <span>{icon}</span>
                <span>{msg}</span>
            </div>
        </div>
        """
        st.markdown(banner_html, unsafe_allow_html=True)
        
        # Limpa o feedback após a exibição
        st.session_state['visual_feedback'] = None
