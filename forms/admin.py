
import streamlit as st
from datetime import date, timedelta
from utils.common import parse_date_val
from utils.timezone import today_brazil
from supabase_client import QueryBuilder, select_all, select_by_id, update_by_id, delete_by_id
from db_compat import (
    get_process_by_id, get_user_by_id,
    update_process, add_process_history,
    registrar_vinculo_servidor, fechar_vinculo_servidor
)
from services.prazo_service import count_business_days

def display_edit_prompt_form(prompt_id):
    """Formulário modal para editar um prompt de IA."""
    st.header("✏️ Editando Prompt")
    
    prompt = select_by_id("prompts_ia", prompt_id)
    if not prompt: st.error("Prompt não encontrado."); return

    with st.form("edit_prompt_form"):
        st.info(f"Editando o prompt: **{prompt['titulo']}**")
        novo_titulo = st.text_input("Título", value=prompt['titulo'])
        novo_conteudo = st.text_area("Conteúdo", value=prompt['conteudo'], height=250)
        nova_visibilidade = st.checkbox("Compartilhar com todos?", value=prompt.get('e_publico', False))
        
        salvar_btn = st.form_submit_button("Salvar Alterações")
        cancelar_btn = st.form_submit_button("Cancelar")

        if salvar_btn:
            updates = {
                "titulo": novo_titulo,
                "conteudo": novo_conteudo,
                "e_publico": nova_visibilidade
            }
            update_by_id("prompts_ia", prompt_id, updates)
            st.success("Prompt atualizado com sucesso!")
            del st.session_state['prompt_para_editar_id']
            st.rerun()
        
        if cancelar_btn:
            del st.session_state['prompt_para_editar_id']
            st.rerun()

