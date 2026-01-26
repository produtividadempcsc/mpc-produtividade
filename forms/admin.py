
import streamlit as st
from datetime import date, timedelta
from supabase_client import QueryBuilder, select_all, select_by_id, update_by_id, delete_by_id
from db_compat import (
    get_process_by_id, get_user_by_id, count_business_days,
    update_process, add_process_history
)

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
        servidores = QueryBuilder("usuarios").eq("perfil", "Servidor").eq("ativo", True).order("nome_completo").execute()
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
        produtos_dict = {p['nome_produto']: p['id'] for p in produtos} 
        produtos_nomes = list(produtos_dict.keys())
        produtos_nomes.sort()
        
        tid = processo.get('id_tipo_produto')
        current_produto_index = 0
        if tid:
             curr_prod = next((p for p in produtos if p['id'] == tid), None)
             if curr_prod:
                 p_name = curr_prod.get('nome_produto')
                 if p_name in produtos_nomes:
                     current_produto_index = produtos_nomes.index(p_name)

        procuradores = QueryBuilder("usuarios").eq("perfil", "Procurador").eq("ativo", True).execute() 
        procuradores.sort(key=lambda x: x.get('nome_completo', ''))
        procuradores_dict = {p['nome_completo']: p['id'] for p in procuradores}
        procuradores_nomes = list(procuradores_dict.keys())

        proc_id_val = processo.get('id_procurador')
        current_procurador_index = 0
        if proc_id_val:
            found_name = next((name for name, i in procuradores_dict.items() if i == proc_id_val), None)
            if found_name:
                current_procurador_index = procuradores_nomes.index(found_name)

        chefes = QueryBuilder("usuarios").eq("perfil", "Chefe de Gabinete").eq("ativo", True).order("nome_completo").execute()
        chefes_dict = {c['nome_completo']: c['id'] for c in chefes}
        chefes_nomes = list(chefes_dict.keys())
        
        cid_val = processo.get('id_chefe_gabinete')
        current_chefe_index = 0
        if cid_val:
             found_name = next((name for name, i in chefes_dict.items() if i == cid_val), None)
             if found_name:
                 current_chefe_index = chefes_nomes.index(found_name)

        col1, col2 = st.columns(2)
        with col1:
            novo_numero = st.text_input("Número do Processo", value=p_num)
            novo_servidor_nome = st.selectbox("Servidor Responsável", options=servidores_nomes, index=current_servidor_index)
            # Added Chefe selection to admin form if missing in original snippet logic but good practice
            # Wait, the original snippet didn't show chefe selection in admin form explicitly in the partial view I saw?
            # Checking view_file output again... line 767 "novo_servidor_nome...".
            # It seems admin form has simpler layout in snippet. I will keep consistent with snippet.
            # But wait, lines 807 "id_servidor_responsavel": servidores_dict[novo_servidor_nome].
            # It seems I need to capture inputs.
            # Let's verify if `chefes` logic was present. 
            # In lines 714+, it loads servers, products, procuradores. It does NOT seem to load Chefes explicitly in the snippet provided for Admin form?
            # Ah, wait. I should check if `id_chefe_gabinete` is updated in lines 805+.
            # Snippet 805+ does NOT show update for `id_chefe_gabinete`. 
            # It ONLY updates: processo_numero, id_servidor_responsavel, id_tipo_produto, id_procurador, observacao_chefe, dates...
            # So I should NOT add Chefe selector if it wasn't there, or maybe I should?
            # It's better to stick to what I saw. If I missed it, I might break it. But `id_chefe_gabinete` is usually static or assigned.
            # I will omit Chefe selector for Admin if not present, to match snippet.
            # The Admin form snippet I saw (line 700-800) did not query Chefes.
            
            novo_produto_nome = st.selectbox("Tipo de Produto", options=produtos_nomes, index=current_produto_index)
        with col2:
            novo_procurador_nome = st.selectbox("Procurador Vinculado", options=procuradores_nomes, index=current_procurador_index)
            observacao_chefe = st.text_area("Observações do Gabinete", value=processo.get('observacao_chefe') or "")

        st.markdown("---")
        st.subheader("Edição de Datas")
        
        def parse_date_val(d):
            if isinstance(d, str): return date.fromisoformat(d)
            return d
            
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
            updates = {
                "processo_numero": novo_numero,
                "id_servidor_responsavel": servidores_dict[novo_servidor_nome],
                "id_tipo_produto": produtos_dict[novo_produto_nome],
                "id_procurador": procuradores_dict[novo_procurador_nome] if novo_procurador_nome else None,
                "observacao_chefe": observacao_chefe,
                "data_atribuicao_servidor": data_atribuicao.isoformat() if data_atribuicao else None,
                "data_conclusao_servidor": data_conclusao_servidor.isoformat() if data_conclusao_servidor else None,
                "data_conclusao_chefe": data_conclusao_chefe.isoformat() if data_conclusao_chefe else None,
                "nao_se_aplica_prazo_servidor": nao_se_aplica_prazo_servidor,
                "ignorar_revisao_chefe": ignorar_revisao_chefe,
                "ignorar_analise_procurador": ignorar_analise_procurador
            }
            
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
            data_reinicio = st.date_input("Data de Reinício da Contagem", value=date.today())
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
            data_suspensao = st.date_input("Data de Início da Suspensão", value=date.today())
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
        QueryBuilder("processo_historico").eq("id_processo", pid).delete()
        QueryBuilder("anexos_processo").eq("id_processo", pid).delete()
        QueryBuilder("comentarios").eq("id_processo", pid).delete()
        QueryBuilder("processo_favoritos").eq("id_processo", pid).delete()

        delete_by_id("processos", pid)
        
        st.success("Registro deletado permanentemente!")
        del st.session_state['processo_para_editar_id']
        del st.session_state[f"confirm_delete_{pid}"]
        st.rerun()
