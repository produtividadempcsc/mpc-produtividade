
import pandas as pd
import streamlit as st
import plotly.express as px

# Batch-friendly imports (avoid per-row DB calls)
from services.prazo_service import (
    calculate_net_work_days_batch,
    calculate_due_date_batch,
    calculate_net_duration_calendar_batch
)
from repositories.calendar_repository import get_all_holidays
from repositories.afastamento_repository import get_all_leave_dates_by_user

def prepare_master_dataframe(processos_data, usuarios_dict, tipos_dict):
    """
    Processa os dados brutos dos processos e retorna o DataFrame mestre enriquecido.
    """
    if not processos_data:
        return pd.DataFrame()
        
    df = pd.DataFrame(processos_data)
    
    # Mapeamentos
    df['servidor_nome'] = df['id_servidor_responsavel'].map(lambda x: usuarios_dict.get(x, {}).get('nome_completo', 'N/A'))
    df['chefe_gabinete_nome'] = df['id_chefe_gabinete'].map(lambda x: usuarios_dict.get(x, {}).get('nome_completo', 'N/A'))
    df['nome_produto'] = df['id_tipo_produto'].map(lambda x: tipos_dict.get(x, {}).get('nome_produto', 'N/A'))
    df['tipo_contagem_prazo'] = df['id_tipo_produto'].map(lambda x: tipos_dict.get(x, {}).get('tipo_contagem_prazo', 'dias uteis'))

    # Conversão de datas
    date_cols = ['data_atribuicao_servidor', 'data_conclusao_servidor', 'data_conclusao_chefe']
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors='coerce')
        
    return df


def _prefetch_batch_data(df):
    """
    Pré-carrega feriados e afastamentos de TODOS os usuários de uma só vez.
    Evita chamadas ao banco por linha (N queries → 2 queries).
    """
    feriados = get_all_holidays()
    leave_map = get_all_leave_dates_by_user()
    return feriados, leave_map


def calculate_metrics_servidor(df):
    """
    Calcula métricas e colunas derivadas para análise dos servidores.
    Otimizado: pré-carrega feriados e afastamentos uma única vez (batch).
    """
    df = df.dropna(subset=['data_atribuicao_servidor', 'data_conclusao_servidor']).copy()
    if df.empty:
        return df
    
    # Pré-carregar dados UMA VEZ (em vez de por linha)
    feriados, leave_map = _prefetch_batch_data(df)
        
    # Duração: respeita tipo de contagem (dias úteis vs corridos) e suspensões manuais
    def calc_duracao(row):
        uid = row['id_servidor_responsavel']
        af = leave_map.get(uid, set())
        if row.get('tipo_contagem_prazo') == 'dias uteis':
            return max(0, calculate_net_work_days_batch(
                row['data_atribuicao_servidor'].date(),
                row['data_conclusao_servidor'].date(),
                af, feriados
            ) - row.get('prazo_total_dias_suspenso', 0))
        else:
            return calculate_net_duration_calendar_batch(
                row['data_atribuicao_servidor'].date(),
                row['data_conclusao_servidor'].date(),
                af, row.get('prazo_total_dias_suspenso', 0)
            )
    
    df['duracao_servidor'] = df.apply(calc_duracao, axis=1)

    # Data-limite: batch version
    def calc_due(row):
        uid = row['id_servidor_responsavel']
        af = leave_map.get(uid, set())
        return calculate_due_date_batch(
            start_date=row['data_atribuicao_servidor'].date(),
            prazo_dias=row['prazo_servidor_aplicado'],
            tipo_contagem=row['tipo_contagem_prazo'],
            afastamentos_datas=af,
            feriados=feriados,
            dias_suspensos=row.get('prazo_total_dias_suspenso', 0)
        )
    
    df['data_final_teorica'] = df.apply(calc_due, axis=1)
    df['no_prazo_servidor'] = df['data_conclusao_servidor'].dt.date <= df['data_final_teorica']
    
    return df

