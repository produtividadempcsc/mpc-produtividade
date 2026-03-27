# backup.py (Versão adaptada para Supabase API)

import os
import pandas as pd
from datetime import datetime, date
from supabase_client import QueryBuilder, select_all, upsert
from utils.timezone import now_brazil

from db_compat import get_config, set_config
import utils

TABLE_NAMES = [
    'usuarios', 'tipos_produto', 'processos', 'afastamentos', 
    'calendario', 'prompts_ia', 'configuracoes', 'substituicoes', 
    'processo_historico', 'gabinete_servidores', 'procurador_chefes',
    'chefe_subordinado_chefe', 'comentario_lido',
    'comentarios', 'notificacoes',
    'historico_perfil', 'historico_vinculos',
    'processo_servidor_historico',
    'processo_devolucoes', 'devolucao_procurador_chefe'
]
BACKUP_DIR = "backups_locais"

def list_backups():
    """Lista os arquivos de backup .xlsx no diretório de backups."""
    if not os.path.exists(BACKUP_DIR):
        return []
    
    files = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.xlsx') and os.path.isfile(os.path.join(BACKUP_DIR, f))]
    files.sort(key=lambda f: os.path.getmtime(os.path.join(BACKUP_DIR, f)), reverse=True)
    return files


def backup_local_excel() -> str:
    """
    Cria um backup de todas as tabelas em um único arquivo Excel,
    com cada tabela em uma aba separada, usando a API do Supabase.
    Retorna o caminho do arquivo se o backup for bem-sucedido.
    """
    timestamp = now_brazil().strftime("%Y-%m-%d_%H-%M-%S")
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)

    file_path = os.path.join(BACKUP_DIR, f"backup_mpcsc_{timestamp}.xlsx")
    
    try:
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            for table_name in TABLE_NAMES:
                try:
                    # Fetch all data via API using select_all helper
                    data = select_all(table_name)
                    
                    if data:
                        df = pd.DataFrame(data)
                    else:
                        df = pd.DataFrame()
                    
                    df.to_excel(writer, sheet_name=table_name, index=False)
                except Exception as e:
                    print(f"AVISO: Erro ao fazer backup da tabela '{table_name}': {e}")
                    continue
        
        if os.path.exists(file_path):
            print(f"Backup criado com sucesso em: {file_path}")
            return file_path
        else:
            print("A criação do arquivo de backup falhou por um motivo desconhecido.")
            return ""
            
    except Exception as e:
        import traceback
        print(f"Erro detalhado ao gerar backup em Excel: {e}")
        traceback.print_exc()
        if os.path.exists(file_path):
            os.remove(file_path)
        return ""

# Ordem de Restauração (Topológica)
RESTORE_ORDER = [
    'usuarios', 'tipos_produto', 'processos', 
    'afastamentos', 'substituicoes', 'calendario',
    'configuracoes', 'prompts_ia', 'notificacoes',
    'comentarios', 'processo_historico',
    'gabinete_servidores', 'procurador_chefes', 
    'chefe_subordinado_chefe', 'comentario_lido',
    'historico_perfil', 'historico_vinculos',
    'processo_servidor_historico',
    'processo_devolucoes', 'devolucao_procurador_chefe'
]

def clean_database():
    """
    Limpa todas as tabelas na ordem inversa de restauração para evitar conflitos
    de chaves estrangeiras.
    """
    print(f"[{now_brazil()}] AÇÃO: Limpando banco de dados antes da restauração...")
    tables_to_clean = list(reversed(RESTORE_ORDER))
    
    col_map = {
        'chefe_subordinado_chefe': 'chefe_superior_id',
        'comentario_lido': 'id_usuario',
        'gabinete_servidores': 'chefe_id',
        'procurador_chefes': 'procurador_id',
        'configuracoes': 'chave',
        'calendario': 'data'
    }
    
    for table in tables_to_clean:
        print(f"   [INFO] Apagando dados da tabela '{table}'...")
        try:
            pk_col = col_map.get(table, 'id')
            
            qb = QueryBuilder(table)
            qb.is_not_null(pk_col)  # Deleta tudo onde a coluna não é nula
            
            success = qb.delete()
            if not success:
                print(f"   [AVISO] Nenhuma exclusão retornada em '{table}' (pode já estar vazia).")
            else:
                print(f"   [INFO] Tabela '{table}' limpa com sucesso.")
        except Exception as e:
            print(f"   [ERRO] Falha ao limpar '{table}': {e}")


