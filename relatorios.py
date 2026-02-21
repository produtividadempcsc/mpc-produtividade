import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
import os
import io
import zipfile
from fpdf import FPDF
from supabase_client import QueryBuilder, select_all
from db_compat import get_all_users
from repositories.calendar_repository import get_all_holidays
from repositories.afastamento_repository import get_all_leave_dates_by_user
from services.prazo_service import (
    calculate_due_date_batch,
    calculate_net_work_days_batch,
    calculate_net_duration_calendar_batch,
)

def get_available_years():
    """
    Retorna anos disponíveis para relatórios.
    Gera dinamicamente de 2024 até o ano corrente, em ordem decrescente.
    """
    current_year = datetime.now().year
    return list(range(current_year, 2023, -1))


def sanitize_text(text):
    if text is None: return ""
    return str(text).encode('latin-1', 'replace').decode('latin-1')

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        try:
            self.image('logo_mpcsc.jpg', 10, 8, 33)
        except Exception:
            self.cell(0, 10, 'MPC/SC', 0, 0, 'L')
        self.cell(0, 10, sanitize_text('Relatório de Produtividade'), 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def gerar_relatorio_dashboard(df_processos: pd.DataFrame):
    pdf = PDF(orientation='L')
    pdf.add_page()
    
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, sanitize_text('Lista de Processos'), 0, 1, 'L')

    if df_processos.empty:
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, 'Nenhum processo encontrado para os filtros selecionados.', 0, 1)
        return bytes(pdf.output(dest='S')) # Corrected line

    pdf.set_font('Arial', 'B', 8)
    line_height = pdf.font_size * 2.5
    col_widths = {
        'Nº Processo': 25,
        'Servidor': 45,
        'Produto': 65,
        'Status Geral': 25,
        'Data Final': 25
    }
    headers = list(col_widths.keys())

    for i, header in enumerate(headers):
        pdf.cell(col_widths[header], line_height, sanitize_text(header), 1, 0, 'C')
    pdf.ln()

    pdf.set_font('Arial', '', 8)
    for index, row in df_processos.iterrows():
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        max_y = y_start
        pdf.set_xy(x_start, y_start)
        pdf.multi_cell(col_widths['Nº Processo'], line_height, sanitize_text(row.get('Nº Processo')), border=1, align='L')
        max_y = max(max_y, pdf.get_y())
        
        pdf.set_xy(x_start + col_widths['Nº Processo'], y_start)
        pdf.multi_cell(col_widths['Servidor'], line_height, sanitize_text(row.get('Servidor')), border=1, align='L')
        max_y = max(max_y, pdf.get_y())

        pdf.set_xy(x_start + col_widths['Nº Processo'] + col_widths['Servidor'], y_start)
        pdf.multi_cell(col_widths['Produto'], line_height, sanitize_text(row.get('Produto')), border=1, align='L')
        max_y = max(max_y, pdf.get_y())

        pdf.set_xy(x_start + col_widths['Nº Processo'] + col_widths['Servidor'] + col_widths['Produto'], y_start)
        pdf.multi_cell(col_widths['Status Geral'], line_height, sanitize_text(row.get('Status Geral')), border=1, align='C')
        max_y = max(max_y, pdf.get_y())
        
        pdf.set_xy(x_start + col_widths['Nº Processo'] + col_widths['Servidor'] + col_widths['Produto'] + col_widths['Status Geral'], y_start)
        pdf.multi_cell(col_widths['Data Final'], line_height, sanitize_text(row.get('Data Final')), border=1, align='C')
        max_y = max(max_y, pdf.get_y())

        pdf.set_y(max_y)
        
    return bytes(pdf.output(dest='S')) # Corrected line

