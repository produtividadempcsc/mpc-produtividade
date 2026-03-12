
from datetime import date, datetime
from supabase_client import QueryBuilder, select_all, update_by_id
from repositories.calendar_repository import is_business_day
from services.prazo_service import calculate_due_date
from utils.notifications import send_email_notification
from utils.timezone import today_brazil
from utils.common import get_mpc_status
from repositories.devolucao_repository import get_devolucoes_batch
from repositories.devolucao_procurador_chefe_repository import get_devolucoes_procurador_chefe_batch


def update_process_statuses():
    """
    Analisa todos os processos para garantir a integridade dos prazos aplicados e, em seguida,
    atualiza os status dos processos que ainda estão ativos.
    (Versão Supabase - OTIMIZADA com cache)
    """
    try:
        print(f"[{datetime.now()}] INICIANDO JOB de verificação de prazos e status (Supabase).")
        
        # =======================================================================
        # CACHE CENTRALIZADO - Carrega todos os dados necessários uma vez
        # =======================================================================
        todos_processos = select_all("processos")
        todos_produtos = select_all("tipos_produto")
        
        # Cache de produtos por ID
        produtos_por_id = {p['id']: p for p in todos_produtos}
        
        # Cache de produtos por nome (para get_correct_version)
        # Agrupa por nome e ordena por data_validade
        produtos_por_nome = {}
        for p in todos_produtos:
            nome = p.get('nome_produto')
            if nome not in produtos_por_nome:
                produtos_por_nome[nome] = []
            produtos_por_nome[nome].append(p)
        
        # Ordena cada grupo por data_validade
        for nome in produtos_por_nome:
            produtos_por_nome[nome].sort(key=lambda x: x.get('data_validade', '9999-12-31'))
        
        def get_correct_version_cached(original_product_id: int, reference_date):
            """Versão otimizada que usa cache em memória"""
            if not original_product_id or not reference_date:
                return None
            
            produto_original = produtos_por_id.get(original_product_id)
            if not produto_original:
                return None
            
            nome_produto = produto_original.get('nome_produto')
            versoes = produtos_por_nome.get(nome_produto, [])
            
            if not versoes:
                return None
            
            ref_date_str = reference_date.isoformat() if isinstance(reference_date, date) else reference_date
            
            # Buscar versão com data_validade >= reference_date
            for v in versoes:
                if v.get('data_validade', '9999-12-31') >= ref_date_str:
                    return v
            
            # Fallback: retornar a versão mais recente
            return versoes[-1] if versoes else None
        
        # --- ETAPA 1: CORREÇÃO DE INTEGRIDADE DOS PRAZOS ---
        print(f"[{datetime.now()}] ETAPA 1: Verificando integridade dos prazos...")
        prazo_updates_count = 0
        
        # Buscar devoluções ativas em batch para todos processos com prazo_customizado
        ids_customizados = [p['id'] for p in todos_processos if p.get('prazo_customizado')]
        devolucoes_ativas = get_devolucoes_batch(ids_customizados) if ids_customizados else {}

        for p in todos_processos:
            if not p.get('data_atribuicao_servidor') or not p.get('id_tipo_produto'):
                continue
            
            dt_atrib = p['data_atribuicao_servidor']
            if isinstance(dt_atrib, str):
                dt_atrib = date.fromisoformat(dt_atrib)

            produto_correto = get_correct_version_cached(p['id_tipo_produto'], dt_atrib)
            if not produto_correto:
                continue

            updates = {}
            
            # Só corrigir prazo_servidor_aplicado se NÃO for customizado E não tem devolução ativa
            has_active_dev = p['id'] in devolucoes_ativas
            if not p.get('prazo_customizado') and not has_active_dev and p.get('prazo_servidor_aplicado') != produto_correto['prazo_servidor']:
                updates['prazo_servidor_aplicado'] = produto_correto['prazo_servidor']
            
            if p.get('prazo_chefe_aplicado') != produto_correto['prazo_chefe']:
                updates['prazo_chefe_aplicado'] = produto_correto['prazo_chefe']
            
            if updates:
                print(f"[{datetime.now()}] CORREÇÃO DE PRAZO: Processo {p.get('processo_numero')} - {updates}")
                update_by_id("processos", p['id'], updates)
                p.update(updates)
                prazo_updates_count += 1
        
        if prazo_updates_count > 0:
            print(f"[{datetime.now()}] SUCESSO ETAPA 1: {prazo_updates_count} prazos corrigidos.")
        else:
            print(f"[{datetime.now()}] INFO ETAPA 1: Nenhum prazo precisou de correção.")

        # --- ETAPA 2: ATUALIZAÇÃO DE STATUS ---
        print(f"[{datetime.now()}] ETAPA 2: Atualizando status de processos ativos...")
        hoje = today_brazil()
        status_updates_count = 0

        # Sub-etapa 2.1: Servidor
        processos_servidor_ativos = [
            p for p in todos_processos 
            if p.get('status_servidor') in ["No Prazo", "Atrasado", "Devolvido"]
        ]
        
        for p in processos_servidor_ativos:
            # Usando cache em vez de query
            produto_obj = produtos_por_id.get(p['id_tipo_produto'])
            if not produto_obj: continue
            
            dt_atrib = p.get('data_atribuicao_servidor')
            if isinstance(dt_atrib, str): dt_atrib = date.fromisoformat(dt_atrib)
            
            # Usar dados da devolução ativa como fonte primária
            prazo_efetivo = p.get('prazo_servidor_aplicado')
            data_inicio_efetiva = dt_atrib
            
            dev = devolucoes_ativas.get(p['id'])
            if dev:
                prazo_efetivo = dev.get('prazo_dias', prazo_efetivo)
                dt_dev_str = dev.get('data_devolucao')
                if dt_dev_str:
                    data_inicio_efetiva = date.fromisoformat(dt_dev_str) if isinstance(dt_dev_str, str) else dt_dev_str
            
            data_final_servidor = calculate_due_date(
                start_date=data_inicio_efetiva,
                prazo_dias=prazo_efetivo,
                tipo_contagem=produto_obj.get('tipo_contagem_prazo'),
                id_usuario=p.get('id_servidor_responsavel'),
                dias_suspensos=p.get('prazo_total_dias_suspenso', 0),
                nao_se_aplica_prazo=p.get('nao_se_aplica_prazo_servidor', False)
            )

            original_status = p.get('status_servidor')
            novo_status = original_status

            if hoje > data_final_servidor:
                novo_status = "Atrasado"
            else:
                if original_status != "Devolvido":
                    novo_status = "No Prazo"
            
            updates = {}
            if novo_status != original_status:
                updates['status_servidor'] = novo_status
                status_updates_count += 1
                
            if novo_status != "Atrasado" and p.get('notificacao_atraso_enviada'):
                updates['notificacao_atraso_enviada'] = False
                
            if updates:
                update_by_id("processos", p['id'], updates)
                print(f"[{datetime.now()}] STATUS UPDATE (Servidor): Processo {p['id']} -> {updates}")

        # Sub-etapa 2.2: Chefe
        processos_chefe_ativos = [
            p for p in todos_processos
            if p.get('status_chefe') in ["Aguardando Análise", "Revisão Atrasada"]
        ]

        # Pre-fetch devolucoes procurador ativas
        processo_ids_chefe = [p['id'] for p in processos_chefe_ativos]
        devolucoes_procurador_ativas = get_devolucoes_procurador_chefe_batch(processo_ids_chefe)

        for p in processos_chefe_ativos:
            # Usando cache em vez de query
            produto_obj = produtos_por_id.get(p['id_tipo_produto'])
            if not produto_obj: continue
            
            pid = p['id']
            
            if pid in devolucoes_procurador_ativas:
                dt_base_str = devolucoes_procurador_ativas[pid]['data_devolucao']
            else:
                dt_atribuicao_chefe = p.get('data_atribuicao_chefe')
                dt_conclusao_serv = p.get('data_conclusao_servidor')
                dt_base_str = dt_atribuicao_chefe or dt_conclusao_serv
                
            if dt_base_str and isinstance(dt_base_str, str): dt_base_str = date.fromisoformat(str(dt_base_str)[:10])
            
            if not dt_base_str: continue 

            data_final_chefe = calculate_due_date(
                start_date=dt_base_str,
                prazo_dias=p.get('prazo_chefe_aplicado'),
                tipo_contagem=produto_obj.get('tipo_contagem_prazo'),
                id_usuario=p.get('id_chefe_gabinete'),
                dias_suspensos=p.get('prazo_total_dias_suspenso', 0)
            )

            original_status = p.get('status_chefe')
            novo_status = original_status

            if hoje > data_final_chefe:
                novo_status = "Revisão Atrasada"
            else:
                novo_status = "Aguardando Análise"

            updates = {}
            if novo_status != original_status:
                updates['status_chefe'] = novo_status
                status_updates_count += 1
            
            if novo_status != "Revisão Atrasada" and p.get('notificacao_atraso_enviada'):
                updates['notificacao_atraso_enviada'] = False

            if updates:
                update_by_id("processos", p['id'], updates)
                print(f"[{datetime.now()}] STATUS UPDATE (Chefe): Processo {p['id']} -> {updates}")

        # Sub-etapa 2.3: Status MPC
        print(f"[{datetime.now()}] Sub-etapa 2.3: Atualizando status MPC...")
        mpc_updates_count = 0
        
        # Filtrar processos que podem ter prazo MPC (não finalizados)
        processos_mpc = [
            p for p in todos_processos
            if p.get('status_chefe') != "Finalizado" and p.get('data_entrada_mpc') and p.get('prazo_mpc_dias')
        ]
        
        for p in processos_mpc:
            status_mpc_atual = p.get('status_mpc')
            novo_status_mpc, _ = get_mpc_status(p)
            
            if status_mpc_atual != novo_status_mpc:
                update_by_id("processos", p['id'], {'status_mpc': novo_status_mpc})
                print(f"[{datetime.now()}] STATUS UPDATE (MPC): Processo {p['id']} -> {novo_status_mpc}")
                mpc_updates_count += 1
        
        if mpc_updates_count > 0:
            print(f"[{datetime.now()}] Sub-etapa 2.3: {mpc_updates_count} status MPC atualizados.")

        print(f"[{datetime.now()}] JOB FINALIZADO. Total Updates: {status_updates_count + mpc_updates_count}")

    except Exception as e:
        print(f"[{datetime.now()}] ERRO NO JOB: {e}")