def restore_database(backup_source):
    """
    Restaura o banco de dados a partir de um arquivo Excel.
    Pode receber um caminho de arquivo (str) ou um objeto UploadedFile do Streamlit.
    """
    print(f"[{now_brazil()}] AÇÃO: Iniciando restauração do banco de dados...")
    
    try:
        # Limpar o banco primeiro
        clean_database()
        
        # Carregar Excel (suporta path ou buffer)
        xls = pd.ExcelFile(backup_source)
        
        success_count = 0
        errors = []
        
        # Armazenar IDs válidos de usuários para filtrar chaves estrangeiras órfãs
        valid_user_ids = set()

        for table in RESTORE_ORDER:
            if table in xls.sheet_names:
                try:
                    df = pd.read_excel(xls, sheet_name=table)
                    
                    if df.empty:
                        print(f"   [AVISO] Tabela '{table}' vazia no backup. Pulando.")
                        continue
                        
                    # Preencher valid_user_ids
                    if table == 'usuarios':
                        valid_user_ids = set(df['id'].dropna())
                    
                    # Filtrar registros órfãos que fariam a API falhar
                    if valid_user_ids:
                        if table == 'afastamentos' and 'id_usuario' in df.columns:
                            df = df[df['id_usuario'].isin(valid_user_ids)]
                        elif table == 'gabinete_servidores':
                            df = df[df['chefe_id'].isin(valid_user_ids) & df['servidor_id'].isin(valid_user_ids)]
                        elif table == 'procurador_chefes':
                            df = df[df['procurador_id'].isin(valid_user_ids) & df['chefe_id'].isin(valid_user_ids)]
                    
                        
                    # Limpeza de dados para compatibilidade com JSON/Supabase
                    # 1. Garantir que NaN se torne None (compatível com JSON null)
                    # Converter para object evita que None vire NaN em colunas numéricas
                    df = df.astype(object).where(pd.notnull(df), None)
                    
                    # 2. Converter datas (se houver colunas de data que ficaram como objeto/timestamp)
                    # O pandas read_excel chupa datas como Timestamp, que o supabase-py serializa bem,
                    # mas às vezes precisa de conversão para string ISO.
                    # Vamos converter Timestamps para str isoformat
                    for col in df.columns:
                        # Verifica se é datetime (pd.to_datetime pode ter sido aplicado ou inferido)
                        # Como convertemos para object, verificação de tipo pode ser tricky via api.types
                        # Mas 'astype(object)' mantém tipos originais (Timestamp, int, float) envoltos.
                        
                        # Melhor iterar e converter se for timestamp
                        sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else None
                        if isinstance(sample, (pd.Timestamp, datetime, date)):
                             df[col] = df[col].apply(lambda x: x.isoformat() if pd.notnull(x) else None)
                            
                    records = df.to_dict(orient='records')
                    count = len(records)
                    print(f"   [INFO] Restaurando '{table}' ({count} registros)...")
                    if records:
                        # print(f"      [DEBUG] Exemplo: {str(records[0])[:200]}...")
                        pass
                    # Usando insert direto para capturar exceções de lote
                    # (Como a base foi limpa, podemos usar insert. O upsert escondia o erro)
                    try:
                        from supabase_client import get_supabase
                        supabase_client = get_supabase()
                        # Tentar INSERT em lote
                        result = supabase_client.table(table).insert(records).execute()
                    except Exception as e_batch:
                        print(f"      [AVISO] Falha no insert em lote para '{table}'. Erro: {repr(e_batch)}")
                        print(f"      [AVISO] Tentando linha a linha (com upsert)...")
                        # Fallback linha a linha
                        for record in records:
                            try:
                                res_row = upsert(table, record)
                                if res_row is None:
                                     print(f"         [ERRO ROW] Tabela '{table}', registro id={record.get('id', 'N/A')} falhou (erro exibido pelo client).")
                            except Exception as e_row:
                                print(f"         [ERRO ROW] Tabela '{table}', Falha inesperada no registro id={record.get('id', 'N/A')}: {repr(e_row)}")
                            
                    success_count += 1
                    
                except Exception as e_table:
                    msg = f"Erro ao restaurar tabela '{table}': {repr(e_table)}"
                    print(f"   [ERRO] {msg}")
                    errors.append(msg)
            else:
                print(f"   [INFO] Tabela '{table}' não encontrada no arquivo de backup.")

        # Resetar sequências de auto-incremento para evitar conflito de IDs
        print(f"[{now_brazil()}] AÇÃO: Resetando sequências de auto-incremento...")
        try:
            from supabase_client import rpc
            rpc('reset_all_sequences')
            print(f"[{now_brazil()}] SUCESSO: Sequências resetadas.")
        except Exception as e_seq:
            print(f"[{now_brazil()}] AVISO: Falha ao resetar sequências: {e_seq}")

        if errors:
            return False, f"Restauração concluída com {len(errors)} erros. Verifique os logs."
        else:
            return True, "Banco de dados restaurado com sucesso! (Dados mesclados/atualizados)"

    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Erro crítico na restauração: {e}"