def display_admin_edit_processo_form(processo_id):
    st.header("✏️ Editando Processo (Admin)")
    
    processo = get_process_by_id(processo_id)
    if not processo:
        st.error("Processo não encontrado.")
        if 'processo_para_editar_admin_id' in st.session_state:
            del st.session_state['processo_para_editar_admin_id']
        st.button("Voltar ao Dashboard")
        return

    pid = processo.get('id')
    p_num = processo.get('processo_numero')

    with st.form("admin_edit_form"):
        st.info(f"Editando o processo **{p_num}**.")
        
        # --- Lógica de Users/Produtos ---
        # Fix #6: Incluir Chefe de Gabinete na lista de servidores responsáveis
        servidores = QueryBuilder("usuarios").in_list("perfil", ["Servidor", "Chefe de Gabinete"]).eq("ativo", True).order("nome_completo").execute()
        servidores_dict = {s['nome_completo']: s['id'] for s in servidores}
        servidores_nomes = list(servidores_dict.keys())
        current_servidor_index = 0

        sid = processo.get('id_servidor_responsavel')
        if sid:
            found_name = next((name for name, i in servidores_dict.items() if i == sid), None)
            if not found_name:
                 s_atual = get_user_by_id(sid)
                 if s_atual:
                    s_name = s_atual.get('nome_completo')
                    servidores_dict[s_name] = sid
                    servidores_nomes.append(s_name)
                    servidores_nomes.sort()
                    found_name = s_name
            if found_name:
                current_servidor_index = servidores_nomes.index(found_name)

        produtos = select_all("tipos_produto") 
        produtos.sort(key=lambda x: x.get('nome_produto', ''))
        produtos_dict = {p['nome_produto']: p['id'] for p in produtos} 
        produtos_nomes = list(produtos_dict.keys())
        
        tid = processo.get('id_tipo_produto')
        current_produto_index = 0
        if tid:
             curr_prod = next((p for p in produtos if p['id'] == tid), None)
             if curr_prod:
                 p_name = curr_prod.get('nome_produto')
                 if p_name in produtos_nomes:
                     current_produto_index = produtos_nomes.index(p_name)

        procuradores = QueryBuilder("usuarios").eq("perfil", "Procurador").eq("ativo", True).order("nome_completo").execute()
        procuradores_dict = {p['nome_completo']: p['id'] for p in procuradores}
        procuradores_nomes = list(procuradores_dict.keys())

        proc_id_val = processo.get('id_procurador')
        current_procurador_index = 0
        if proc_id_val:
            found_name = next((name for name, i in procuradores_dict.items() if i == proc_id_val), None)
            if not found_name:
                proc_atual = get_user_by_id(proc_id_val)
                if proc_atual:
                    proc_name = proc_atual.get('nome_completo')
                    procuradores_dict[proc_name] = proc_id_val
                    procuradores_nomes.append(proc_name)
                    procuradores_nomes.sort()
                    found_name = proc_name
            if found_name:
                current_procurador_index = procuradores_nomes.index(found_name)

        # Fix #7: Carregar e exibir Chefes de Gabinete
        chefes = QueryBuilder("usuarios").eq("perfil", "Chefe de Gabinete").eq("ativo", True).order("nome_completo").execute()
        chefes_dict = {c['nome_completo']: c['id'] for c in chefes}
        chefes_nomes = list(chefes_dict.keys())
        
        cid_val = processo.get('id_chefe_gabinete')
        current_chefe_index = 0
        if cid_val:
             found_name = next((name for name, i in chefes_dict.items() if i == cid_val), None)
             if not found_name:
                 chefe_atual = get_user_by_id(cid_val)
                 if chefe_atual:
                     chefe_name = chefe_atual.get('nome_completo')
                     chefes_dict[chefe_name] = cid_val
                     chefes_nomes.append(chefe_name)
                     chefes_nomes.sort()
                     found_name = chefe_name
             if found_name:
                 current_chefe_index = chefes_nomes.index(found_name)

        col1, col2 = st.columns(2)
        with col1:
            novo_numero = st.text_input("Número do Processo", value=p_num)
            # Fix #17: Tratar lista vazia de servidores
            if servidores_nomes:
                novo_servidor_nome = st.selectbox("Servidor Responsável", options=servidores_nomes, index=current_servidor_index)
            else:
                novo_servidor_nome = st.selectbox("Servidor Responsável", options=["Nenhum servidor disponível"], disabled=True)
            # Fix #7: Selectbox para Chefe de Gabinete
            if chefes_nomes:
                novo_chefe_nome = st.selectbox("Chefe de Gabinete", options=chefes_nomes, index=current_chefe_index)
            else:
                novo_chefe_nome = st.selectbox("Chefe de Gabinete", options=["Nenhum chefe disponível"], disabled=True)
            # Fix #17: Tratar lista vazia de produtos
            if produtos_nomes:
                novo_produto_nome = st.selectbox("Tipo de Produto", options=produtos_nomes, index=current_produto_index)
            else:
                novo_produto_nome = st.selectbox("Tipo de Produto", options=["Nenhum produto disponível"], disabled=True)
        with col2:
            if procuradores_nomes:
                novo_procurador_nome = st.selectbox("Procurador Vinculado", options=procuradores_nomes, index=current_procurador_index)
            else:
                novo_procurador_nome = st.selectbox("Procurador Vinculado", options=["Nenhum procurador disponível"], disabled=True)
            observacao_chefe = st.text_area("Observações do Gabinete", value=processo.get('observacao_chefe') or "")

        st.markdown("---")
        st.subheader("Edição de Datas")
        
        dt_atrib_val = parse_date_val(processo.get('data_atribuicao_servidor'))
        dt_conc_serv_val = parse_date_val(processo.get('data_conclusao_servidor'))
        dt_conc_chefe_val = parse_date_val(processo.get('data_conclusao_chefe'))
        
        col_data1, col_data2, col_data3 = st.columns(3)
        with col_data1:
            data_atribuicao = st.date_input("Data de Atribuição", value=dt_atrib_val)
        with col_data2:
            data_conclusao_servidor = st.date_input("Data de Conclusão do Servidor", value=dt_conc_serv_val)
        with col_data3:
            data_conclusao_chefe = st.date_input("Data de Conclusão da Revisão", value=dt_conc_chefe_val)

        st.markdown("---")
        st.subheader("Opções de Exceção")
        col_check1, col_check2, col_check3 = st.columns(3)
        with col_check1:
            nao_se_aplica_prazo_servidor = st.checkbox("Não se aplica prazo ao Servidor", value=processo.get('nao_se_aplica_prazo_servidor', False), help="Se marcado, nenhum prazo de conclusão será atribuído à tarefa do servidor inicial e a tarefa não será sinalizada como 'atrasada' em nenhum momento.", disabled=dt_conc_serv_val is not None)
        with col_check2:
            ignorar_revisao_chefe = st.checkbox("Ignorar etapa de Revisão (Chefe de Gabinete)", value=processo.get('ignorar_revisao_chefe', False), help="Se marcado, o sistema deve automaticamente pular essa etapa e encaminhar o processo para a próxima fase do fluxo.", disabled=dt_conc_chefe_val is not None)
        with col_check3:
            ignorar_analise_procurador = st.checkbox("Ignorar etapa de Análise (Procurador)", value=processo.get('ignorar_analise_procurador', False), help="Se marcado, o sistema deve automaticamente pular essa etapa e encaminhar o processo para a próxima fase do fluxo.", disabled=processo.get('status_chefe') == "Finalizado")

        salvar_btn = st.form_submit_button("Salvar Alterações")
        cancelar_btn = st.form_submit_button("Cancelar Edição")

        if salvar_btn:
            # Validação: verificar se as seleções são válidas
            if not servidores_nomes or novo_servidor_nome == "Nenhum servidor disponível":
                st.error("Não há servidores disponíveis para selecionar.")
                st.stop()
            if not produtos_nomes or novo_produto_nome == "Nenhum produto disponível":
                st.error("Não há tipos de produto disponíveis para selecionar.")
                st.stop()

            selected_serv_id = servidores_dict[novo_servidor_nome]
            old_serv_id = processo.get('id_servidor_responsavel')
            
            updates = {
                "processo_numero": novo_numero,
                "id_servidor_responsavel": selected_serv_id,
                "id_tipo_produto": produtos_dict[novo_produto_nome],
                "id_procurador": procuradores_dict.get(novo_procurador_nome) if procuradores_nomes and novo_procurador_nome != "Nenhum procurador disponível" else processo.get('id_procurador'),
                "id_chefe_gabinete": chefes_dict.get(novo_chefe_nome) if chefes_nomes and novo_chefe_nome != "Nenhum chefe disponível" else processo.get('id_chefe_gabinete'),
                "observacao_chefe": observacao_chefe,
                "data_atribuicao_servidor": data_atribuicao.isoformat() if data_atribuicao else None,
                "data_conclusao_servidor": data_conclusao_servidor.isoformat() if data_conclusao_servidor else None,
                "data_conclusao_chefe": data_conclusao_chefe.isoformat() if data_conclusao_chefe else None,
                "nao_se_aplica_prazo_servidor": nao_se_aplica_prazo_servidor,
                "ignorar_revisao_chefe": ignorar_revisao_chefe,
                "ignorar_analise_procurador": ignorar_analise_procurador
            }
            
            # Detectar mudança de servidor e registrar histórico
            if old_serv_id != selected_serv_id:
                hoje = today_brazil()
                
                old_serv_name = "Nenhum"
                if old_serv_id:
                    old_u = get_user_by_id(old_serv_id)
                    if old_u:
                        old_serv_name = old_u.get('nome_completo', 'Desconhecido')
                
                # Calcular dias com o servidor anterior
                dias_com_anterior = ""
                dt_atrib_old = processo.get('data_atribuicao_servidor')
                if dt_atrib_old:
                    if isinstance(dt_atrib_old, str):
                        dt_atrib_old = date.fromisoformat(dt_atrib_old)
                    dias = (hoje - dt_atrib_old).days
                    dias_com_anterior = f" ({dias} dia{'s' if dias != 1 else ''} com o processo)"
                
                # Fechar vínculo antigo e registrar novo
                fechar_vinculo_servidor(pid, hoje)
                registrar_vinculo_servidor(pid, selected_serv_id, hoje)
                
                # Resetar prazo do servidor
                updates['data_atribuicao_servidor'] = hoje.isoformat()
                updates['data_conclusao_servidor'] = None
                updates['status_servidor'] = 'No Prazo'
                updates['prazo_customizado'] = False
                
                obs_hist = f"Servidor alterado de {old_serv_name}{dias_com_anterior} para {novo_servidor_nome}. Prazo reiniciado."
                add_process_history(pid, "Servidor Responsável Alterado", st.session_state.active_user_id, obs_hist)
            
            update_process(pid, updates)
            st.success("Processo atualizado com sucesso!")
            del st.session_state['processo_para_editar_admin_id']
            st.rerun()
        
        if cancelar_btn:
            del st.session_state['processo_para_editar_admin_id']
            st.rerun()

    st.markdown("---")
    st.subheader("🗓️ Gerenciar Prazos")
    
    prazo_status = processo.get('prazo_status')
    prazo_susp_em = parse_date_val(processo.get('prazo_suspenso_em'))
    
    if prazo_status == 'Suspenso':
        st.info(f"Prazo suspenso desde: {prazo_susp_em.strftime('%d/%m/%Y') if prazo_susp_em else 'data não registrada'}")
        with st.form("admin_reiniciar_prazo_form"):
            data_reinicio = st.date_input("Data de Reinício da Contagem", value=today_brazil())
            reiniciar_btn = st.form_submit_button("Registrar Reinício do Prazo")
            
            if reiniciar_btn:
                if prazo_susp_em and data_reinicio > prazo_susp_em:
                    data_fim_suspensao = data_reinicio - timedelta(days=1)
                    # count business days
                    dias_suspensos = count_business_days(prazo_susp_em, data_fim_suspensao)
                    
                    curr_total_susp = processo.get('prazo_total_dias_suspenso', 0) or 0
                    
                    upd_prazo = {
                        "prazo_total_dias_suspenso": curr_total_susp + dias_suspensos,
                        "prazo_status": 'Ativo',
                        "prazo_suspenso_em": None
                    }
                    
                    update_process(pid, upd_prazo)
                    add_process_history(
                        pid, 
                        f"Prazo Reiniciado pelo Administrador", 
                        st.session_state.active_user_id,
                        f"Reiniciado em {data_reinicio.strftime('%d/%m/%Y')}. Total de dias suspensos: {dias_suspensos}."
                    )
                    
                    st.success(f"Prazo do processo reiniciado! {dias_suspensos} dia(s) de suspensão foram adicionados.")
                    st.rerun()
                else:
                    st.error("A data de reinício deve ser posterior à data de suspensão.")

    else:
        with st.form("admin_suspender_prazo_form"):
            data_suspensao = st.date_input("Data de Início da Suspensão", value=today_brazil())
            suspender_btn = st.form_submit_button("Registrar Suspensão do Prazo")

            if suspender_btn:
                upd_prazo = {
                    "prazo_status": 'Suspenso',
                    "prazo_suspenso_em": data_suspensao.isoformat()
                }
                update_process(pid, upd_prazo)
                
                add_process_history(
                    pid, 
                    "Prazo Suspenso pelo Administrador", 
                    st.session_state.active_user_id,
                    f"Suspenso a partir de {data_suspensao.strftime('%d/%m/%Y')}."
                )
                
                st.success("Prazo do processo suspenso!")
                st.rerun()

    st.markdown("---")
    st.subheader("🗑️ Deletar Registro")
    st.warning("Atenção: A exclusão de um registro é permanente e não pode ser desfeita.")
    
    if f"confirm_delete_{pid}" not in st.session_state:
        st.session_state[f"confirm_delete_{pid}"] = False

    def toggle_confirm():
        st.session_state[f"confirm_delete_{pid}"] = not st.session_state[f"confirm_delete_{pid}"]

    st.checkbox("Sim, eu entendo e quero deletar este registro.", key=f"cb_{pid}", on_change=toggle_confirm)
    
    if st.button("Deletar Registro Permanentemente", disabled=(not st.session_state[f"confirm_delete_{pid}"])):
        # Fix #2: Deleção completa em cascata (mesma lógica de forms/processo.py)
        QueryBuilder("processo_historico").eq("id_processo", pid).delete()
        QueryBuilder("processo_servidor_historico").eq("id_processo", pid).delete()
        
        # Buscar e remover comentários e suas marcações de leitura
        comments = QueryBuilder("comentarios").eq("id_processo", pid).select("id").execute()
        if comments:
            comment_ids = [c['id'] for c in comments]
            for cid in comment_ids:
                QueryBuilder("comentario_lido").eq("id_comentario", cid).delete()
            QueryBuilder("comentarios").eq("id_processo", pid).delete()
        
        # Remover notificações e devoluções
        QueryBuilder("notificacoes").eq("id_processo", pid).delete()
        QueryBuilder("processo_devolucoes").eq("id_processo", pid).delete()

        delete_by_id("processos", pid)
        
        st.success("Registro deletado permanentemente!")
        # Fix #3: Chave correta do session_state
        if 'processo_para_editar_admin_id' in st.session_state:
            del st.session_state['processo_para_editar_admin_id']
        del st.session_state[f"confirm_delete_{pid}"]
        st.rerun()