def calculate_metrics_chefe(df):
    """
    Calcula métricas e colunas derivadas para análise dos chefes.
    Otimizado: pré-carrega feriados e afastamentos uma única vez (batch).
    """
    df = df.dropna(subset=['data_conclusao_chefe', 'data_conclusao_servidor']).copy()
    if df.empty:
        return df
    
    # Pré-carregar dados UMA VEZ
    feriados, leave_map = _prefetch_batch_data(df)
        
    # Duração revisão: respeita tipo de contagem e suspensões manuais
    def calc_duracao(row):
        uid = row['id_chefe_gabinete']
        af = leave_map.get(uid, set())
        
        # Start date: sempre usa data_conclusao_servidor (alinhado com relatorios.py)
        start_date = row['data_conclusao_servidor'].date()
        
        if row.get('tipo_contagem_prazo') == 'dias uteis':
            return max(0, calculate_net_work_days_batch(
                start_date,
                row['data_conclusao_chefe'].date(),
                af, feriados
            ) - row.get('prazo_total_dias_suspenso', 0))
        else:
            return calculate_net_duration_calendar_batch(
                start_date,
                row['data_conclusao_chefe'].date(),
                af, row.get('prazo_total_dias_suspenso', 0)
            )
    
    df['duracao_revisao_chefe'] = df.apply(calc_duracao, axis=1)
    
    # Duração total de produção (Métrica 9 do Relatório): data_atribuicao_servidor → data_conclusao_chefe
    # Combina afastamentos do servidor e do chefe (mesma lógica de relatorios.py _compute_chefe_metrics)
    def calc_duracao_total(row):
        uid_s = row['id_servidor_responsavel']
        uid_c = row['id_chefe_gabinete']
        af = leave_map.get(uid_s, set()).union(leave_map.get(uid_c, set()))
        if pd.isna(row.get('data_atribuicao_servidor')) or pd.isna(row.get('data_conclusao_chefe')):
            return None
        if row.get('tipo_contagem_prazo') == 'dias uteis':
            return max(0, calculate_net_work_days_batch(
                row['data_atribuicao_servidor'].date(),
                row['data_conclusao_chefe'].date(),
                af, feriados
            ) - row.get('prazo_total_dias_suspenso', 0))
        else:
            return calculate_net_duration_calendar_batch(
                row['data_atribuicao_servidor'].date(),
                row['data_conclusao_chefe'].date(),
                af, row.get('prazo_total_dias_suspenso', 0)
            )
    
    df['duracao_total_producao'] = df.apply(calc_duracao_total, axis=1)
    
    # Data-limite revisão: batch version
    def calc_due(row):
        uid = row['id_chefe_gabinete']
        af = leave_map.get(uid, set())
        # Alinhado com relatorios.py: sempre usa data_conclusao_servidor
        start_date = row['data_conclusao_servidor'].date()
        
        return calculate_due_date_batch(
            start_date=start_date,
            prazo_dias=row['prazo_chefe_aplicado'],
            tipo_contagem=row['tipo_contagem_prazo'],
            afastamentos_datas=af,
            feriados=feriados,
            dias_suspensos=row.get('prazo_total_dias_suspenso', 0)
        )
    
    df['data_final_revisao_teorica'] = df.apply(calc_due, axis=1)
    df['revisao_no_prazo'] = df['data_conclusao_chefe'].dt.date <= df['data_final_revisao_teorica']
    
    return df

def calculate_acervo_snapshot(df, data_ref_ts, filter_terminal_status=True):
    """
    Calcula o estado do acervo em uma data de referência específica.
    Alinhado com relatorios.py (Métricas 4 e 8).
    
    Args:
        filter_terminal_status: Se True, exclui processos com status terminal
            (Concluído/Finalizado). Usar True para snapshot atual, False para
            histórico (preserva consistência com relatórios já gerados).
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    # Acervo Servidores (Métrica 4 do relatório)
    mask_serv = (
        (df['data_atribuicao_servidor'] <= data_ref_ts) &
        (~df['nao_se_aplica_prazo_servidor'].fillna(False).astype(bool)) &
        (
            (df['data_conclusao_servidor'].isna()) |
            (df['data_conclusao_servidor'] > data_ref_ts)
        )
    )
    if filter_terminal_status and 'status_servidor' in df.columns:
        mask_serv = mask_serv & (~df['status_servidor'].isin(['Concluído', 'Finalizado']))
    
    acervo_serv = df[mask_serv].copy()
    
    # Acervo Chefe (Métrica 8 do relatório)
    mask_chefe = (
        (df['data_conclusao_servidor'] <= data_ref_ts) &
        (~df['ignorar_revisao_chefe'].fillna(False).astype(bool)) &
        (
            (df['data_conclusao_chefe'].isna()) |
            (df['data_conclusao_chefe'] > data_ref_ts)
        )
    )
    if filter_terminal_status and 'status_chefe' in df.columns:
        mask_chefe = mask_chefe & (~df['status_chefe'].isin(['Revisado', 'Finalizado']))
    
    acervo_chefe = df[mask_chefe].copy()
    
    return acervo_serv, acervo_chefe



def prepare_devolucoes_dataframe(historico_data, usuarios_dict):
    """
    Processa dados históricos de devoluções.
    """
    if not historico_data:
        return pd.DataFrame()
        
    df = pd.DataFrame(historico_data)
    return df

def create_metric_card(value, label, icon="📊"):
    return f"""
    <div class="metric-card">
        <div class="metric-value">{icon} {value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """

def format_and_plot(data, chart_type, title, icon="📈", description=""):
    st.markdown(f'<div class="section-header">{icon} {title}</div>', unsafe_allow_html=True)
    if description:
        st.caption(description)
        
    if isinstance(data, pd.Series):
        if data.empty:
            st.info("Sem dados.")
            return
        df_display = data.reset_index()
        df_display.columns = ["Nome", "Valor"]
        
        if chart_type == "Barra":
            fig = px.bar(
                df_display, x="Valor", y="Nome", orientation='h', text="Valor",
                color="Valor", color_continuous_scale='viridis'
            )
            fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
            st.plotly_chart(fig, use_container_width=True, key=title)
        elif chart_type == "Linha":
            st.line_chart(data)
        else:
            st.area_chart(data)
            
        with st.expander("Ver dados"):
            st.dataframe(df_display, width=1500, hide_index=True)
            
    elif isinstance(data, pd.DataFrame):
        if data.empty:
            st.info("Sem dados.")
            return
            
        if chart_type == "Barra":
            st.bar_chart(data)
        elif chart_type == "Linha":
            st.line_chart(data)
        else:
            st.area_chart(data)
            
        with st.expander("Ver dados"):
            st.dataframe(data, width=1500)