def initialize_restored_data():
    """
    Função a ser chamada após uma restauração de backup.
    Recalcula status e prazos para todos os processos.
    (Versão Supabase - Batch Update)
    """
    try:
        print("Iniciando pós-processamento dos dados restaurados...")
        
        todos_processos = select_all("processos")
        todos_produtos = select_all("tipos_produto")
        
        if not todos_processos:
            print("Nenhum processo para processar.")
            return

        produtos_map = {p['id']: p for p in todos_produtos}
        
        hoje = today_brazil()
        updates = []
        
        # Pre-fetch all active procurador devolucoes
        devolucoes_procurador_ativas = get_devolucoes_procurador_chefe_batch([p['id'] for p in todos_processos])

        for processo in todos_processos:
            updated_fields = {}
            pid = processo.get('id')
            prod_id = processo.get('id_tipo_produto')
            produto = produtos_map.get(prod_id)
            
            if not prod_id:
                if processo.get('status_servidor') != "Aguardando Definição":
                    updated_fields['status_servidor'] = "Aguardando Definição"
                if processo.get('status_chefe') != "Pendente":
                    updated_fields['status_chefe'] = "Pendente"
                
                if updated_fields:
                    updated_fields['id'] = pid
                    updates.append(updated_fields)
                continue

            if not produto:
                if processo.get('status_servidor') != "Erro de Vinculação":
                    updated_fields['status_servidor'] = "Erro de Vinculação"
                if processo.get('status_chefe') != "Pendente":
                    updated_fields['status_chefe'] = "Pendente"
                
                if updated_fields:
                    updated_fields['id'] = pid
                    updates.append(updated_fields)
                continue

            prazo_serv = processo.get('prazo_servidor_aplicado')
            prazo_chefe = processo.get('prazo_chefe_aplicado')
            
            if prazo_serv is None and not processo.get('prazo_customizado'):
                updated_fields['prazo_servidor_aplicado'] = produto.get('prazo_servidor')
                prazo_serv = produto.get('prazo_servidor')
                
            if prazo_chefe is None:
                updated_fields['prazo_chefe_aplicado'] = produto.get('prazo_chefe')
                prazo_chefe = produto.get('prazo_chefe')

            dt_concl_chefe = processo.get('data_conclusao_chefe')
            dt_concl_serv = processo.get('data_conclusao_servidor')
            dt_atrib_serv = processo.get('data_atribuicao_servidor')
            dt_atrib_chefe_str = processo.get('data_atribuicao_chefe')
            
            def parse_dt(d):
                if isinstance(d, str): return date.fromisoformat(d[:10])
                return d
            
            dt_concl_chefe = parse_dt(dt_concl_chefe)
            dt_concl_serv = parse_dt(dt_concl_serv)
            dt_atrib_serv = parse_dt(dt_atrib_serv)

            if dt_concl_chefe is not None and processo.get('status_chefe') not in ["Aguardando Análise", "Revisão Atrasada", "Processo com o Procurador"]:
                if processo.get('status_servidor') != "Finalizado":
                    updated_fields['status_servidor'] = "Finalizado"
                if processo.get('status_chefe') != "Finalizado":
                    updated_fields['status_chefe'] = "Finalizado"
                    
            elif dt_concl_serv is not None or dt_atrib_chefe_str:
                if processo.get('status_servidor') != "Concluído" and dt_concl_serv is not None:
                    updated_fields['status_servidor'] = "Concluído"
                
                pid = processo.get('id')
                # Usa devolução do procurador se houver
                if pid in devolucoes_procurador_ativas:
                    dt_base_chefe = date.fromisoformat(str(devolucoes_procurador_ativas[pid]['data_devolucao'])[:10])
                else:
                    dt_base_chefe = dt_atrib_chefe_str or dt_concl_serv
                    if isinstance(dt_base_chefe, str): dt_base_chefe = date.fromisoformat(str(dt_base_chefe)[:10])
                
                data_final_chefe = calculate_due_date(
                    start_date=dt_base_chefe,
                    prazo_dias=prazo_chefe,
                    tipo_contagem=produto.get('tipo_contagem_prazo'),
                    id_usuario=processo.get('id_chefe_gabinete'),
                    dias_suspensos=processo.get('prazo_total_dias_suspenso', 0)
                )
                
                new_status_chefe = "Aguardando Análise"
                if hoje > data_final_chefe:
                    new_status_chefe = "Revisão Atrasada"
                
                if processo.get('status_chefe') != new_status_chefe:
                    updated_fields['status_chefe'] = new_status_chefe
                    
            else:
                new_status_chefe = "Aguardando Análise"
                if processo.get('status_chefe') != "Aguardando Análise":
                    updated_fields['status_chefe'] = "Aguardando Análise"
                
                if dt_atrib_serv:
                    data_final_servidor = calculate_due_date(
                        start_date=dt_atrib_serv,
                        prazo_dias=prazo_serv,
                        tipo_contagem=produto.get('tipo_contagem_prazo'),
                        id_usuario=processo.get('id_servidor_responsavel'),
                        dias_suspensos=processo.get('prazo_total_dias_suspenso', 0),
                        nao_se_aplica_prazo=processo.get('nao_se_aplica_prazo_servidor', False)
                    )
                    
                    new_status_serv = "No Prazo"
                    if hoje > data_final_servidor:
                        new_status_serv = "Atrasado"
                    
                    if processo.get('status_servidor') != new_status_serv:
                        updated_fields['status_servidor'] = new_status_serv

            if updated_fields:
                updated_fields['id'] = pid
                updates.append(updated_fields)

        if updates:
            print(f"Atualizando {len(updates)} processos...")
            for update_dict in updates:
                pid = update_dict.pop('id')
                try:
                    update_by_id("processos", pid, update_dict)
                except Exception as e:
                    print(f"Error updating process {pid}: {e}")
        
        print(f"Pós-processamento concluído. {len(updates)} processos atualizados.")
        
    except Exception as e:
        print(f"ERRO durante a inicialização de dados restaurados: {e}")