def executar_backup_automatico_e_enviar_email():
    """
    Job para ser executado pelo scheduler. Verifica se um backup automático é
    necessário com base na configuração, o executa e envia por e-mail.
    """
    print(f"[{now_brazil()}] JOB INICIADO: Verificação de backup automático.")
    try:
        freq = get_config('backup_frequencia') or "Desativado"
        last_backup_str = get_config('data_ultimo_backup')
        email_backup = get_config('email_backup_automatico')
        
        if freq == "Desativado":
            print(f"[{now_brazil()}] INFO: Backup automático desativado. Job ignorado.")
            return

        needs_backup = False
        if not last_backup_str:
            needs_backup = True
        else:
            try:
                last_backup_date = datetime.fromisoformat(last_backup_str)
                # Fix: Garantir comparação entre datetimes do mesmo tipo (naive)
                now_naive = now_brazil().replace(tzinfo=None)
                delta = now_naive - last_backup_date
                if freq == "Diário" and delta.days >= 1:
                    needs_backup = True
                elif freq == "Semanal" and delta.days >= 7:
                    needs_backup = True
            except Exception as e:
                print(f"⚠️ Erro silencioso em backup.py (Date parse): {e}")
                needs_backup = True
        
        if not needs_backup:
            print(f"[{now_brazil()}] INFO: Backup não é necessário hoje. Próxima verificação agendada.")
            return

        print(f"[{now_brazil()}] AÇÃO: Backup necessário. Gerando arquivo...")
        file_path = backup_local_excel()

        if not file_path:
            print(f"[{now_brazil()}] ERRO: A criação do arquivo de backup local falhou.")
            return

        set_config('data_ultimo_backup', now_brazil().isoformat())
        
        print(f"[{now_brazil()}] SUCESSO: Backup local criado em '{file_path}'.")

        destinatario = email_backup
        if not destinatario:
            print(f"[{now_brazil()}] AVISO: E-mail de backup não configurado. O arquivo foi salvo localmente mas não será enviado.")
            return

        print(f"[{now_brazil()}] AÇÃO: Enviando backup para {destinatario}...")
        assunto = f"Backup do Sistema de Produtividade - {now_brazil().strftime('%d/%m/%Y')}"
        corpo = f"<html><body><p>Olá,</p><p>O backup automático ({freq.lower()}) do sistema de produtividade está em anexo.</p><p>Data de geração: {now_brazil().strftime('%d/%m/%Y %H:%M:%S')}</p></body></html>"
        
        success = utils.send_email_notification(destinatario, assunto, corpo, attachment_path=file_path, force_send=True)

        if success:
            print(f"[{now_brazil()}] SUCESSO: Backup enviado por e-mail para {destinatario}.")
        else:
            print(f"[{now_brazil()}] ERRO: Falha ao enviar o e-mail de backup.")

    except Exception as e:
        print(f"[{now_brazil()}] ERRO CRÍTICO no job 'executar_backup_automatico_e_enviar_email': {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"[{now_brazil()}] JOB CONCLUÍDO: Verificação de backup automático.")


def executar_backup_manual_e_enviar_email(engine=None): # engine param kept for compatibility but ignored
    """
    Executa um backup manual e o envia por e-mail para o destinatário configurado.
    Retorna uma tupla (bool_sucesso, str_mensagem).
    """
    print(f"[{now_brazil()}] AÇÃO: Backup manual solicitado.")
    
    try:
        destinatario = get_config('email_backup_automatico')
    except Exception as e:
        print(f"⚠️ Erro silencioso em backup.py (Get Config email): {e}")
        destinatario = None

    if not destinatario:
        msg = "E-mail para backups não configurado. Por favor, configure um e-mail antes de executar o backup manual."
        print(f"[{now_brazil()}] ERRO: {msg}")
        return False, msg

    print(f"[{now_brazil()}] AÇÃO: Gerando arquivo de backup manual...")
    file_path = backup_local_excel()

    if not file_path:
        msg = "A criação do arquivo de backup local falhou."
        print(f"[{now_brazil()}] ERRO: {msg}")
        return False, msg

    print(f"[{now_brazil()}] AÇÃO: Enviando backup para {destinatario}...")
    assunto = f"Backup Manual do Sistema de Produtividade - {now_brazil().strftime('%d/%m/%Y')}"
    corpo = f"<html><body><p>Olá,</p><p>O backup manual solicitado do sistema de produtividade está em anexo.</p><p>Data de geração: {now_brazil().strftime('%d/%m/%Y %H:%M:%S')}</p></body></html>"
    
    success = utils.send_email_notification(destinatario, assunto, corpo, attachment_path=file_path, force_send=True)

    try:
        os.remove(file_path)
        print(f"[{now_brazil()}] INFO: Arquivo de backup local '{file_path}' removido após o envio.")
    except OSError as e:
        print(f"[{now_brazil()}] AVISO: Falha ao remover o arquivo de backup local: {e}")

    if success:
        msg = f"Backup manual enviado com sucesso por e-mail para {destinatario}."
        print(f"[{now_brazil()}] SUCESSO: {msg}")
        return True, msg
    else:
        msg = "Falha ao enviar o e-mail de backup. Verifique os logs."
        print(f"[{now_brazil()}] ERRO: {msg}")
        return False, msg
