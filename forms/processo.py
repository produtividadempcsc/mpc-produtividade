
import streamlit as st
from datetime import date, timedelta
from supabase_client import QueryBuilder, select_all, delete_by_id
from db_compat import (
    get_process_by_id, get_user_by_id, get_product_type_by_id,
    add_process_history, count_business_days, update_process
)
from utils.common import get_servidor_status
from utils.ui import display_process_history

def display_edit_processo_form(processo_id):
    st.header("✏️ Editando Processo")
    
    # Busca processo via Supabase
    processo = get_process_by_id(processo_id)
    if not processo:
        st.error("Processo não encontrado.")
        if 'processo_para_editar_id' in st.session_state:
            del st.session_state['processo_para_editar_id']
        st.button("Voltar ao Dashboard")
        return

    # Helper para acessar campos (já que processo é dict)
    p_num = processo.get('processo_numero')
    pid = processo.get('id')

    # Formulário principal para edição
    with st.form("edit_form"):
        st.info(f"Editando o processo **{p_num}**.")
        
        # --- Lógica de Servidores ---
        # Buscar Servidores Ativos
        # Buscar Servidores Ativos e Chefes de Gabinete (pois chefe pode assumir processo)
        servidores = QueryBuilder("usuarios").in_list("perfil", ["Servidor", "Chefe de Gabinete"]).eq("ativo", True).order("nome_completo").execute()
        servidores_dict = {s['nome_completo']: s['id'] for s in servidores}
        servidores_nomes = list(servidores_dict.keys())
        
        current_servidor_index = 0
        sid = processo.get('id_servidor_responsavel')
        if sid:
            # Tenta achar o nome no dict carregado
            found_name = next((name for name, i in servidores_dict.items() if i == sid), None)
            if not found_name:
                # Se não achou (ex: inativo ou outro perfil), busca individualmente
                s_atual = get_user_by_id(sid)
                if s_atual:
                    s_name = s_atual.get('nome_completo')
                    servidores_dict[s_name] = sid
                    servidores_nomes.append(s_name)
                    servidores_nomes.sort()
                    found_name = s_name
            
            if found_name:
                current_servidor_index = servidores_nomes.index(found_name)

        # --- Lógica de Produtos ---
        # Buscar Tipos de Produto (group by nome not native easy, fetching all simple list)
        produtos = select_all("tipos_produto") 
        produtos.sort(key=lambda x: x.get('nome_produto', ''))
        produtos_dict = {p['nome_produto']: p['id'] for p in produtos} 
        produtos_nomes = list(produtos_dict.keys())
        
        tid = processo.get('id_tipo_produto')
        current_produto_index = 0
        if tid:
            # Find name for tid
            curr_prod = next((p for p in produtos if p['id'] == tid), None)
            if curr_prod:
                p_name = curr_prod.get('nome_produto')
                if p_name in produtos_nomes:
                    current_produto_index = produtos_nomes.index(p_name)
        
        # --- Lógica de Procuradores ---
        procuradores = QueryBuilder("usuarios").eq("perfil", "Procurador").eq("ativo", True).order("nome_completo").execute()
        procuradores_dict = {p['nome_completo']: p['id'] for p in procuradores}
        procuradores_nomes = list(procuradores_dict.keys())
        
        proc_id_val = processo.get('id_procurador')
        current_procurador_index = 0
        if proc_id_val:
             found_name = next((name for name, i in procuradores_dict.items() if i == proc_id_val), None)
             if found_name:
                 current_procurador_index = procuradores_nomes.index(found_name)

        # --- Lógica de Chefes de Gabinete ---
        chefes = QueryBuilder("usuarios").eq("perfil", "Chefe de Gabinete").eq("ativo", True).order("nome_completo").execute()
        chefes_dict = {c['nome_completo']: c['id'] for c in chefes}
        chefes_nomes = list(chefes_dict.keys())
        
        cid_val = processo.get('id_chefe_gabinete')
        current_chefe_index = 0
        if cid_val:
             found_name = next((name for name, i in chefes_dict.items() if i == cid_val), None)
             if found_name:
                 current_chefe_index = chefes_nomes.index(found_name)

        # --- Layout do Formulário ---
        col1, col2 = st.columns(2)
        with col1:
            novo_numero = st.text_input("Número do Processo", value=p_num)
            novo_servidor_nome = st.selectbox("Servidor Responsável", options=servidores_nomes, index=current_servidor_index)
            novo_chefe_nome = st.selectbox("Chefe de Gabinete", options=chefes_nomes, index=current_chefe_index)
            
        with col2:
            novo_produto_nome = st.selectbox("Tipo de Produto", options=produtos_nomes, index=current_produto_index)
            novo_procurador_nome = st.selectbox("Procurador Vinculado", options=procuradores_nomes, index=current_procurador_index)
        
        prioridades = ['Regular', 'Prioritário', 'Urgente']
        p_prio = processo.get('prioridade')
        prioridade_atual_index = prioridades.index(p_prio) if p_prio in prioridades else 0
        prioridade = st.selectbox("Prioridade", options=prioridades, index=prioridade_atual_index)

        observacao_chefe = st.text_area("Observações do Gabinete", value=processo.get('observacao_chefe') or "")

        # Ações administrativas
        finalizar_processo_check = False
        status_chefe = processo.get('status_chefe')
        if st.session_state.active_perfil in ["Chefe de Gabinete", "Procurador", "Administrador"]:
            st.markdown("---")
            st.warning("Ação Administrativa")
            finalizar_processo_check = st.checkbox(
                "Marcar como Finalizado",
                value=(status_chefe == "Finalizado")
            )

        # Edição de datas
        st.markdown("---")
        
        def parse_date_val(d):
            if isinstance(d, str): return date.fromisoformat(d)
            return d

        dt_atrib_val = parse_date_val(processo.get('data_atribuicao_servidor'))
        dt_conc_serv_val = parse_date_val(processo.get('data_conclusao_servidor'))
        dt_conc_chefe_val = parse_date_val(processo.get('data_conclusao_chefe'))

        if st.session_state.active_perfil in ["Chefe de Gabinete", "Procurador", "Administrador"]:
            st.subheader("Edição de Datas")
            col_data1, col_data2, col_data3 = st.columns(3)
            with col_data1:
                data_atribuicao = st.date_input("Data de Atribuição", value=dt_atrib_val, format="DD/MM/YYYY")
            with col_data2:
                data_conclusao_servidor = st.date_input("Data de Conclusão (Servidor)", value=dt_conc_serv_val, format="DD/MM/YYYY")
            with col_data3:
                data_conclusao_chefe = st.date_input("Data de Revisão", value=dt_conc_chefe_val, format="DD/MM/YYYY")
        else:
            data_atribuicao = st.date_input("Data de Atribuição", value=dt_atrib_val, format="DD/MM/YYYY")
            data_conclusao_servidor = dt_conc_serv_val
            data_conclusao_chefe = dt_conc_chefe_val
        st.markdown("---")

        st.write("Opções de Exceção:")
        col1_check, col2_check, col3_check = st.columns(3)
        with col1_check:
            nao_se_aplica_prazo_servidor = st.checkbox("Não se aplica prazo ao Servidor", value=processo.get('nao_se_aplica_prazo_servidor', False))
        with col2_check:
            ignorar_revisao_chefe = st.checkbox("Ignorar etapa de Revisão (Chefe de Gabinete)", value=processo.get('ignorar_revisao_chefe', False))
        with col3_check:
            ignorar_analise_procurador = st.checkbox("Ignorar etapa de Análise (Procurador)", value=processo.get('ignorar_analise_procurador', False))

        # Campos de Prazo MPC
        st.markdown("---")
        st.subheader("📆 Prazo do Setor MPC")
        dt_entrada_mpc_val = parse_date_val(processo.get('data_entrada_mpc'))
        col_mpc1, col_mpc2 = st.columns(2)
        with col_mpc1:
            data_entrada_mpc = st.date_input(
                "Data de Entrada no MPC", 
                value=dt_entrada_mpc_val, 
                format="DD/MM/YYYY",
                help="Data em que o processo chegou ao MPC. Deixe vazio se não se aplica."
            )
        with col_mpc2:
            prazo_mpc_dias = st.number_input(
                "Prazo MPC (dias corridos)", 
                min_value=0, 
                value=processo.get('prazo_mpc_dias') or 0,
                help="Prazo total em dias corridos para o processo ser finalizado pelo setor MPC. 0 = Não se aplica."
            )

        salvar_btn = st.form_submit_button("Salvar Alterações")
        cancelar_btn = st.form_submit_button("Cancelar Edição")


        if salvar_btn:
            updates = {}
            
            selected_prod_id = produtos_dict[novo_produto_nome]
            selected_serv_id = servidores_dict[novo_servidor_nome]
            selected_chefe_id = chefes_dict[novo_chefe_nome]
            selected_proc_id = procuradores_dict[novo_procurador_nome]

            updates['processo_numero'] = novo_numero
            updates['id_servidor_responsavel'] = selected_serv_id
            updates['id_chefe_gabinete'] = selected_chefe_id
            updates['id_tipo_produto'] = selected_prod_id
            updates['id_procurador'] = selected_proc_id
            updates['prioridade'] = prioridade
            updates['observacao_chefe'] = observacao_chefe
            updates['nao_se_aplica_prazo_servidor'] = nao_se_aplica_prazo_servidor
            updates['ignorar_revisao_chefe'] = ignorar_revisao_chefe
            updates['ignorar_analise_procurador'] = ignorar_analise_procurador
            
            # Campos de Prazo MPC
            updates['data_entrada_mpc'] = data_entrada_mpc.isoformat() if data_entrada_mpc else None
            updates['prazo_mpc_dias'] = prazo_mpc_dias if prazo_mpc_dias > 0 else None
            # Calcular status_mpc baseado nos novos valores
            if not data_entrada_mpc or prazo_mpc_dias == 0:
                updates['status_mpc'] = "Não se aplica"
            else:
                from utils.common import get_mpc_status
                temp_proc = processo.copy()
                temp_proc['data_entrada_mpc'] = data_entrada_mpc
                temp_proc['prazo_mpc_dias'] = prazo_mpc_dias
                new_status_mpc, _ = get_mpc_status(temp_proc)
                updates['status_mpc'] = new_status_mpc
            
            updates['data_atribuicao_servidor'] = data_atribuicao.isoformat() if data_atribuicao else None
            
            produto_selecionado = get_product_type_by_id(selected_prod_id)
            if produto_selecionado:
                updates['prazo_servidor_aplicado'] = produto_selecionado.get('prazo_servidor')
                updates['prazo_chefe_aplicado'] = produto_selecionado.get('prazo_chefe')
            
            if st.session_state.active_perfil in ["Chefe de Gabinete", "Procurador", "Administrador"]:
                updates['data_conclusao_servidor'] = data_conclusao_servidor.isoformat() if data_conclusao_servidor else None
                updates['data_conclusao_chefe'] = data_conclusao_chefe.isoformat() if data_conclusao_chefe else None
            
            was_finalizado = status_chefe == "Finalizado"

            old_data_servidor = dt_conc_serv_val
            old_data_chefe = dt_conc_chefe_val
            
            if finalizar_processo_check:
                if not was_finalizado:
                    updates['status_servidor'] = "Finalizado"
                    updates['status_chefe'] = "Finalizado"
                    evento = "Processo Finalizado"
                    if st.session_state.active_perfil == "Procurador":
                        evento = "Processo Aprovado pelo Procurador"
                    add_process_history(pid, evento, st.session_state.active_user_id)
            else:
                if was_finalizado:
                    evento = "Finalização do processo revertida"
                    add_process_history(pid, evento, st.session_state.active_user_id)
                    
                    dc_chefe = data_conclusao_chefe
                    dc_serv = data_conclusao_servidor
                    
                    if dc_chefe:
                        updates['status_servidor'] = "Concluído"
                        updates['status_chefe'] = "Processo com o Procurador"
                    elif dc_serv:
                        updates['status_servidor'] = "Concluído"
                        updates['status_chefe'] = "Aguardando Análise"
                    else:
                        temp_proc = processo.copy()
                        temp_proc.update(updates)
                        temp_proc['data_conclusao_servidor'] = None
                        temp_proc['data_conclusao_chefe'] = None
                        temp_proc['data_atribuicao_servidor'] = data_atribuicao.isoformat() if data_atribuicao else None
                        
                        updates['status_servidor'] = get_servidor_status(temp_proc)
                        updates['status_chefe'] = None

            new_dc_chefe = data_conclusao_chefe
            new_dc_serv = data_conclusao_servidor
            
            # --- HISTÓRICO DE ALTERAÇÕES DE VÍNCULO ---
            # 1. Servidor
            old_serv_id = processo.get('id_servidor_responsavel')
            if old_serv_id != selected_serv_id:
                old_serv_name = "Nenhum"
                if old_serv_id:
                    # Tenta pegar do dict primeiro se possível (se estava na lista original)
                    # Mas como o dict é Nome->ID, teríamos que inverter ou buscar.
                    # Vamos buscar direto para garantir o nome correto antigo.
                    old_u = get_user_by_id(old_serv_id)
                    if old_u: 
                        old_serv_name = old_u.get('nome_completo', 'Desconhecido')
                add_process_history(pid, f"Servidor alterado de {old_serv_name} para {novo_servidor_nome}", st.session_state.active_user_id)

            # 2. Chefe de Gabinete
            old_chefe_id = processo.get('id_chefe_gabinete')
            if old_chefe_id != selected_chefe_id:
                old_chefe_name = "Nenhum"
                if old_chefe_id:
                    old_u = get_user_by_id(old_chefe_id)
                    if old_u:
                        old_chefe_name = old_u.get('nome_completo', 'Desconhecido')
                add_process_history(pid, f"Chefe de Gabinete alterado de {old_chefe_name} para {novo_chefe_nome}", st.session_state.active_user_id)

            # 3. Procurador
            old_proc_id = processo.get('id_procurador')
            if old_proc_id != selected_proc_id:
                old_proc_name = "Nenhum"
                if old_proc_id:
                    old_u = get_user_by_id(old_proc_id)
                    if old_u:
                        old_proc_name = old_u.get('nome_completo', 'Desconhecido')
                add_process_history(pid, f"Procurador alterado de {old_proc_name} para {novo_procurador_nome}", st.session_state.active_user_id)

            # --- ATUALIZAÇÃO DE STATUS BASEADA NAS DATAS (sem ser finalização) ---
            # Isso garante que o processo se mova entre as páginas corretamente
            if not finalizar_processo_check and not was_finalizado:
                # Caso 1: Data de revisão do chefe foi preenchida
                if new_dc_chefe and not old_data_chefe:
                    # Chefe revisou -> vai para o procurador
                    updates['status_servidor'] = "Concluído"
                    updates['status_chefe'] = "Processo com o Procurador"
                # Caso 2: Data de conclusão do servidor foi preenchida (but without chefe review)
                elif new_dc_serv and not old_data_servidor and not new_dc_chefe:
                    # Servidor concluiu -> vai para revisão do chefe
                    updates['status_servidor'] = "Concluído"
                    updates['status_chefe'] = "Aguardando Análise"
                # Caso 3: Data de revisão do chefe foi removida
                elif old_data_chefe and not new_dc_chefe:
                    if new_dc_serv:
                        # Se ainda tem conclusão do servidor, volta para revisão
                        updates['status_servidor'] = "Concluído"
                        updates['status_chefe'] = "Aguardando Análise"
                    else:
                        # Se não tem nenhuma data, recalcula status do servidor
                        temp_proc = processo.copy()
                        temp_proc.update(updates)
                        temp_proc['data_conclusao_servidor'] = None
                        temp_proc['data_conclusao_chefe'] = None
                        temp_proc['data_atribuicao_servidor'] = data_atribuicao.isoformat() if data_atribuicao else None
                        updates['status_servidor'] = get_servidor_status(temp_proc)
                        updates['status_chefe'] = "Aguardando Análise"
                # Caso 4: Data de conclusão do servidor foi removida
                elif old_data_servidor and not new_dc_serv:
                    # Volta para o servidor trabalhar
                    temp_proc = processo.copy()
                    temp_proc.update(updates)
                    temp_proc['data_conclusao_servidor'] = None
                    temp_proc['data_conclusao_chefe'] = None
                    temp_proc['data_atribuicao_servidor'] = data_atribuicao.isoformat() if data_atribuicao else None
                    updates['status_servidor'] = get_servidor_status(temp_proc)
                    updates['status_chefe'] = "Aguardando Análise"
            
            # --- HISTÓRICO DE ALTERAÇÕES DE DATA ---
            if old_data_chefe and not new_dc_chefe:
                add_process_history(pid, "Data de revisão do chefe removida", st.session_state.active_user_id)
            elif not old_data_chefe and new_dc_chefe:
                add_process_history(pid, "Data de revisão do chefe registrada", st.session_state.active_user_id)
            
            if old_data_servidor and not new_dc_serv:
                add_process_history(pid, "Data de conclusão do servidor removida", st.session_state.active_user_id)
            elif not old_data_servidor and new_dc_serv:
                 add_process_history(pid, "Data de conclusão do servidor registrada", st.session_state.active_user_id)

            update_process(pid, updates)
            
            st.success("Processo atualizado!")
            del st.session_state['processo_para_editar_id']
            st.rerun()

        if cancelar_btn:
            del st.session_state['processo_para_editar_id']
            st.rerun()


    st.markdown("---")
    if st.toggle("Mostrar Histórico do Processo"):
        display_process_history(processo)

    st.markdown("---")
    if st.session_state.active_perfil in ["Chefe de Gabinete", "Procurador", "Administrador"]:
        st.subheader("🗓️ Gerenciar Prazos")
        
        prazo_status = processo.get('prazo_status')
        prazo_susp_em = parse_date_val(processo.get('prazo_suspenso_em'))
        
        if prazo_status == 'Suspenso':
            st.info(f"Prazo suspenso desde: {prazo_susp_em.strftime('%d/%m/%Y') if prazo_susp_em else 'data não registrada'}")
            with st.form("reiniciar_prazo_form"):
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
                            "Prazo Reiniciado", 
                            st.session_state.active_user_id,
                            f"Reiniciado em {data_reinicio.strftime('%d/%m/%Y')}. Total de dias suspensos: {dias_suspensos}."
                        )
                        
                        st.success(f"Prazo do processo reiniciado! {dias_suspensos} dia(s) de suspensão foram adicionados.")
                        st.rerun()
                    else:
                        st.error("A data de reinício deve ser posterior à data de suspensão.")

        else:
            with st.form("suspender_prazo_form"):
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
                        "Prazo Suspenso", 
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