def send_deadline_notifications():
    """
    Envia notificações por e-mail sobre prazos vencendo e processos atrasados.
    Apenas em dias úteis.
    (Versão Supabase)
    """
    try:
        hoje = today_brazil()
        # Adicionado verificação de dia útil
        if not is_business_day(hoje):
            print(f"INFO: Hoje não é um dia útil. Nenhuma notificação de prazo será enviada.")
            return

        processos = select_all("processos")
        
        processos_alvo = [
            p for p in processos 
            if p.get('status_servidor') in ["No Prazo", "Atrasado"] or 
               p.get('status_chefe') in ["Aguardando Análise", "Revisão Atrasada"]
        ]

        if not processos_alvo: return

        user_ids = set()
        type_ids = set()
        for p in processos_alvo:
            if p.get('id_servidor_responsavel'): user_ids.add(p['id_servidor_responsavel'])
            if p.get('id_chefe_gabinete'): user_ids.add(p['id_chefe_gabinete'])
            if p.get('id_tipo_produto'): type_ids.add(p['id_tipo_produto'])
        
        users_map = {}
        if user_ids:
            u_res = QueryBuilder("usuarios").in_list("id", list(user_ids)).execute()
            users_map = {u['id']: u for u in u_res}
            
        types_map = {}
        if type_ids:
            t_res = QueryBuilder("tipos_produto").in_list("id", list(type_ids)).execute()
            types_map = {t['id']: t for t in t_res}

        # Buscar devoluções ativas de processos com prazo customizado
        ids_custom_notif = [p.get('id') for p in processos_alvo if p.get('prazo_customizado')]
        devolucoes_ativas_notif = get_devolucoes_batch(ids_custom_notif) if ids_custom_notif else {}

        for p in processos_alvo:
            sid = p.get('id_servidor_responsavel')
            cid = p.get('id_chefe_gabinete')
            tid = p.get('id_tipo_produto')
            
            servidor = users_map.get(sid)
            chefe = users_map.get(cid)
            produto = types_map.get(tid)

            if not (servidor and servidor.get('email') and chefe and chefe.get('email') and produto):
                continue

            def parse_dt(d):
                if isinstance(d, str): return date.fromisoformat(d)
                return d
            
            dt_atrib = parse_dt(p.get('data_atribuicao_servidor'))
            dt_concl = parse_dt(p.get('data_conclusao_servidor'))

            # Usar dados da devolução ativa como fonte primária
            prazo_efetivo = p.get('prazo_servidor_aplicado')
            data_inicio_efetiva = dt_atrib
            
            dev = devolucoes_ativas_notif.get(p.get('id'))
            if dev:
                prazo_efetivo = dev.get('prazo_dias', prazo_efetivo)
                dt_dev_str = dev.get('data_devolucao')
                if dt_dev_str:
                    data_inicio_efetiva = date.fromisoformat(dt_dev_str) if isinstance(dt_dev_str, str) else dt_dev_str

            # --- Notificação para Servidor ---
            if p.get('status_servidor') in ["No Prazo", "Atrasado"] and servidor.get('notifica_email_prazos'):
                data_final_servidor = calculate_due_date(
                    start_date=data_inicio_efetiva, 
                    prazo_dias=prazo_efetivo, 
                    tipo_contagem=produto.get('tipo_contagem_prazo'), 
                    id_usuario=sid, 
                    dias_suspensos=p.get('prazo_total_dias_suspenso', 0),
                    nao_se_aplica_prazo=p.get('nao_se_aplica_prazo_servidor', False)
                )
                
                notif_env = p.get('notificacao_atraso_enviada')
                p_num = p.get('processo_numero')
                
                if data_final_servidor < hoje and not notif_env:
                    assunto = f'Processo Atrasado: {p_num}'
                    corpo = f'O processo nº {p_num} está atrasado. O prazo era {data_final_servidor.strftime("%d/%m/%Y")}.'
                    send_email_notification(servidor.get('email'), assunto, corpo)
                    update_by_id("processos", p['id'], {'notificacao_atraso_enviada': True})
                    p['notificacao_atraso_enviada'] = True
                    
                elif data_final_servidor == hoje:
                    assunto = f'Lembrete de Prazo: Processo {p_num}'
                    corpo = f'Lembrete: O processo nº {p_num} vence hoje, {data_final_servidor.strftime("%d/%m/%Y")}.'
                    send_email_notification(servidor.get('email'), assunto, corpo)
            
            # --- Notificação para Chefe ---
            dt_base_revisao = p.get('data_atribuicao_chefe') or p.get('data_conclusao_servidor')
            if dt_base_revisao and isinstance(dt_base_revisao, str): dt_base_revisao = date.fromisoformat(str(dt_base_revisao)[:10])
            
            if p.get('status_chefe') in ["Aguardando Análise", "Revisão Atrasada"] and dt_base_revisao:
                data_final_revisao = calculate_due_date(
                    start_date=dt_base_revisao, 
                    prazo_dias=p.get('prazo_chefe_aplicado'), 
                    tipo_contagem=produto.get('tipo_contagem_prazo'), 
                    id_usuario=cid,
                    dias_suspensos=p.get('prazo_total_dias_suspenso', 0)
                )
                
                notif_env = p.get('notificacao_atraso_enviada')
                p_num = p.get('processo_numero')

                if data_final_revisao < hoje and not notif_env:
                    assunto = f'Revisão de Processo Atrasada: {p_num}'
                    corpo = f'A revisão do processo nº {p_num} está atrasada. O prazo era {data_final_revisao.strftime("%d/%m/%Y")}.'
                    send_email_notification(chefe.get('email'), assunto, corpo)
                    update_by_id("processos", p['id'], {'notificacao_atraso_enviada': True})
                    
                elif data_final_revisao == hoje:
                    assunto = f'Lembrete de Prazo de Revisão: {p_num}'
                    corpo = f'Lembrete: A revisão do processo nº {p_num} vence hoje, {data_final_revisao.strftime("%d/%m/%Y")}.'
                    send_email_notification(chefe.get('email'), assunto, corpo)
        
    except Exception as e:
        print(f"ERRO CRÍTICO ao enviar notificações de prazo: {e}")


def cleanup_old_notifications():
    """
    Remove notificações lidas há mais de 30 dias para manter o banco enxuto.
    """
    try:
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=30)).isoformat()
        
        # Buscar IDs das notificações antigas lidas
        old_notifs = QueryBuilder("notificacoes") \
            .eq("lida", True) \
            .lt("timestamp", cutoff) \
            .select("id") \
            .execute()
        
        if not old_notifs:
            print(f"[{datetime.now()}] Limpeza de notificações: nenhuma notificação antiga encontrada.")
            return 0
        
        # Deletar em batches
        count = 0
        for n in old_notifs:
            from supabase_client import delete_by_id
            delete_by_id("notificacoes", n['id'])
            count += 1
        
        print(f"[{datetime.now()}] Limpeza de notificações: {count} notificações antigas removidas.")
        return count
        
    except Exception as e:
        print(f"ERRO ao limpar notificações antigas: {e}")
        return 0
