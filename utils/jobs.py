
from datetime import date, datetime, timedelta
import pytz
from supabase_client import supabase, QueryBuilder, select_all, update_by_id
from db_compat import (
    get_correct_product_type_version, get_product_type_by_id, 
    calculate_due_date, is_business_day
)
from utils.notifications import send_email_notification
from utils.timezone import today_brazil, now_brazil

def update_process_statuses():
    """
    Analisa todos os processos para garantir a integridade dos prazos aplicados e, em seguida,
    atualiza os status dos processos que ainda estão ativos.
    (Versão Supabase)
    """
    try:
        print(f"[{datetime.now()}] INICIANDO JOB de verificação de prazos e status (Supabase).")
        
        # --- ETAPA 1: CORREÇÃO DE INTEGRIDADE DOS PRAZOS ---
        print(f"[{datetime.now()}] ETAPA 1: Verificando integridade dos prazos...")
        
        todos_processos = select_all("processos")
        prazo_updates_count = 0

        for p in todos_processos:
            if not p.get('data_atribuicao_servidor') or not p.get('id_tipo_produto'):
                continue
            
            dt_atrib = p['data_atribuicao_servidor']
            if isinstance(dt_atrib, str):
                dt_atrib = date.fromisoformat(dt_atrib)

            produto_correto = get_correct_product_type_version(p['id_tipo_produto'], dt_atrib)
            if not produto_correto:
                continue

            updates = {}
            if p.get('prazo_servidor_aplicado') != produto_correto['prazo_servidor']:
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
            produto_obj = get_product_type_by_id(p['id_tipo_produto'])
            if not produto_obj: continue
            
            dt_atrib = p.get('data_atribuicao_servidor')
            if isinstance(dt_atrib, str): dt_atrib = date.fromisoformat(dt_atrib)
            
            data_final_servidor = calculate_due_date(
                start_date=dt_atrib,
                prazo_dias=p.get('prazo_servidor_aplicado'),
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

        for p in processos_chefe_ativos:
            produto_obj = get_product_type_by_id(p['id_tipo_produto'])
            if not produto_obj: continue
            
            dt_conclusao = p.get('data_conclusao_servidor')
            if dt_conclusao and isinstance(dt_conclusao, str): dt_conclusao = date.fromisoformat(dt_conclusao)
            
            if not dt_conclusao: continue 

            data_final_chefe = calculate_due_date(
                start_date=dt_conclusao,
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

        print(f"[{datetime.now()}] JOB FINALIZADO. Total Updates: {status_updates_count}")

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
            
            if prazo_serv is None:
                updated_fields['prazo_servidor_aplicado'] = produto.get('prazo_servidor')
                prazo_serv = produto.get('prazo_servidor')
                
            if prazo_chefe is None:
                updated_fields['prazo_chefe_aplicado'] = produto.get('prazo_chefe')
                prazo_chefe = produto.get('prazo_chefe')

            dt_concl_chefe = processo.get('data_conclusao_chefe')
            dt_concl_serv = processo.get('data_conclusao_servidor')
            dt_atrib_serv = processo.get('data_atribuicao_servidor')
            
            def parse_dt(d):
                if isinstance(d, str): return date.fromisoformat(d)
                return d
            
            dt_concl_chefe = parse_dt(dt_concl_chefe)
            dt_concl_serv = parse_dt(dt_concl_serv)
            dt_atrib_serv = parse_dt(dt_atrib_serv)

            if dt_concl_chefe is not None:
                if processo.get('status_servidor') != "Finalizado":
                    updated_fields['status_servidor'] = "Finalizado"
                if processo.get('status_chefe') != "Finalizado":
                    updated_fields['status_chefe'] = "Finalizado"
                    
            elif dt_concl_serv is not None:
                if processo.get('status_servidor') != "Concluído":
                    updated_fields['status_servidor'] = "Concluído"
                
                data_final_chefe = calculate_due_date(
                    start_date=dt_concl_serv,
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
            chunk_size = 100
            for i in range(0, len(updates), chunk_size):
                chunk = updates[i:i + chunk_size]
                try:
                    supabase.table("processos").upsert(chunk).execute()
                    print(f"Update partial batch {i}-{i+len(chunk)}")
                except Exception as e:
                    print(f"Error upserting batch: {e}")
        
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

            # --- Notificação para Servidor ---
            if p.get('status_servidor') in ["No Prazo", "Atrasado"] and servidor.get('notifica_email_prazos'):
                data_final_servidor = calculate_due_date(
                    start_date=dt_atrib, 
                    prazo_dias=p.get('prazo_servidor_aplicado'), 
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
            if p.get('status_chefe') in ["Aguardando Análise", "Revisão Atrasada"] and dt_concl:
                data_final_revisao = calculate_due_date(
                    start_date=dt_concl, 
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