def gerar_relatorio_detalhado(df_processos: pd.DataFrame):
    pdf = PDF(orientation='L')
    pdf.add_page()

    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, sanitize_text('Relatório Detalhado de Processos'), 0, 1, 'C')
    pdf.ln()

    if df_processos.empty:
        pdf.set_font('Arial', '', 12)
        pdf.cell(0, 10, 'Nenhum processo encontrado para os filtros selecionados.', 0, 1)
        return bytes(pdf.output(dest='S')) # Corrected line

    pdf.set_font('Arial', 'B', 8)
    
    headers = [
        "Status", "Nº Processo", "Servidor",
        "Data Atribuição Servidor", "Prazo Servidor", "Data Conclusão Servidor",
        "Data Atribuição Chefe", "Prazo Chefe", "Data Conclusão"
    ]
    
    col_widths = {
        "Status": 20, "Nº Processo": 45, "Servidor": 40,
        "Data Atribuição Servidor": 38, "Prazo Servidor": 20, "Data Conclusão Servidor": 38,
        "Data Atribuição Chefe": 35, "Prazo Chefe": 20, "Data Conclusão": 25
    }

    for header in headers:
        pdf.cell(col_widths[header], 10, sanitize_text(header), 1, 0, 'C')
    pdf.ln()

    pdf.set_font('Arial', '', 8)
    
    for _, row in df_processos.iterrows():
        status = row.get('status_servidor', 'N/A')

        if status == "Atrasado": pdf.set_fill_color(255, 102, 102)
        elif status == "No Prazo": pdf.set_fill_color(102, 255, 102)
        elif status == "Concluído": pdf.set_fill_color(173, 216, 230)
        else: pdf.set_fill_color(255, 255, 255)

        pdf.cell(col_widths["Status"], 10, sanitize_text(status), 1, 0, 'C', fill=True)
        pdf.cell(col_widths["Nº Processo"], 10, sanitize_text(row.get('processo_numero')), 1)
        pdf.cell(col_widths["Servidor"], 10, sanitize_text(row.get('servidor_responsavel_nome')), 1)
        pdf.cell(col_widths["Data Atribuição Servidor"], 10, sanitize_text(str(row.get('data_atribuicao_servidor', ''))), 1)
        pdf.cell(col_widths["Prazo Servidor"], 10, sanitize_text(str(row.get('prazo_servidor_aplicado', ''))), 1)
        pdf.cell(col_widths["Data Conclusão Servidor"], 10, sanitize_text(str(row.get('data_conclusao_servidor', ''))), 1)
        pdf.cell(col_widths["Data Atribuição Chefe"], 10, sanitize_text(str(row.get('data_atribuicao_chefe', ''))), 1)
        pdf.cell(col_widths["Prazo Chefe"], 10, sanitize_text(str(row.get('prazo_chefe_aplicado', ''))), 1)
        pdf.cell(col_widths["Data Conclusão"], 10, sanitize_text(str(row.get('data_conclusao_chefe', ''))), 1)
        pdf.ln()
        
    return bytes(pdf.output(dest='S')) # Corrected line

def _get_user_hierarchy():
    """Get user hierarchy from Supabase API."""
    all_users = get_all_users()
    
    servidores = {u.get('id'): u.get('nome_completo') for u in all_users if u.get('perfil') == 'Servidor'}
    
    # For chefes, we need to fetch the relationships
    chefes = {}
    for u in all_users:
        if u.get('perfil') == 'Chefe de Gabinete':
            # Get servidores linked to this chefe via gabinete_servidores table
            servs = QueryBuilder("gabinete_servidores").eq("chefe_id", u.get('id')).execute()
            servidor_ids = [s.get('servidor_id') for s in servs]
            # Get procuradores linked via procurador_chefes table
            procs = QueryBuilder("procurador_chefes").eq("chefe_id", u.get('id')).execute()
            proc_ids = [p.get('procurador_id') for p in procs]
            chefes[u.get('id')] = {
                "nome": u.get('nome_completo'),
                "servidores": servidor_ids,
                "procuradores": proc_ids
            }
    
    # For procuradores, get their linked chefes
    procuradores = {}
    for u in all_users:
        if u.get('perfil') == 'Procurador':
            chefes_links = QueryBuilder("procurador_chefes").eq("procurador_id", u.get('id')).execute()
            chefe_ids = [c.get('chefe_id') for c in chefes_links]
            procuradores[u.get('id')] = {
                "nome": u.get('nome_completo'),
                "chefes": chefe_ids
            }
    
    return {"servidores": servidores, "chefes": chefes, "procuradores": procuradores}

def _format_value(value, is_percent=False):
    if pd.isna(value) or value is None: return 'Não Disponível'
    formatted_value = f"{value:.2f}" if isinstance(value, float) else str(value)
    return f"{formatted_value}%" if is_percent else formatted_value

def _calculate_average(series): return series.mean() if not series.empty else 0
def _calculate_percentage(series): return (series.sum() / len(series) * 100) if not series.empty else 0

def _fetch_processes_for_report(end_date_iso: str):
    """
    Fetch only the columns needed for report metrics, filtered to processes
    that existed by end_date (data_atribuicao_servidor <= end_date).
    Returns list of dicts.
    """
    columns = (
        "id, id_servidor_responsavel, id_chefe_gabinete, id_procurador, "
        "id_tipo_produto, data_atribuicao_servidor, data_conclusao_servidor, "
        "data_conclusao_chefe, prazo_servidor_aplicado, prazo_chefe_aplicado, "
        "prazo_total_dias_suspenso, status_servidor, status_chefe, "
        "data_finalizacao, nao_se_aplica_prazo_servidor, ignorar_revisao_chefe, "
        "ignorar_analise_procurador"
    )
    return QueryBuilder("processos") \
        .select(columns) \
        .lte("data_atribuicao_servidor", end_date_iso) \
        .fetch_all()


def _prefetch_leave_sets(user_ids: set) -> dict:
    """
    Pre-fetch leave date sets for all user_ids at once.
    Returns dict: {user_id: set(date)}.
    Uses the cached get_leave_dates_set per user (10min TTL),
    but calling it eagerly here avoids surprise latency inside .apply().
    """
    leave_map = {}
    for uid in user_ids:
        if uid is not None:
            leave_map[uid] = get_all_leave_dates_by_user().get(uid, set()) # Changed to use get_all_leave_dates_by_user
    return leave_map


