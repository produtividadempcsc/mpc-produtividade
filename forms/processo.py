
import streamlit as st
from datetime import date, timedelta
from utils.timezone import today_brazil
from supabase_client import QueryBuilder, select_all, delete_by_id, insert
from db_compat import (
    get_process_by_id, get_user_by_id, get_product_type_by_id,
    add_process_history, update_process,
    registrar_vinculo_servidor, fechar_vinculo_servidor
)
from services.prazo_service import count_business_days
from utils.common import get_servidor_status, parse_date_val
from utils.ui import display_process_history
import utils.notifications as notif_utils
import ui_utils

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

    p_num = processo.get('processo_numero')
    pid = processo.get('id')

    # Formulário principal para edição
    with st.form("edit_form"):
        st.info(f"Editando o processo **{p_num}**.")
        
        # --- Buscar Servidores Ativos e Chefes de Gabinete (chefe pode assumir processo) ---
        servidores = QueryBuilder("usuarios").in_list("perfil", ["Servidor", "Chefe de Gabinete"]).eq("ativo", True).order("nome_completo").execute()
        servidores_dict = {s['nome_completo']: s['id'] for s in servidores}
        servidores_nomes = list(servidores_dict.keys())
        
        current_servidor_index = 0
        sid = processo.get('id_servidor_responsavel')
        if sid:
            found_name = next((name for name, i in servidores_dict.items() if i == sid), None)
            if not found_name:
                # Servidor inativo ou de outro perfil — buscar individualmente
                s_atual = get_user_by_id(sid)
                if s_atual:
                    s_name = s_atual.get('nome_completo')
                    servidores_dict[s_name] = sid
                    servidores_nomes.append(s_name)
                    servidores_nomes.sort()
                    found_name = s_name
            
            if found_name:
                current_servidor_index = servidores_nomes.index(found_name)

        # --- Buscar Tipos de Produto ---
        # Fix #19: Usar ID como chave interna para evitar sobrescrita de versões com mesmo nome
        produtos = select_all("tipos_produto") 
        produtos.sort(key=lambda x: x.get('nome_produto', ''))
        # Para o selectbox, usar nome_produto (usuário vê o nome),
        # mas manter mapeamento por índice para pegar o ID correto
        produtos_nomes_uniq = []
        produtos_id_map = {}
        seen_names = set()
        for p in produtos:
            pname = p['nome_produto']
            if pname not in seen_names:
                seen_names.add(pname)
                produtos_nomes_uniq.append(pname)
                produtos_id_map[pname] = p['id']
        produtos_nomes = produtos_nomes_uniq
        
        tid = processo.get('id_tipo_produto')
        current_produto_index = 0
        if tid:
            curr_prod = next((p for p in produtos if p['id'] == tid), None)
            if curr_prod:
                p_name = curr_prod.get('nome_produto')
                if p_name in produtos_nomes:
                    current_produto_index = produtos_nomes.index(p_name)
        
        # --- Buscar Procuradores (com tratamento de lista vazia) ---
        procuradores = QueryBuilder("usuarios").eq("perfil", "Procurador").eq("ativo", True).order("nome_completo").execute()
        procuradores_dict = {p['nome_completo']: p['id'] for p in procuradores}
        procuradores_nomes = list(procuradores_dict.keys())
        
        proc_id_val = processo.get('id_procurador')
        current_procurador_index = 0
        if proc_id_val:
            found_name = next((name for name, i in procuradores_dict.items() if i == proc_id_val), None)
            if not found_name:
                # Procurador inativo — buscar individualmente
                proc_atual = get_user_by_id(proc_id_val)
                if proc_atual:
                    proc_name = proc_atual.get('nome_completo')
                    procuradores_dict[proc_name] = proc_id_val
                    procuradores_nomes.append(proc_name)
                    procuradores_nomes.sort()
                    found_name = proc_name
            if found_name:
                current_procurador_index = procuradores_nomes.index(found_name)

        # --- Buscar Chefes de Gabinete (com tratamento de lista vazia) ---
        chefes = QueryBuilder("usuarios").eq("perfil", "Chefe de Gabinete").eq("ativo", True).order("nome_completo").execute()
        chefes_dict = {c['nome_completo']: c['id'] for c in chefes}
        chefes_nomes = list(chefes_dict.keys())
        
        cid_val = processo.get('id_chefe_gabinete')
        current_chefe_index = 0
        if cid_val:
            found_name = next((name for name, i in chefes_dict.items() if i == cid_val), None)
            if not found_name:
                # Chefe inativo — buscar individualmente
                chefe_atual = get_user_by_id(cid_val)
                if chefe_atual:
                    chefe_name = chefe_atual.get('nome_completo')
                    chefes_dict[chefe_name] = cid_val
                    chefes_nomes.append(chefe_name)
                    chefes_nomes.sort()
                    found_name = chefe_name
            if found_name:
                current_chefe_index = chefes_nomes.index(found_name)

        # --- Layout do Formulário em Cartões (Cards) ---
        st.write("") # Respiro inicial

        with st.container(border=True):
            st.subheader("📝 Dados Básicos")
            col_b1, col_b2, col_b3 = st.columns(3)
            with col_b1:
                novo_numero = st.text_input("Número do Processo", value=p_num)
            with col_b2:
                novo_produto_nome = st.selectbox("Tipo de Produto", options=produtos_nomes, index=current_produto_index)
            with col_b3:
                prioridades = ['Regular', 'Prioritário', 'Urgente']
                p_prio = processo.get('prioridade')
                prioridade_atual_index = prioridades.index(p_prio) if p_prio in prioridades else 0
                prioridade = st.selectbox("Prioridade", options=prioridades, index=prioridade_atual_index)

        with st.container(border=True):
            st.subheader("👥 Envolvidos")
            col_env1, col_env2 = st.columns(2)
            with col_env1:
                if servidores_nomes:
                    novo_servidor_nome = st.selectbox("👤 Servidor Responsável", options=servidores_nomes, index=current_servidor_index)
                else:
                    novo_servidor_nome = st.selectbox("👤 Servidor Responsável", options=["Nenhum servidor disponível"], disabled=True)
                
                if chefes_nomes:
                    novo_chefe_nome = st.selectbox("👔 Chefe de Gabinete", options=chefes_nomes, index=current_chefe_index)
                else:
                    novo_chefe_nome = st.selectbox("👔 Chefe de Gabinete", options=["Nenhum chefe disponível"], disabled=True)
            with col_env2:
                if procuradores_nomes:
                    novo_procurador_nome = st.selectbox("⚖️ Procurador Vinculado", options=procuradores_nomes, index=current_procurador_index)
                else:
                    novo_procurador_nome = st.selectbox("⚖️ Procurador Vinculado", options=["Nenhum procurador disponível"], disabled=True)
                
            observacao_chefe = st.text_area("📌 Observações do Gabinete", value=processo.get('observacao_chefe') or "", height=100)

        dt_atrib_val = parse_date_val(processo.get('data_atribuicao_servidor'))
        dt_conc_serv_val = parse_date_val(processo.get('data_conclusao_servidor'))
        dt_conc_chefe_val = parse_date_val(processo.get('data_conclusao_chefe'))

        with st.container(border=True):
            st.subheader("📅 Prazos e Datas")
            if st.session_state.active_perfil in ["Chefe de Gabinete", "Procurador", "Administrador"]:
                col_data1, col_data2, col_data3 = st.columns(3)
                with col_data1:
                    data_atribuicao = st.date_input("Data de Atribuição", value=dt_atrib_val, format="DD/MM/YYYY")
                with col_data2:
                    data_conclusao_servidor = st.date_input("Conclusão (Servidor)", value=dt_conc_serv_val, format="DD/MM/YYYY")
                with col_data3:
                    data_conclusao_chefe = st.date_input("Data de Revisão", value=dt_conc_chefe_val, format="DD/MM/YYYY")
            else:
                data_atribuicao = st.date_input("Data de Atribuição", value=dt_atrib_val, format="DD/MM/YYYY", disabled=True)
                data_conclusao_servidor = dt_conc_serv_val
                data_conclusao_chefe = dt_conc_chefe_val
                
            st.write("") # Respiro interno
            st.markdown("**Opções de Exceção de Prazo:**")
            col1_check, col2_check, col3_check = st.columns(3)
            with col1_check:
                nao_se_aplica_prazo_servidor = st.checkbox("Não se aplica ao Servidor", value=processo.get('nao_se_aplica_prazo_servidor', False))
            with col2_check:
                ignorar_revisao_chefe = st.checkbox("Ignorar Revisão (Chefe)", value=processo.get('ignorar_revisao_chefe', False))
            with col3_check:
                ignorar_analise_procurador = st.checkbox("Ignorar Análise (Procurador)", value=processo.get('ignorar_analise_procurador', False))

        with st.container(border=True):
            st.subheader("🏛️ Prazo do Setor MPC")
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

        # Ação administrativa: Finalizar processo
        finalizar_processo_check = False
        status_chefe = processo.get('status_chefe')
        if st.session_state.active_perfil in ["Chefe de Gabinete", "Procurador", "Administrador"]:
            with st.container(border=True):
                st.subheader("⚠️ Ações Administrativas")
                finalizar_processo_check = st.checkbox(
                    "Marcar Processo como Finalizado",
                    value=(status_chefe == "Finalizado")
                )
        st.write("") # Respiro antes dos botões

        st.markdown("""
            <style>
            div.element-container:has(.btn-salvar) + div.element-container button {
                background-color: #28a745 !important;
                color: white !important;
                border-color: #28a745 !important;
            }
            div.element-container:has(.btn-cancelar) + div.element-container button {
                background-color: #dc3545 !important;
                color: white !important;
                border-color: #dc3545 !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        col_btn1, col_btn2 = st.columns([1, 1])
        with col_btn1:
            st.markdown('<div class="btn-salvar"></div>', unsafe_allow_html=True)
            salvar_btn = st.form_submit_button("Salvar Alterações", use_container_width=True)
        with col_btn2:
            st.markdown('<div class="btn-cancelar"></div>', unsafe_allow_html=True)
            cancelar_btn = st.form_submit_button("Cancelar Edição", use_container_width=True)


        if salvar_btn:
            # Validação: verificar se as seleções são válidas (não são placeholders)
            if not servidores_nomes or novo_servidor_nome == "Nenhum servidor disponível":
                st.error("Não há servidores disponíveis para selecionar.")
                st.stop()
            if not procuradores_nomes or novo_procurador_nome == "Nenhum procurador disponível":
                st.error("Não há procuradores disponíveis para selecionar.")
                st.stop()
            if not chefes_nomes or novo_chefe_nome == "Nenhum chefe disponível":
                st.error("Não há chefes de gabinete disponíveis para selecionar.")
                st.stop()

            updates = {}
            
            selected_prod_id = produtos_id_map[novo_produto_nome]
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
                # Só sobrescrever prazo_servidor_aplicado se NÃO for prazo customizado (devolução)
                if not processo.get('prazo_customizado'):
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
            # 1. Servidor (só executa troca se NÃO estiver finalizando o processo)
            old_serv_id = processo.get('id_servidor_responsavel')
            if old_serv_id != selected_serv_id and not finalizar_processo_check:
                old_serv_name = "Nenhum"
                if old_serv_id:
                    old_u = get_user_by_id(old_serv_id)
                    if old_u: 
                        old_serv_name = old_u.get('nome_completo', 'Desconhecido')
                
                # Calcular dias com o servidor anterior
                hoje = today_brazil()
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
                
                # Resetar prazo do servidor: nova data de atribuição = hoje
                updates['data_atribuicao_servidor'] = hoje.isoformat()
                updates['data_conclusao_servidor'] = None
                updates['status_servidor'] = 'No Prazo'
                
                # Recalcular prazo_servidor_aplicado com base no tipo de produto
                if produto_selecionado:
                    updates['prazo_servidor_aplicado'] = produto_selecionado.get('prazo_servidor')
                    updates['prazo_customizado'] = False
                
                obs_hist = f"Servidor alterado de {old_serv_name}{dias_com_anterior} para {novo_servidor_nome}. Prazo reiniciado."
                add_process_history(pid, "Servidor Responsável Alterado", st.session_state.active_user_id, obs_hist)

                # Notificar o novo servidor por e-mail e notificação interna
                try:
                    from utils.timezone import now_brazil as _now_brazil
                    notificacao_data = {
                        "id_usuario_destino": selected_serv_id,
                        "mensagem": f"O processo '{p_num}' foi reatribuído a você.",
                        "lida": False,
                        "timestamp": _now_brazil().isoformat()
                    }
                    insert("notificacoes", notificacao_data)

                    novo_servidor_user = get_user_by_id(selected_serv_id)
                    if novo_servidor_user and novo_servidor_user.get('email') and novo_servidor_user.get('notifica_email_novo_processo'):
                        assunto = f"Processo Reatribuído: {p_num}"
                        corpo = f"""
                        <html><body>
                        <p>Olá {novo_servidor_user.get('nome_completo')},</p>
                        <p>O processo <b>{p_num}</b> foi reatribuído a você no sistema de produtividade.</p>
                        <p>Acesse o sistema para mais detalhes.</p>
                        </body></html>
                        """
                        notif_utils.send_email_notification(novo_servidor_user.get('email'), assunto, corpo)
                except Exception as e:
                    print(f"[NOTIFICAÇÃO] Erro ao notificar novo servidor: {e}")

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
            if not finalizar_processo_check and not was_finalizado:
                # Caso 1: Data de revisão do chefe foi preenchida
                if new_dc_chefe and not old_data_chefe:
                    updates['status_servidor'] = "Concluído"
                    updates['status_chefe'] = "Processo com o Procurador"
                # Caso 2: Data de conclusão do servidor foi preenchida (sem revisão do chefe)
                elif new_dc_serv and not old_data_servidor and not new_dc_chefe:
                    updates['status_servidor'] = "Concluído"
                    updates['status_chefe'] = "Aguardando Análise"
                # Caso 3: Data de revisão do chefe foi removida
                elif old_data_chefe and not new_dc_chefe:
                    if new_dc_serv:
                        updates['status_servidor'] = "Concluído"
                        updates['status_chefe'] = "Aguardando Análise"
                    else:
                        temp_proc = processo.copy()
                        temp_proc.update(updates)
                        temp_proc['data_conclusao_servidor'] = None
                        temp_proc['data_conclusao_chefe'] = None
                        temp_proc['data_atribuicao_servidor'] = data_atribuicao.isoformat() if data_atribuicao else None
                        updates['status_servidor'] = get_servidor_status(temp_proc)
                        updates['status_chefe'] = "Aguardando Análise"
                # Caso 4: Data de conclusão do servidor foi removida
                elif old_data_servidor and not new_dc_serv:
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
            
            ui_utils.set_success_feedback("Processo atualizado!")
            del st.session_state['processo_para_editar_id']
            st.rerun()

        if cancelar_btn:
            del st.session_state['processo_para_editar_id']
            st.rerun()


    st.write("")
    with st.expander("🕰️ Histórico do Processo"):
        display_process_history(processo)

    st.write("")
    if st.session_state.active_perfil in ["Chefe de Gabinete", "Procurador", "Administrador"]:
        with st.container(border=True):
            st.subheader("🗓️ Gerenciar Prazos")
            
        prazo_status = processo.get('prazo_status')
        prazo_susp_em = parse_date_val(processo.get('prazo_suspenso_em'))
        
        if prazo_status == 'Suspenso':
            st.info(f"Prazo suspenso desde: {prazo_susp_em.strftime('%d/%m/%Y') if prazo_susp_em else 'data não registrada'}")
            with st.form("reiniciar_prazo_form"):
                data_reinicio = st.date_input("Data de Reinício da Contagem", value=today_brazil())
                reiniciar_btn = st.form_submit_button("Registrar Reinício do Prazo")
                
                if reiniciar_btn:
                    if prazo_susp_em and data_reinicio > prazo_susp_em:
                        data_fim_suspensao = data_reinicio - timedelta(days=1)
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
                        
                        ui_utils.set_success_feedback(f"Prazo do processo reiniciado! {dias_suspensos} dia(s) de suspensão foram adicionados.")
                        st.rerun()
                    else:
                        st.error("A data de reinício deve ser posterior à data de suspensão.")

        else:
            with st.form("suspender_prazo_form"):
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
                        "Prazo Suspenso", 
                        st.session_state.active_user_id,
                        f"Suspenso a partir de {data_suspensao.strftime('%d/%m/%Y')}."
                    )
                    
                    ui_utils.set_success_feedback("Prazo do processo suspenso!")
                    st.rerun()

        st.write("")
        if f"confirm_delete_{pid}" not in st.session_state:
            st.session_state[f"confirm_delete_{pid}"] = False

        def toggle_confirm():
            st.session_state[f"confirm_delete_{pid}"] = not st.session_state[f"confirm_delete_{pid}"]

        with st.container(border=True):
            st.markdown("<h3 style='color: #dc3545;'>🚨 Zona de Perigo</h3>", unsafe_allow_html=True)
            st.error("Atenção: A exclusão de um registro é permanente e não pode ser desfeita. Todos os históricos, comentários e vínculos serão apagados.")
            
            st.checkbox("Sim, eu entendo e quero deletar este registro.", key=f"cb_{pid}", on_change=toggle_confirm)
            
            if st.button("Deletar Registro Permanentemente", disabled=(not st.session_state[f"confirm_delete_{pid}"])):
                # Limpar todos os dados dependentes antes de deletar
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
                ui_utils.set_success_feedback("Registro deletado permanentemente!", "warning")
                
                if 'processo_para_editar_id' in st.session_state:
                    del st.session_state['processo_para_editar_id']
                del st.session_state[f"confirm_delete_{pid}"]
                st.rerun()
