import pandas as pd
from datetime import datetime, date, timedelta
import os
from supabase_client import QueryBuilder, select_all
import db_compat
import sys

def get_corregedoria_data(procurador_id: int, start_date: date, end_date: date):
    """
    Coleta e processa os dados para o relatório da corregedoria.
    Retorna um dicionário com os DataFrames prontos para o Excel.
    """
    
    # 1. Buscar dados do Procurador e sua equipe
    procurador = db_compat.get_user_by_id(procurador_id)
    if not procurador:
        raise ValueError(f"Procurador com ID {procurador_id} não encontrado.")
    
    # Buscar Chefes vinculados ao Procurador
    # Usando a tabela de associação 'procurador_chefes'
    rels_chefes = QueryBuilder("procurador_chefes").eq("procurador_id", procurador_id).execute()
    chefe_ids = [r['chefe_id'] for r in rels_chefes]
    
    chefes_users = []
    if chefe_ids:
        chefes_users = QueryBuilder("usuarios").in_list("id", chefe_ids).execute()
        
    chefes_map = {u['id']: u for u in chefes_users}
    
    # Buscar Servidores vinculados aos Chefes
    servidor_ids = []
    chefes_servidores_map = {} # chefe_id -> list of servidor_ids
    
    if chefe_ids:
        rels_servidores = QueryBuilder("gabinete_servidores").in_list("chefe_id", chefe_ids).execute()
        for r in rels_servidores:
            cid = r['chefe_id']
            sid = r['servidor_id']
            servidor_ids.append(sid)
            if cid not in chefes_servidores_map:
                chefes_servidores_map[cid] = []
            chefes_servidores_map[cid].append(sid)
            
    servidores_users = []
    if server_ids := list(set(servidor_ids)):
         servidores_users = QueryBuilder("usuarios").in_list("id", server_ids).execute()
    
    servidores_map = {u['id']: u for u in servidores_users}
    
    gabinete_ids = [procurador_id] + chefe_ids + list(set(servidor_ids))
    
    # 2. Buscar Processos do Procurador
    # Filter by id_procurador directly is efficient
    raw_processes = QueryBuilder("processos").eq("id_procurador", procurador_id).execute()
    
    # Pre-fetch product types for efficiency
    product_types = db_compat.get_all_product_types()
    prod_map = {p['id']: p for p in product_types}
    
    # 3. Filtrar e Processar Processos
    dados_processos = []
    
    start_dt = str(start_date)
    end_dt = str(end_date)
    
    for p in raw_processes:
        # Verificar se processa tramitou no período, lógica:
        # data_atribuicao_servidor OU data_conclusao_servidor OU data_conclusao_chefe 
        # deve estar entre start e end.
        
        dates_to_check = []
        if p.get('data_atribuicao_servidor'): dates_to_check.append(p.get('data_atribuicao_servidor'))
        if p.get('data_conclusao_servidor'): dates_to_check.append(p.get('data_conclusao_servidor'))
        if p.get('data_conclusao_chefe'): dates_to_check.append(p.get('data_conclusao_chefe'))
        
        in_period = False
        for d_str in dates_to_check:
            # d_str format YYYY-MM-DD
            if start_dt <= d_str <= end_dt:
                in_period = True
                break
        
        if not in_period:
            continue
            
        # Ensure essential fields exist
        if not all([p.get('id_servidor_responsavel'), p.get('id_chefe_gabinete'), p.get('id_tipo_produto'), p.get('data_atribuicao_servidor')]):
            continue
            
        tipo_prod = prod_map.get(p['id_tipo_produto'])
        if not tipo_prod: continue
        
        servidor = servidores_map.get(p['id_servidor_responsavel']) or db_compat.get_user_by_id(p['id_servidor_responsavel']) # Fallback if not in current hierarchy but in history
        chefe = chefes_map.get(p['id_chefe_gabinete']) or db_compat.get_user_by_id(p['id_chefe_gabinete'])
        
        # --- Cálculos Servidor ---
        servidor_concluiu_prazo = "N/A"
        tempo_conclusao_servidor = None
        afastamento_servidor = 0
        
        # Parsing dates
        d_atrib_serv = datetime.fromisoformat(p.get('data_atribuicao_servidor')).date()
        d_concl_serv = datetime.fromisoformat(p.get('data_conclusao_servidor')).date() if p.get('data_conclusao_servidor') else None
        
        if d_concl_serv:
             # Calculate due date logic
             # Note: calling db_compat.calculate_due_date
             # Args: start_date, prazo_dias, tipo_contagem, id_usuario, dias_suspensos, nao_se_aplica_prazo
             
             prazo_servidor = p.get('prazo_servidor_aplicado')
             tipo_contagem = tipo_prod.get('tipo_contagem_prazo')
             dias_suspensos = p.get('prazo_total_dias_suspenso', 0)
             nao_aplica = p.get('nao_se_aplica_prazo_servidor', False)
             
             data_vencimento_servidor = db_compat.calculate_due_date(
                 d_atrib_serv, prazo_servidor, tipo_contagem, 
                 p['id_servidor_responsavel'], dias_suspensos, nao_aplica
             )
             
             servidor_concluiu_prazo = "Sim" if d_concl_serv <= data_vencimento_servidor else "Não"
             tempo_conclusao_servidor = db_compat.calculate_net_work_days(d_atrib_serv, d_concl_serv, p['id_servidor_responsavel'])
             afastamento_servidor = db_compat.get_leave_days_for_period(d_atrib_serv, d_concl_serv, p['id_servidor_responsavel'])

        # --- Cálculos Chefe ---
        chefe_concluiu_prazo = "N/A"
        tempo_revisao_chefe = None
        afastamento_chefe = 0
        
        d_concl_chefe = datetime.fromisoformat(p.get('data_conclusao_chefe')).date() if p.get('data_conclusao_chefe') else None
        
        if p.get('ignorar_revisao_chefe'):
            chefe_concluiu_prazo = "Não se Aplica"
        elif d_concl_serv and d_concl_chefe:
            prazo_chefe = p.get('prazo_chefe_aplicado')
            tipo_contagem = tipo_prod.get('tipo_contagem_prazo')
            dias_suspensos = p.get('prazo_total_dias_suspenso', 0)
            
            data_vencimento_chefe = db_compat.calculate_due_date(
                d_concl_serv, prazo_chefe, tipo_contagem,
                p['id_chefe_gabinete'], dias_suspensos
            )
            
            chefe_concluiu_prazo = "Sim" if d_concl_chefe <= data_vencimento_chefe else "Não"
            tempo_revisao_chefe = db_compat.calculate_net_work_days(d_concl_serv, d_concl_chefe, p['id_chefe_gabinete'])
            afastamento_chefe = db_compat.get_leave_days_for_period(d_concl_serv, d_concl_chefe, p['id_chefe_gabinete'])

        dados_processos.append({
            'Nº do Processo': p.get('processo_numero'),
            'Tipo do Processo': tipo_prod.get('nome_produto'),
            'Servidor Responsável': servidor.get('nome_completo') if servidor else "Desconhecido",
            'Data de Atribuição (Servidor)': d_atrib_serv,
            'Data de Conclusão (Servidor)': d_concl_serv,
            'Afastamento Servidor (dias)': afastamento_servidor,
            'Tempo de Conclusão (Servidor)': tempo_conclusao_servidor,
            'Servidor Concluiu no Prazo?': servidor_concluiu_prazo,
            'Chefe de Gabinete': chefe.get('nome_completo') if chefe else "Desconhecido",
            'Chefe de Gabinete ID': p['id_chefe_gabinete'],
            'Servidor ID': p['id_servidor_responsavel'],
            'Data de Início da Revisão': d_concl_serv, # Same as serv conclusion
            'Data de Revisão (Chefe de Gabinete)': d_concl_chefe,
            'Afastamento Chefe (dias)': afastamento_chefe,
            'Tempo de Revisão (Chefe)': tempo_revisao_chefe,
            'Chefe Concluiu no Prazo?': chefe_concluiu_prazo,
            'Prazo MPC - servidor': p.get('prazo_servidor_aplicado'),
            'Prazo MPC - chefe de gabinete': p.get('prazo_chefe_aplicado')
        })
        
    # Build DataFrames
    df_universo = pd.DataFrame(dados_processos)
    
    if df_universo.empty:
        return None
        
    # --- Process DataFrames for Sheets ---
    
    # 1. Consolidado Gabinete
    df_consolidado = pd.DataFrame({
        'Procurador': [procurador.get('nome_completo')],
        'Total de Processos Tramitados': [len(df_universo)]
    })
    
    # Filters for summary calculation
    # We need to filter 'concluded' ones for productivity metrics
    # df_extrato_servidores = df_universo[df_universo['Data de Conclusão (Servidor)'].between(start_date, end_date)]
    # Pandas between works with dates if col is datetime. 
    # Our cols are objects (date). Let's convert for filtering safety.
    
    df_univ_calc = df_universo.copy()
    df_univ_calc['Data de Conclusão (Servidor)'] = pd.to_datetime(df_univ_calc['Data de Conclusão (Servidor)'], errors='coerce').dt.date
    df_univ_calc['Data de Revisão (Chefe de Gabinete)'] = pd.to_datetime(df_univ_calc['Data de Revisão (Chefe de Gabinete)'], errors='coerce').dt.date
    
    # Filter: Conclusion IS IN report period
    mask_serv = df_univ_calc['Data de Conclusão (Servidor)'].apply(lambda x: start_date <= x <= end_date if pd.notnull(x) else False)
    df_extrato_servidores = df_univ_calc[mask_serv].copy()
    
    mask_chefe = df_univ_calc['Data de Revisão (Chefe de Gabinete)'].apply(lambda x: start_date <= x <= end_date if pd.notnull(x) else False)
    df_extrato_chefes = df_univ_calc[mask_chefe].copy()

    def calcular_percentuais_produtividade(base_df, total_tramitados, serv_col='Servidor Concluiu no Prazo?', chefe_col='Chefe Concluiu no Prazo?'):
        if base_df.empty:
             return pd.Series({
                'Total de Processos Tramitados': total_tramitados,
                'Servidores - % no Prazo': 0,
                'Servidores - % Fora do Prazo': 0,
                'Chefes - % no Prazo': 0,
                'Chefes - % Fora do Prazo': 0,
            })
            
        serv_base_calculo = base_df[base_df[serv_col].isin(['Sim', 'Não'])]
        chefe_base_calculo = base_df[base_df[chefe_col].isin(['Sim', 'Não'])]
        
        serv_no_prazo_pct = (serv_base_calculo[serv_col] == 'Sim').sum() / len(serv_base_calculo) * 100 if not serv_base_calculo.empty else 0
        chefe_no_prazo_pct = (chefe_base_calculo[chefe_col] == 'Sim').sum() / len(chefe_base_calculo) * 100 if not chefe_base_calculo.empty else 0
        
        return pd.Series({
            'Total de Processos Tramitados': total_tramitados,
            'Servidores - % no Prazo': serv_no_prazo_pct,
            'Servidores - % Fora do Prazo': 100 - serv_no_prazo_pct if not serv_base_calculo.empty else 0,
            'Chefes - % no Prazo': chefe_no_prazo_pct,
            'Chefes - % Fora do Prazo': 100 - chefe_no_prazo_pct if not chefe_base_calculo.empty else 0,
        })

    # 2. Produtividade por Tipo de Processo
    df_prod_tipo_processo = df_universo.groupby('Tipo do Processo').apply(
        lambda g: calcular_percentuais_produtividade(g, total_tramitados=len(g)), include_groups=False
    ).reset_index()

    # 3. Produtividade por Chefe (use extrato chefe for metrics, but original script logic might be slightly different. 
    # Original logic: "df_prod_chefe = df_extrato_chefes.groupby()..."
    # We stick to original logic: metrics based on COMPLETED processes in period.
    df_prod_chefe = df_extrato_chefes.groupby('Chefe de Gabinete').apply(
        lambda g: calcular_percentuais_produtividade(g, total_tramitados=len(g)), include_groups=False
    ).reset_index()
    # Rename cols
    df_prod_chefe.rename(columns={
        'Servidores - % no Prazo': 'Servidores da Equipe - % no Prazo',
        'Servidores - % Fora do Prazo': 'Servidores da Equipe - % Fora do Prazo',
        'Chefes - % no Prazo': 'Revisões do Chefe - % no Prazo',
        'Chefes - % Fora do Prazo': 'Revisões do Chefe - % Fora do Prazo',
    }, inplace=True)
    
    # 4. Produtividade por Servidor
    # "df_prod_servidor = df_extrato_servidores.groupby..."
    df_prod_servidor = df_extrato_servidores.groupby(['Servidor Responsável', 'Chefe de Gabinete']).apply(
        lambda g: calcular_percentuais_produtividade(g, total_tramitados=len(g)), include_groups=False
    ).reset_index()
    
    cols_serv = ['Servidor Responsável', 'Chefe de Gabinete', 'Total de Processos Tramitados', 'Servidores - % no Prazo', 'Servidores - % Fora do Prazo']
    # Ensure cols exist
    existing_cols = [c for c in cols_serv if c in df_prod_servidor.columns]
    df_prod_servidor = df_prod_servidor[existing_cols]
    
    df_prod_servidor.rename(columns={
        'Servidor Responsável': 'Servidor', 
        'Chefe de Gabinete': 'Chefe Imediato',
        'Total de Processos Tramitados': 'Total de Processos Concluídos',
        'Servidores - % no Prazo': 'Conclusões do Servidor - % no Prazo',
        'Servidores - % Fora do Prazo': 'Conclusões do Servidor - % Fora do Prazo',
    }, inplace=True)

    # 5. Afastamentos
    # Query for all leaves of people in gabinete that intersect with period
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()
    
    # Using db_compat.QueryBuilder is harder for "OR" conditions on dates (start <= end AND end >= start) with overlaps.
    # We will fetch all leaves for these users and filter in python for safety and ease
    
    leaves_data = []
    if gabinete_ids:
        raw_leaves = QueryBuilder("afastamentos").in_list("id_usuario", gabinete_ids).execute()
        
        users_map_all = {**chefes_map, **servidores_map, procurador_id: procurador}
        
        for l in raw_leaves:
            l_start = datetime.fromisoformat(l['data_inicio']).date()
            l_end = datetime.fromisoformat(l['data_fim']).date()
            
            # Check overlap
            if max(start_date, l_start) <= min(end_date, l_end):
                user = users_map_all.get(l['id_usuario'])
                leaves_data.append({
                    'Nome': user.get('nome_completo') if user else 'Desconhecido',
                    'Perfil': user.get('perfil') if user else 'Desconhecido',
                    'Descrição do Afastamento': l.get('descricao'),
                    'Data de Início': l_start,
                    'Data de Fim': l_end,
                    'Duração (dias)': (l_end - l_start).days + 1
                })
    
    df_afastamentos = pd.DataFrame(leaves_data)

    # 6. Extrato Simplificado
    df_extrato_simplificado = df_universo[[
        'Nº do Processo',
        'Prazo MPC - servidor',
        'Tempo de Conclusão (Servidor)',
        'Data de Conclusão (Servidor)',
        'Prazo MPC - chefe de gabinete',
        'Tempo de Revisão (Chefe)',
        'Data de Revisão (Chefe de Gabinete)'
    ]].copy()
    
    df_extrato_simplificado.rename(columns={
        'Nº do Processo': 'Número do processo',
        'Tempo de Conclusão (Servidor)': 'Número de dias - Servidor',
        'Data de Conclusão (Servidor)': 'Data de Conclusão servidor',
        'Tempo de Revisão (Chefe)': 'Número de dias - chefe de gabinete',
        'Data de Revisão (Chefe de Gabinete)': 'Data de revisão - chefe de gabinete'
    }, inplace=True)

    return {
        'Consolidado do Gabinete': df_consolidado,
        'Prod por Tipo de Processo': df_prod_tipo_processo,
        'Prod por Chefe de Gabinete': df_prod_chefe,
        'Prod por Servidor': df_prod_servidor,
        'Afastamentos no Período': df_afastamentos,
        'Extrato Servidores': df_extrato_servidores,
        'Extrato Chefes Gabinete': df_extrato_chefes,
        'Extrato Simplificado': df_extrato_simplificado
    }