def _build_report_dataframe(processes: list, product_types_map: dict):
    """
    Build the DataFrame used by report metrics from raw process dicts.
    """
    data = []
    for p in processes:
        tipo_produto = product_types_map.get(p.get('id_tipo_produto'), {})
        data.append({
            'id_servidor_responsavel': p.get('id_servidor_responsavel'),
            'id_chefe_gabinete': p.get('id_chefe_gabinete'),
            'id_procurador': p.get('id_procurador'),
            'data_atribuicao_servidor': p.get('data_atribuicao_servidor'),
            'data_conclusao_servidor': p.get('data_conclusao_servidor'),
            'data_conclusao_chefe': p.get('data_conclusao_chefe'),
            'prazo_servidor_aplicado': p.get('prazo_servidor_aplicado'),
            'prazo_chefe_aplicado': p.get('prazo_chefe_aplicado'),
            'prazo_total_dias_suspenso': p.get('prazo_total_dias_suspenso', 0),
            'status_servidor': p.get('status_servidor'),
            'status_chefe': p.get('status_chefe'),
            'tipo_contagem_prazo': tipo_produto.get('tipo_contagem_prazo', 'dias uteis'),
            'data_finalizacao': p.get('data_finalizacao'),
            'nao_se_aplica_prazo_servidor': p.get('nao_se_aplica_prazo_servidor', False),
            'ignorar_revisao_chefe': p.get('ignorar_revisao_chefe', False),
            'ignorar_analise_procurador': p.get('ignorar_analise_procurador', False)
        })

    df = pd.DataFrame(data)
    if df.empty:
        return df

    for col in ['data_atribuicao_servidor', 'data_conclusao_servidor',
                'data_conclusao_chefe', 'data_finalizacao']:
        df[col] = pd.to_datetime(df[col], errors='coerce')

    return df


def _compute_servidor_metrics(df_full, feriados, leave_map):
    """
    Compute server duration and deadline columns using batch functions.
    Returns df_servidor_concluido with 'duracao_servidor', 'data_final_servidor', 'no_prazo_servidor'.
    """
    df = df_full.dropna(subset=['data_atribuicao_servidor', 'data_conclusao_servidor']).copy()
    if df.empty:
        return df

    def calc_duracao(row):
        uid = row['id_servidor_responsavel']
        af = leave_map.get(uid, set())
        if row['tipo_contagem_prazo'] == 'dias uteis':
            return max(0, calculate_net_work_days_batch(
                row['data_atribuicao_servidor'].date(),
                row['data_conclusao_servidor'].date(),
                af, feriados
            ) - row['prazo_total_dias_suspenso'])
        else:
            return calculate_net_duration_calendar_batch(
                row['data_atribuicao_servidor'].date(),
                row['data_conclusao_servidor'].date(),
                af, row['prazo_total_dias_suspenso']
            )

    def calc_due(row):
        uid = row['id_servidor_responsavel']
        af = leave_map.get(uid, set())
        return calculate_due_date_batch(
            row['data_atribuicao_servidor'].date(),
            row['prazo_servidor_aplicado'],
            row['tipo_contagem_prazo'],
            af, feriados,
            row['prazo_total_dias_suspenso']
        )

    df['duracao_servidor'] = df.apply(calc_duracao, axis=1)
    df['data_final_servidor'] = df.apply(calc_due, axis=1)
    df['no_prazo_servidor'] = df['data_conclusao_servidor'].dt.date <= df['data_final_servidor']
    return df


def _compute_chefe_metrics(df_full, feriados, leave_map):
    """
    Compute chief review duration and deadline columns using batch functions.
    Returns df_chefe_concluido with 'duracao_revisao_chefe', 'data_final_chefe', 'no_prazo_chefe'.
    """
    df = df_full.dropna(subset=['data_conclusao_servidor', 'data_conclusao_chefe']).copy()
    if df.empty:
        return df

    def calc_duracao(row):
        uid = row['id_chefe_gabinete']
        af = leave_map.get(uid, set())
        if row['tipo_contagem_prazo'] == 'dias uteis':
            return max(0, calculate_net_work_days_batch(
                row['data_conclusao_servidor'].date(),
                row['data_conclusao_chefe'].date(),
                af, feriados
            ) - row['prazo_total_dias_suspenso'])
        else:
            return calculate_net_duration_calendar_batch(
                row['data_conclusao_servidor'].date(),
                row['data_conclusao_chefe'].date(),
                af, row['prazo_total_dias_suspenso']
            )

    def calc_due(row):
        uid = row['id_chefe_gabinete']
        af = leave_map.get(uid, set())
        return calculate_due_date_batch(
            row['data_conclusao_servidor'].date(),
            row['prazo_chefe_aplicado'],
            row['tipo_contagem_prazo'],
            af, feriados,
            row['prazo_total_dias_suspenso']
        )

    df['duracao_revisao_chefe'] = df.apply(calc_duracao, axis=1)
    df['data_final_chefe'] = df.apply(calc_due, axis=1)
    df['no_prazo_chefe'] = df['data_conclusao_chefe'].dt.date <= df['data_final_chefe']
    return df


