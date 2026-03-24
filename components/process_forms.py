import streamlit as st
from datetime import date, datetime
from utils.timezone import today_brazil, now_brazil
from supabase_client import QueryBuilder, insert
from db_compat import get_user_by_id
from services.prazo_service import calculate_due_date
import utils.notifications as notif_utils

def render_add_process_form(id_chefe_para_acoes, chefe_logado, equipe_atribuivel, all_prods_cached, procuradores_dict):
    """Renderiza o formulário de cadastro e atribuição de um novo processo."""
    with st.expander("➕ Adicionar Novo Processo", expanded=False):
        with st.form("new_process_form", clear_on_submit=True):
            st.subheader("📝 Registrar e Atribuir Novo Processo")
            
            servidores_dict = {s['nome_completo']: s['id'] for s in equipe_atribuivel if s.get('ativo', True)}
            if chefe_logado:
                servidores_dict[chefe_logado['nome_completo']] = id_chefe_para_acoes
            
            produtos_form_dict = {}
            prods_sorted = sorted(all_prods_cached, key=lambda x: x.get('nome_produto', ''))
            for p in prods_sorted:
                 if p['nome_produto'] not in produtos_form_dict:
                     produtos_form_dict[p['nome_produto']] = p['id']
                        
            col1, col2 = st.columns(2)
            with col1:
                processo_numero = st.text_input("📄 Número do Processo")
                id_tipo_produto_nome = st.selectbox("📋 Tipo de Produto", options=list(produtos_form_dict.keys()))
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
            data_atribuicao = st.date_input("📅 Atribuído em", value=today_brazil(), format="DD/MM/YYYY")

            st.markdown("---")
            st.markdown("**⚙️ Opções de Exceção:**")
            col1_check, col2_check, col3_check = st.columns(3)
            with col1_check:
                nao_se_aplica_prazo_servidor = st.checkbox("⏰ Não se aplica prazo ao Servidor", help="Se marcado, nenhum prazo de conclusão será atribuído à tarefa do servidor inicial e a tarefa não será sinalizada como 'atrasada' em nenhum momento.")
            with col2_check:
                ignorar_revisao_chefe = st.checkbox("⏭️ Ignorar etapa de Revisão (Chefe de Gabinete)", help="Se marcado, o sistema deve automaticamente pular essa etapa e encaminhar o processo para a próxima fase do fluxo.")
            with col3_check:
                ignorar_analise_procurador = st.checkbox("⏩ Ignorar etapa de Análise (Procurador)", help="Se marcado, o sistema deve automaticamente pular essa etapa e encaminhar o processo para a próxima fase do fluxo.")
            
            st.markdown("---")
            st.markdown("**📆 Prazo do Setor MPC (Opcional):**")
            col_mpc1, col_mpc2 = st.columns(2)
            with col_mpc1:
                data_entrada_mpc = st.date_input(
                    "Data de Entrada no MPC", 
                    value=None, 
                    format="DD/MM/YYYY",
                    help="Data em que o processo chegou ao MPC. Deixe vazio se não se aplica."
                )
            with col_mpc2:
                prazo_mpc_dias = st.number_input(
                    "Prazo MPC (dias corridos)", 
                    min_value=0, 
                    value=0,
                    help="Prazo total em dias corridos para o processo ser finalizado pelo setor MPC. 0 = Não se aplica."
                )
            
            submitted = st.form_submit_button("✅ Criar e Atribuir Processo", disabled=(not servidores_dict or not procuradores_dict), type="primary")
            
            if submitted and all([processo_numero, id_tipo_produto_nome, id_servidor_nome, id_procurador_nome]):
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
                    "observacao_chefe": observacao_chefe,
                    "data_entrada_mpc": data_entrada_mpc.isoformat() if data_entrada_mpc else None,
                    "prazo_mpc_dias": prazo_mpc_dias if prazo_mpc_dias > 0 else None,
                    "status_mpc": "Não se aplica" if not data_entrada_mpc or prazo_mpc_dias == 0 else "No prazo MPC"
                }
                
                res_proc = insert("processos", novo_processo_data)
                if not res_proc:
                    st.error("Erro ao criar processo.")
                else:
                    novo_pid = res_proc['id']

                    # Registrar vínculo inicial do servidor no histórico
                    from db_compat import registrar_vinculo_servidor
                    registrar_vinculo_servidor(novo_pid, servidores_dict[id_servidor_nome], data_atribuicao)

                    if observacao_chefe:
                        comentario_data = {
                            "id_processo": novo_pid,
                            "id_usuario": id_chefe_para_acoes,
                            "texto": f"OBSERVAÇÃO INICIAL: {observacao_chefe}",
                            "timestamp": now_brazil().isoformat()
                        }
                        insert("comentarios", comentario_data)

                    notificacao_data = {
                        "id_usuario_destino": servidores_dict[id_servidor_nome],
                        "mensagem": f"Novo processo atribuído a você: '{processo_numero}'.",
                        "lida": False,
                        "timestamp": now_brazil().isoformat()
                    }
                    insert("notificacoes", notificacao_data)

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
                    
                    st.toast(f"✅ Processo {processo_numero} criado e atribuído com sucesso!", icon="✅")
                    st.rerun()