def generate_corregedoria_excel(procurador_id: int, start_date: date, end_date: date) -> str:
    """
    Gera o arquivo Excel e retorna o path.
    """
    
    dfs = get_corregedoria_data(procurador_id, start_date, end_date)
    
    if not dfs:
        return None
        
    procurador = db_compat.get_user_by_id(procurador_id)
    nome_safe = "".join(c for c in procurador.get('nome_completo', 'Relatorio') if c.isalnum() or c in (' ', '_')).rstrip().replace(" ", "_")
    
    filename = f"Relatorio_Corregedoria_{nome_safe}_{start_date.strftime('%d%m%Y')}_a_{end_date.strftime('%d%m%Y')}.xlsx"
    filepath = os.path.join("relatorios", filename)
    os.makedirs("relatorios", exist_ok=True)
    
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        for sheet_name, df in dfs.items():
            if df is None: continue
            
            # Format Date Columns
            df_export = df.copy()
            for col in df_export.columns:
                if 'Data' in col:
                     df_export[col] = pd.to_datetime(df_export[col], errors='coerce').dt.strftime('%d-%m-%Y')
            
            df_export.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Auto-adjust columns
            worksheet = writer.sheets[sheet_name]
            for column_cells in worksheet.columns:
                max_length = 0
                column = column_cells[0].column_letter
                for cell in column_cells:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2)
                worksheet.column_dimensions[column].width = adjusted_width

    return filepath