def _extract_metrics(df_full, df_servidor_concluido, df_chefe_concluido,
                     start_date, end_date, procurador_names):
    """
    Extract all 9 metrics from pre-computed DataFrames for a given period.
    """
    report_cutoff_dt = pd.to_datetime(end_date)

    # Filter by completion date within period
    df_servidor_mes = df_servidor_concluido[
        df_servidor_concluido['data_conclusao_servidor'].dt.date.between(start_date, end_date)
    ] if not df_servidor_concluido.empty else df_servidor_concluido

    df_chefe_mes = df_chefe_concluido[
        df_chefe_concluido['data_conclusao_chefe'].dt.date.between(start_date, end_date)
    ] if not df_chefe_concluido.empty else df_chefe_concluido

    metricas = {}

    # 1) Processos concluídos pelos servidores (por Procurador)
    m1 = df_servidor_mes.groupby('id_procurador').size() if not df_servidor_mes.empty else pd.Series(dtype=int)
    metricas["1) Número de processos concluídos pelos pareceristas no mês (visão por procurador)"] = {
        procurador_names.get(pid, f"ID {pid}"): val for pid, val in m1.items() if pid in procurador_names
    }

    # 2) Média de dias (Servidor)
    m2 = df_servidor_mes.groupby('id_procurador')['duracao_servidor'].mean() if not df_servidor_mes.empty else pd.Series(dtype=float)
    metricas["2) Média de dias que os pareceristas demoraram para concluir o processo (visão média por procurador)"] = {
        procurador_names.get(pid, f"ID {pid}"): val for pid, val in m2.items() if pid in procurador_names
    }

    # 3) Percentual no prazo (Servidor)
    m3 = df_servidor_mes.groupby('id_procurador')['no_prazo_servidor'].apply(_calculate_percentage) if not df_servidor_mes.empty else pd.Series(dtype=float)
    metricas["3) Percentual de processos concluídos no prazo por pareceristas (visão média por procurador)"] = {
        procurador_names.get(pid, f"ID {pid}"): val for pid, val in m3.items() if pid in procurador_names
    }

    # 4) Acervo Servidor (Snapshot)
    m4_df = df_full[
        (df_full['data_atribuicao_servidor'] <= report_cutoff_dt) &
        (~df_full['nao_se_aplica_prazo_servidor'].fillna(False).astype(bool)) &
        (
            (
                (
                    (df_full['data_conclusao_servidor'].isnull()) |
                    (df_full['data_conclusao_servidor'] > report_cutoff_dt)
                ) &
                (df_full['status_servidor'].isin(['Em Andamento', 'Atrasado', 'No Prazo']))
            )
            |
            (df_full['status_servidor'] == 'Devolvido')
        )
    ]
    m4 = m4_df.groupby('id_procurador').size()
    metricas["4) Acervo de processo não concluídos ao encerrar o mês por parecerista (visão média por procurador)"] = {
        procurador_names.get(pid, f"ID {pid}"): val for pid, val in m4.items() if pid in procurador_names
    }

    # 5) Número revisados (Chefe)
    m5 = df_chefe_mes.groupby('id_procurador').size() if not df_chefe_mes.empty else pd.Series(dtype=int)
    metricas["5) Número de processos revisados no mês por chefe de gabinete (visão média por procurador)"] = {
        procurador_names.get(pid, f"ID {pid}"): val for pid, val in m5.items() if pid in procurador_names
    }

    # 6) Média dias revisão (Chefe)
    m6 = df_chefe_mes.groupby('id_procurador')['duracao_revisao_chefe'].mean() if not df_chefe_mes.empty else pd.Series(dtype=float)
    metricas["6) Média de dias que os chefes de gabinete demoraram para finalizar a revisão do processo (visão média por procurador)"] = {
        procurador_names.get(pid, f"ID {pid}"): val for pid, val in m6.items() if pid in procurador_names
    }

    # 7) Percentual revisão no prazo (Chefe)
    m7 = df_chefe_mes.groupby('id_procurador')['no_prazo_chefe'].apply(_calculate_percentage) if not df_chefe_mes.empty else pd.Series(dtype=float)
    metricas["7) Percentual de processos revisados pelos chefes de gabinetes no prazo (visão média por procurador)"] = {
        procurador_names.get(pid, f"ID {pid}"): val for pid, val in m7.items() if pid in procurador_names
    }

    # 8) Acervo Revisão Chefe (Snapshot)
    m8_df = df_full[
        (df_full['data_conclusao_servidor'] <= report_cutoff_dt) &
        (~df_full['ignorar_revisao_chefe'].fillna(False).astype(bool)) &
        (
            (
                (df_full['data_conclusao_chefe'].isnull()) |
                (df_full['data_conclusao_chefe'] > report_cutoff_dt)
            )
            |
            (df_full['status_chefe'] == 'Devolvido')
        )
    ]
    m8 = m8_df.groupby('id_procurador').size()
    metricas["8) Acervo de processo não revisados ao encerrar o mês por chefe de gabinete (visão média por procurador)"] = {
        procurador_names.get(pid, f"ID {pid}"): val for pid, val in m8.items() if pid in procurador_names
    }

    # 9) Acervo com Procurador (Snapshot)
    m9_df = df_full[
        (df_full['data_conclusao_chefe'] <= report_cutoff_dt) &
        (~df_full['ignorar_analise_procurador'].fillna(False).astype(bool)) &
        (df_full['status_chefe'] != 'Devolvido') &
        (
            (df_full['data_finalizacao'].isnull()) |
            (df_full['data_finalizacao'] > report_cutoff_dt)
        )
    ]
    m9 = m9_df.groupby('id_procurador').size()
    metricas["9) Acervo de processo revisados pelo chefe de gabinete que estão com o procurador (visão média por procurador)"] = {
        procurador_names.get(pid, f"ID {pid}"): val for pid, val in m9.items() if pid in procurador_names
    }

    return metricas


