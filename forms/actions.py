
import streamlit as st
from datetime import date
from supabase_client import QueryBuilder, insert
from db_compat import (
    get_process_by_id, get_user_by_id, update_process,
    add_process_history, create_notification
)
from utils.notifications import send_email_notification

def display_analise_form(processo_id):
    """Formulário para o Chefe aprovar ou devolver o trabalho do Servidor."""
    st.header("Analisando Processo")
    
    processo = get_process_by_id(processo_id)
    if not processo:
        st.error("Processo não encontrado.")
        if 'processo_em_analise_id' in st.session_state:
            del st.session_state['processo_em_analise_id']
        st.button("Voltar ao Dashboard")
        return
        
    sid = processo.get('id_servidor_responsavel')
    servidor_nome = "Desconhecido"
    if sid:
        servidor = get_user_by_id(sid)
        if servidor:
            servidor_nome = servidor.get('nome_completo')
            
    st.info(f"**Processo:** {processo.get('processo_numero')} | **Servidor:** {servidor_nome}")
    
    pid = processo.get('id')
    p_num = processo.get('processo_numero')

    with st.form("form_analise"):
        observacao_devolucao = st.text_area("Observações para Devolução (obrigatório se devolver):")
        
        st.markdown("---")
        st.markdown("**Ações de Devolução:**")
        col1, col2 = st.columns(2)
        with col1:
            nova_data_atribuicao = st.date_input("Nova Data de Atribuição", value=date.today(), format="DD/MM/YYYY")
        with col2:
            prazo_adicional = st.number_input("Prazo Adicional (dias corridos)", min_value=1, step=1, value=5)
        devolver_button = st.form_submit_button("↩️ Devolver ao Servidor com Novo Prazo")

        st.markdown("---")
        st.markdown("**Ações de Aprovação:**")
        data_aprovacao = st.date_input("Data de Envio ao Procurador", value=date.today(), format="DD/MM/YYYY")
        aprovar_e_enviar_procurador = st.form_submit_button("✅ Aprovar e Enviar para Procurador", type="primary")
        
        if st.form_submit_button("Cancelar"):
            if 'processo_em_analise_id' in st.session_state:
                del st.session_state['processo_em_analise_id']
            st.rerun()
        
        if aprovar_e_enviar_procurador:
            updates = {
                "data_conclusao_chefe": data_aprovacao.isoformat()
            }
            if processo.get('ignorar_analise_procurador'):
                updates["status_chefe"] = "Finalizado"
                updates["status_servidor"] = "Finalizado"
            else:
                updates["status_chefe"] = "Processo com o Procurador"

            QueryBuilder("processo_favoritos") \
                .eq("id_usuario", st.session_state.user_id) \
                .eq("id_processo", pid) \
                .delete() \
                .execute()
            
            update_process(pid, updates)
            st.success("Processo enviado para o Procurador!")
            st.toast(f"Processo {p_num} enviado com sucesso.")
            
            if 'processo_em_analise_id' in st.session_state:
                del st.session_state['processo_em_analise_id']
            st.rerun()
        
        if devolver_button:
            if not observacao_devolucao:
                st.error("Para devolver um processo, as observações são obrigatórias.")
            else:
                updates = {
                    "status_servidor": "Devolvido",
                    "status_chefe": "Devolvido",
                    "data_conclusao_servidor": None,
                    "data_atribuicao_servidor": nova_data_atribuicao.isoformat(),
                    "prazo_servidor_aplicado": prazo_adicional,
                    "observacao_chefe": observacao_devolucao
                }
                
                update_process(pid, updates)
                
                add_process_history(
                    pid, 
                    "Devolvido pelo Chefe", 
                    st.session_state.active_user_id,
                    observacao_devolucao
                )

                insert("comentarios", {
                    "id_processo": pid,
                    "id_usuario": st.session_state.active_user_id,
                    "texto": f"PROCESSO DEVOLVIDO: {observacao_devolucao}"
                })

                if sid:
                    create_notification(
                        sid,
                        f"O processo '{p_num}' foi devolvido por {st.session_state.get('user_nome', 'Chefe')}."
                    )
                
                    servidor = get_user_by_id(sid)
                    if servidor and servidor.get('email') and servidor.get('notifica_email_processo_devolvido'):
                        assunto = f"Processo Devolvido para Ajustes: {p_num}"
                        corpo = f"""
                        <html><body>
                        <p>Olá {servidor.get('nome_completo')},</p>
                        <p>O processo abaixo foi devolvido pelo seu chefe de gabinete com as seguintes observações:</p>
                        <ul>
                            <li><b>Número:</b> {p_num}</li>
                            <li><b>Observações:</b> {observacao_devolucao}</li>
                        </ul>
                        <p>Acesse o sistema para mais detalhes.</p>
                        </body></html>
                        """
                        send_email_notification(servidor['email'], assunto, corpo)

                st.warning("Processo devolvido ao servidor com novo prazo.")
                if 'processo_em_analise_id' in st.session_state:
                    del st.session_state['processo_em_analise_id']
                st.rerun()