def calcular_metricas_mensais(mes, ano):
    """Calcula métricas mensais usando Supabase API (otimizado com batch)."""
    try:
        start_date = date(ano, mes, 1)
        end_date = (date(ano, mes, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        hierarchy = _get_user_hierarchy()
        processes = _fetch_processes_for_report(end_date.isoformat())
        all_product_types = select_all("tipos_produto")
        product_types_map = {p.get('id'): p for p in all_product_types}

        df_full = _build_report_dataframe(processes, product_types_map)
        if df_full.empty:
            return {}

        # Pre-fetch holidays and leaves in batch
        feriados = get_all_holidays()
        user_ids = set()
        for col in ['id_servidor_responsavel', 'id_chefe_gabinete']:
            user_ids.update(df_full[col].dropna().unique())
        leave_map = _prefetch_leave_sets(user_ids)

        # Compute derived columns using batch functions (no per-row DB calls)
        df_servidor_concluido = _compute_servidor_metrics(df_full, feriados, leave_map)
        df_chefe_concluido = _compute_chefe_metrics(df_full, feriados, leave_map)

        # Procurador name mapping
        procurador_names = {pid: pdata['nome'] for pid, pdata in hierarchy['procuradores'].items()}

        return _extract_metrics(
            df_full, df_servidor_concluido, df_chefe_concluido,
            start_date, end_date, procurador_names
        )

    except Exception as e:
        import traceback
        print(f"ERRO DETALHADO em calcular_metricas_mensais: {e}\n{traceback.format_exc()}")
        return {}


def gerar_relatorio_xlsx(metricas, mes, ano):
    wb = Workbook()
    ws = wb.active
    ws.title = f"Relatorio_{mes}_{ano}"
    font_bold = Font(bold=True)

    ws.cell(row=1, column=1, value="Métrica").font = font_bold
    ws.cell(row=1, column=2, value="Visão").font = font_bold
    ws.cell(row=1, column=3, value="Valor").font = font_bold
    
    row_idx = 2
    for metrica, visoes in sorted(metricas.items()):
        def format_value(v): return f"{v:.2f}" if isinstance(v, float) else v

        if isinstance(visoes, dict) and visoes:
            for visao, valor in visoes.items():
                ws.cell(row=row_idx, column=1, value=metrica)
                ws.cell(row=row_idx, column=2, value=str(visao))
                ws.cell(row=row_idx, column=3, value=format_value(valor))
                row_idx += 1
        else:
            ws.cell(row=row_idx, column=1, value=metrica)
            ws.cell(row=row_idx, column=3, value=format_value(visoes) if not isinstance(visoes, dict) else "N/A")
            row_idx += 1
            
    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            try:
                if len(str(cell.value)) > max_length: max_length = len(cell.value)
            except: pass
        adjusted_width = (max_length + 2)
        ws.column_dimensions[column].width = adjusted_width

    filepath = f"relatorios/Relatorio_Produtividade_{mes}_{ano}.xlsx"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    wb.save(filepath)
    return filepath


# ============================================================
# Relatório Mensal em PDF — fpdf2
# ============================================================
MESES_NOME = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

# Cores institucionais MPC/SC
_COR_AZUL  = (0, 51, 102)    # azul marinho
_COR_BRANCO = (255, 255, 255)
_COR_CINZA  = (245, 245, 245)
_COR_TEXTO  = (33, 33, 33)
_COR_BORDA  = (200, 200, 200)


class PDFRelatorio(FPDF):
    """PDF personalizado para o Relatório Mensal de Produtividade."""

    def __init__(self, titulo_cabecalho, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.titulo_cabecalho = titulo_cabecalho
        self.set_margins(left=18, top=18, right=18)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        # --- Logo ---
        try:
            self.image('logo_mpcsc.jpg', x=18, y=10, h=18)
        except Exception:
            pass

        # --- Nome da instituição ---
        self.set_xy(50, 10)
        self.set_font('Arial', 'B', 11)
        self.set_text_color(*_COR_AZUL)
        self.cell(0, 6, sanitize_text('Ministério Público de Santa Catarina'), ln=True, align='R')

        self.set_x(50)
        self.set_font('Arial', '', 9)
        self.set_text_color(*_COR_TEXTO)
        self.cell(0, 5, sanitize_text(self.titulo_cabecalho), ln=True, align='R')

        # --- Linha separadora ---
        self.set_draw_color(*_COR_AZUL)
        self.set_line_width(0.6)
        self.line(18, 30, self.w - 18, 30)
        self.ln(6)
        self.set_line_width(0.2)
        self.set_draw_color(*_COR_BORDA)

    def footer(self):
        self.set_y(-13)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(140, 140, 140)
        self.cell(0, 10, sanitize_text(f'Página {self.page_no()} / {{nb}}'), align='C')

    def secao_metrica(self, numero, titulo, dados):
        """Renderiza o título da métrica e a tabela de resultados."""
        # Título da métrica
        self.set_fill_color(*_COR_AZUL)
        self.set_text_color(*_COR_BRANCO)
        self.set_font('Arial', 'B', 9)
        self.cell(0, 7, sanitize_text(f'  {numero}. {titulo}'), fill=True, ln=True)
        self.ln(1)

        if not dados:
            self.set_font('Arial', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, sanitize_text('  Nenhum dado disponível para o período.'), ln=True)
            self.ln(3)
            return

        # Cabeçalho da tabela
        self.set_text_color(*_COR_BRANCO)
        self.set_fill_color(40, 80, 140)
        self.set_font('Arial', 'B', 8)
        col_w_proc  = self.w - self.l_margin - self.r_margin - 35
        col_w_valor = 35
        self.cell(col_w_proc,  6, sanitize_text('Procurador(a)'), border=0, fill=True, align='L')
        self.cell(col_w_valor, 6, sanitize_text('Valor'),         border=0, fill=True, align='C', ln=True)

        # Linhas de dados
        self.set_font('Arial', '', 8)
        for i, (procurador, valor) in enumerate(dados.items()):
            # Cores alternadas
            if i % 2 == 0:
                self.set_fill_color(*_COR_BRANCO)
            else:
                self.set_fill_color(*_COR_CINZA)
            self.set_text_color(*_COR_TEXTO)

            if isinstance(valor, float):
                valor_fmt = f'{valor:.2f}'
            else:
                valor_fmt = str(valor)

            self.cell(col_w_proc,  6, sanitize_text(f'  {procurador}'), border=0, fill=True, align='L')
            self.cell(col_w_valor, 6, sanitize_text(valor_fmt),          border=0, fill=True, align='C', ln=True)

        # Linha de rodapé da tabela
        self.set_draw_color(*_COR_BORDA)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(5)


def gerar_relatorio_pdf(metricas: dict, mes: int, ano: int) -> bytes:
    """Gera o relatório mensal de produtividade em PDF e retorna os bytes."""
    mes_nome       = MESES_NOME.get(mes, str(mes))
    periodo        = f'{mes_nome}/{ano}'
    data_geracao   = datetime.now().strftime('%d/%m/%Y %H:%M')
    titulo_top     = f'Relatório Mensal de Produtividade — {periodo}'

    pdf = PDFRelatorio(titulo_cabecalho=titulo_top, orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- Bloco de informações no topo da primeira página ---
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*_COR_AZUL)
    pdf.cell(0, 8, sanitize_text('RELATÓRIO MENSAL DE PRODUTIVIDADE'), ln=True, align='C')
    pdf.ln(1)

    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(*_COR_TEXTO)
    infos = [
        ('Período de Referência:', periodo),
        ('Data do Relatório:',     data_geracao),
        ('Origem:',                'Produzido automaticamente pelo Sistema de Produtividade MPC/SC'),
    ]
    for label, valor in infos:
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(52, 5, sanitize_text(label))
        pdf.set_font('Arial', '', 9)
        pdf.cell(0, 5, sanitize_text(valor), ln=True)

    # Linha divisora após informações
    pdf.ln(3)
    pdf.set_draw_color(*_COR_AZUL)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)
    pdf.set_line_width(0.2)
    pdf.set_draw_color(*_COR_BORDA)

    # --- Métricas ---
    # Mapeamento de chave completa -> título curto para o PDF
    titulos_curtos = {
        "1)": "Número de processos concluídos pelos pareceristas no mês",
        "2)": "Média de dias para concluir o processo (por procurador)",
        "3)": "Percentual de processos concluídos no prazo (por procurador)",
        "4)": "Acervo não concluído ao encerrar o mês (por procurador)",
        "5)": "Número de processos revisados no mês (por procurador)",
        "6)": "Média de dias para o Chefe finalizar a revisão (por procurador)",
        "7)": "Percentual de revisões pelo Chefe concluídas no prazo",
        "8)": "Acervo não revisado pelo Chefe ao encerrar o mês",
        "9)": "Acervo com o Procurador após revisão do Chefe",
    }

    for numero, (chave, dados) in enumerate(sorted(metricas.items()), start=1):
        # Obter prefixo ("1)", "2)", ...)
        prefixo = chave.strip()[:2]
        titulo  = titulos_curtos.get(prefixo, chave.split(')')[0].strip() if ')' in chave else chave[:80])
        pdf.secao_metrica(numero, titulo, dados if isinstance(dados, dict) else {})

    return bytes(pdf.output())


# ============================================================
# Relatórios por Período (Trimestral, Semestral, Anual)
# ============================================================

PERIODOS_CONFIG = {
    "Trimestral": {
        "Q1": {"nome": "1º Trimestre", "meses": [1, 2, 3]},
        "Q2": {"nome": "2º Trimestre", "meses": [4, 5, 6]},
        "Q3": {"nome": "3º Trimestre", "meses": [7, 8, 9]},
        "Q4": {"nome": "4º Trimestre", "meses": [10, 11, 12]},
    },
    "Semestral": {
        "S1": {"nome": "1º Semestre", "meses": [1, 2, 3, 4, 5, 6]},
        "S2": {"nome": "2º Semestre", "meses": [7, 8, 9, 10, 11, 12]},
    },
    "Anual": {
        "Anual": {"nome": "Anual", "meses": list(range(1, 13))},
    },
}

# Métricas de fluxo (acumulam/médiam): 1,2,3,5,6,7
# Métricas de snapshot (usam último mês): 4,8,9
_METRICAS_FLUXO = {"1)", "2)", "3)", "5)", "6)", "7)"}
_METRICAS_SNAPSHOT = {"4)", "8)", "9)"}


def calcular_metricas_periodo(ano: int, meses: list) -> dict:
    """
    Calcula métricas consolidadas para um período de vários meses.
    Otimizado: busca dados UMA VEZ para o período inteiro, depois fatia por mês.
    - Métricas de fluxo (1-3, 5-7): acumuladas/mediadas ao longo dos meses.
    - Métricas de snapshot (4, 8, 9): usam o último mês do período.
    """
    if not meses:
        return {}

    # Calculate overall date range for the entire period
    first_month_start = date(ano, min(meses), 1)
    last_month = max(meses)
    last_month_end = (date(ano, last_month, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    try:
        hierarchy = _get_user_hierarchy()

        # Single data fetch for the entire period
        processes = _fetch_processes_for_report(last_month_end.isoformat())
        all_product_types = select_all("tipos_produto")
        product_types_map = {p.get('id'): p for p in all_product_types}

        df_full = _build_report_dataframe(processes, product_types_map)
        if df_full.empty:
            return {}

        # Pre-fetch holidays and leaves ONCE
        feriados = get_all_holidays()
        user_ids = set()
        for col in ['id_servidor_responsavel', 'id_chefe_gabinete']:
            user_ids.update(df_full[col].dropna().unique())
        leave_map = _prefetch_leave_sets(user_ids)

        # Compute derived columns ONCE
        df_servidor_concluido = _compute_servidor_metrics(df_full, feriados, leave_map)
        df_chefe_concluido = _compute_chefe_metrics(df_full, feriados, leave_map)

        procurador_names = {pid: pdata['nome'] for pid, pdata in hierarchy['procuradores'].items()}

        # Compute metrics per month (no DB calls — just DataFrame slicing)
        metricas_por_mes = {}
        for mes in meses:
            start_date = date(ano, mes, 1)
            end_date = (date(ano, mes, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            m = _extract_metrics(
                df_full, df_servidor_concluido, df_chefe_concluido,
                start_date, end_date, procurador_names
            )
            if m:
                metricas_por_mes[mes] = m

        if not metricas_por_mes:
            return {}

        # Aggregate per-month metrics
        ultimo_mes = max(metricas_por_mes.keys())
        primeiro_mes_com_dados = min(metricas_por_mes.keys())
        modelo = metricas_por_mes[primeiro_mes_com_dados]

        resultado = {}

        for chave in sorted(modelo.keys()):
            prefixo = chave.strip()[:2]

            if prefixo in _METRICAS_SNAPSHOT:
                if ultimo_mes in metricas_por_mes and chave in metricas_por_mes[ultimo_mes]:
                    resultado[chave] = metricas_por_mes[ultimo_mes][chave]
                else:
                    resultado[chave] = modelo[chave]

            elif prefixo in _METRICAS_FLUXO:
                dados_agregados = {}

                for mes_key, metricas_mes in metricas_por_mes.items():
                    if chave not in metricas_mes:
                        continue
                    dados_mes = metricas_mes[chave]
                    if not isinstance(dados_mes, dict):
                        continue

                    for procurador, valor in dados_mes.items():
                        if procurador not in dados_agregados:
                            dados_agregados[procurador] = []
                        if valor is not None and not (isinstance(valor, float) and np.isnan(valor)):
                            dados_agregados[procurador].append(valor)

                resultado_metrica = {}
                for procurador, valores in dados_agregados.items():
                    if not valores:
                        resultado_metrica[procurador] = 0
                    elif prefixo in {"1)", "5)"}:
                        resultado_metrica[procurador] = sum(valores)
                    else:
                        resultado_metrica[procurador] = sum(valores) / len(valores)

                resultado[chave] = resultado_metrica
            else:
                resultado[chave] = modelo.get(chave, {})

        return resultado

    except Exception as e:
        import traceback
        print(f"ERRO DETALHADO em calcular_metricas_periodo: {e}\n{traceback.format_exc()}")
        return {}


def gerar_relatorio_periodo_pdf(metricas: dict, ano: int, nome_periodo: str) -> bytes:
    """Gera o relatório de produtividade para um período consolidado em PDF."""
    periodo = f'{nome_periodo}/{ano}'
    data_geracao = datetime.now().strftime('%d/%m/%Y %H:%M')
    titulo_top = f'Relatório de Produtividade — {periodo}'

    pdf = PDFRelatorio(titulo_cabecalho=titulo_top, orientation='P', unit='mm', format='A4')
    pdf.alias_nb_pages()
    pdf.add_page()

    # --- Bloco de informações ---
    pdf.set_font('Arial', 'B', 14)
    pdf.set_text_color(*_COR_AZUL)
    pdf.cell(0, 8, sanitize_text(f'RELATÓRIO DE PRODUTIVIDADE — {nome_periodo.upper()}'), ln=True, align='C')
    pdf.ln(1)

    pdf.set_font('Arial', '', 9)
    pdf.set_text_color(*_COR_TEXTO)
    infos = [
        ('Período de Referência:', periodo),
        ('Data do Relatório:', data_geracao),
        ('Origem:', 'Produzido automaticamente pelo Sistema de Produtividade MPC/SC'),
    ]
    for label, valor in infos:
        pdf.set_font('Arial', 'B', 9)
        pdf.cell(52, 5, sanitize_text(label))
        pdf.set_font('Arial', '', 9)
        pdf.cell(0, 5, sanitize_text(valor), ln=True)

    pdf.ln(3)
    pdf.set_draw_color(*_COR_AZUL)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(6)
    pdf.set_line_width(0.2)
    pdf.set_draw_color(*_COR_BORDA)

    # --- Métricas ---
    titulos_curtos = {
        "1)": "Processos concluídos pelos pareceristas no período",
        "2)": "Média de dias para concluir o processo (por procurador)",
        "3)": "Percentual de processos concluídos no prazo (por procurador)",
        "4)": "Acervo não concluído ao encerrar o período (por procurador)",
        "5)": "Processos revisados no período (por procurador)",
        "6)": "Média de dias para o Chefe finalizar a revisão (por procurador)",
        "7)": "Percentual de revisões pelo Chefe concluídas no prazo",
        "8)": "Acervo não revisado pelo Chefe ao encerrar o período",
        "9)": "Acervo com o Procurador após revisão do Chefe",
    }

    for numero, (chave, dados) in enumerate(sorted(metricas.items()), start=1):
        prefixo = chave.strip()[:2]
        titulo = titulos_curtos.get(prefixo, chave.split(')')[0].strip() if ')' in chave else chave[:80])
        pdf.secao_metrica(numero, titulo, dados if isinstance(dados, dict) else {})

    return bytes(pdf.output())


def gerar_relatorio_lote_zip(ano: int, meses: list = None) -> bytes:
    """
    Gera relatórios individuais para cada mês especificado e os empacota em um ZIP.
    Otimizado: busca dados UMA VEZ e fatia por mês.
    Retorna os bytes do arquivo ZIP.
    """
    if meses is None:
        meses = list(range(1, 13))

    # Single data fetch for the entire year
    last_month_end = date(ano, 12, 31)
    try:
        hierarchy = _get_user_hierarchy()
        processes = _fetch_processes_for_report(last_month_end.isoformat())
        all_product_types = select_all("tipos_produto")
        product_types_map = {p.get('id'): p for p in all_product_types}

        df_full = _build_report_dataframe(processes, product_types_map)

        feriados = get_all_holidays()
        leave_map = {}
        if not df_full.empty:
            user_ids = set()
            for col in ['id_servidor_responsavel', 'id_chefe_gabinete']:
                user_ids.update(df_full[col].dropna().unique())
            leave_map = _prefetch_leave_sets(user_ids)

        df_servidor_concluido = _compute_servidor_metrics(df_full, feriados, leave_map) if not df_full.empty else pd.DataFrame()
        df_chefe_concluido = _compute_chefe_metrics(df_full, feriados, leave_map) if not df_full.empty else pd.DataFrame()

        procurador_names = {pid: pdata['nome'] for pid, pdata in hierarchy['procuradores'].items()}
    except Exception as e:
        print(f"Erro ao carregar dados para lote: {e}")
        df_full = pd.DataFrame()
        df_servidor_concluido = pd.DataFrame()
        df_chefe_concluido = pd.DataFrame()
        procurador_names = {}

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        meses_gerados = 0
        for mes in meses:
            try:
                if df_full.empty:
                    continue
                start_date = date(ano, mes, 1)
                end_date = (date(ano, mes, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
                metricas = _extract_metrics(
                    df_full, df_servidor_concluido, df_chefe_concluido,
                    start_date, end_date, procurador_names
                )
                if metricas:
                    pdf_bytes = gerar_relatorio_pdf(metricas, mes, ano)
                    mes_nome = MESES_NOME.get(mes, str(mes))
                    nome_arquivo = f"Relatorio_Produtividade_{mes_nome}_{ano}.pdf"
                    zf.writestr(nome_arquivo, pdf_bytes)
                    meses_gerados += 1
            except Exception as e:
                print(f"Erro ao gerar relatório de {mes}/{ano}: {e}")

        if meses_gerados == 0:
            zf.writestr("AVISO.txt", f"Nenhum dado encontrado para o ano {ano}.")

    buffer.seek(0)
    return buffer.getvalue()