def display_chefe_update_form(processo_id):
    """Formulário para o chefe concluir um processo."""
    st.header("Concluir Processo do Chefe de Gabinete")
    
    processo = get_process_by_id(processo_id)
    if not processo:
        st.error("Processo não encontrado.")
        return
    
    pid = processo.get('id')
    p_num = processo.get('processo_numero')
    st.info(f"**Processo:** {p_num}")

    with st.form("chefe_update_form"):
        data_conclusao = st.date_input("Data de Conclusão", value=date.today())
        observacao_chefe = st.text_area("Observações (será salva no histórico do processo):", value=processo.get('observacao_chefe') or "")
        
        concluir_button = st.form_submit_button("✅ Concluir e Enviar para Procurador", type="primary")
        cancelar_button = st.form_submit_button("Cancelar")

        if concluir_button:
            updates = {
                "data_conclusao_servidor": data_conclusao.isoformat(),
                "data_conclusao_chefe": data_conclusao.isoformat(),
                "status_servidor": "Concluído",
                "status_chefe": "Processo com o Procurador",
                "observacao_chefe": observacao_chefe
            }
            
            update_process(pid, updates)
            
            add_process_history(
                pid, 
                "Concluído pelo Chefe de Gabinete", 
                st.session_state.active_user_id,
                observacao_chefe
            )
            
            proc_id = processo.get('id_procurador')
            if proc_id:
                procurador = get_user_by_id(proc_id)
                if procurador and procurador.get('email') and procurador.get('notifica_email_pronto_analise'):
                    assunto = f"Processo Pronto para Análise: {p_num}"
                    corpo = f"""
                    <html><body>
                    <p>Olá {procurador.get('nome_completo')},</p>
                    <p>O processo <b>{p_num}</b> foi concluído pelo Chefe de Gabinete e está pronto para sua análise.</p>
                    <p>Acesse o sistema para mais detalhes.</p>
                    </body></html>
                    """
                    send_email_notification(procurador['email'], assunto, corpo)

            st.success("Processo concluído e enviado para o procurador!")
            if 'processo_para_atualizar_id' in st.session_state:
                del st.session_state['processo_para_atualizar_id']
            st.rerun()
        
        if cancelar_button:
            if 'processo_para_atualizar_id' in st.session_state:
                del st.session_state['processo_para_atualizar_id']
            st.rerun()

def display_servidor_update_form(processo_id):
    """Formulário para o servidor concluir um processo."""
    st.header("Atualizar Andamento do Processo")
    
    processo = get_process_by_id(processo_id)
    if not processo:
        st.error("Processo não encontrado.")
        return
    
    pid = processo.get('id')
    p_num = processo.get('processo_numero')
    
    st.info(f"**Processo:** {p_num}")
    if processo.get('status_servidor') == "Devolvido":
        st.warning(f"Este processo foi devolvido. Verifique os comentários para mais detalhes.")

    with st.form("servidor_update_form"):
        data_conclusao = st.date_input("Data de Conclusão", value=date.today())
        observacao_servidor = ""
        
        concluir_button = st.form_submit_button("✅ Concluir e Enviar para Revisão", type="primary")
        cancelar_button = st.form_submit_button("Cancelar")

        if concluir_button:
            updates = {
                "data_conclusao_servidor": data_conclusao.isoformat(),
                "status_servidor": "Concluído"
            }

            if processo.get('ignorar_revisao_chefe'):
                updates["status_chefe"] = "Processo com o Procurador"
                if processo.get('ignorar_analise_procurador'):
                    updates["status_chefe"] = "Finalizado"
                    updates["status_servidor"] = "Finalizado"
            else:
                updates["status_chefe"] = "Aguardando Análise"
            
            QueryBuilder("processo_favoritos") \
                .eq("id_usuario", st.session_state.user_id) \
                .eq("id_processo", pid) \
                .delete() \
                .execute()
            st.toast(f"Processo {p_num} removido dos seus favoritos ao ser concluído.")

            update_process(pid, updates)

            add_process_history(
                pid, 
                "Concluído pelo Servidor", 
                st.session_state.active_user_id,
                observacao_servidor
            )
            
            cid = processo.get('id_chefe_gabinete')
            if cid:
                create_notification(
                    cid, 
                    f"O servidor {st.session_state.get('user_nome', 'Servidor')} concluiu o processo '{p_num}'."
                )
                
                chefe = get_user_by_id(cid)
                if chefe and chefe.get('email') and chefe.get('notifica_email_processo_concluido'):
                    assunto = f"Processo Concluído pelo Servidor: {p_num}"
                    corpo = f"""
                    <html><body>
                    <p>Olá {chefe.get('nome_completo')},</p>
                    <p>O servidor <b>{st.session_state.get('user_nome', 'Servidor')}</b> concluiu o processo abaixo e ele aguarda sua revisão.</p>
                    <ul>
                        <li><b>Número:</b> {p_num}</li>
                    </ul>
                    <p>Acesse o sistema para analisar.</p>
                    </body></html>
                    """
                    send_email_notification(chefe['email'], assunto, corpo)

            st.success("Processo concluído e enviado para revisão!")
            if 'processo_para_atualizar_id' in st.session_state:
                del st.session_state['processo_para_atualizar_id']
            st.rerun()
        
        if cancelar_button:
            if 'processo_para_atualizar_id' in st.session_state:
                del st.session_state['processo_para_atualizar_id']
            st.rerun()
