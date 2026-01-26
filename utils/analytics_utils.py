
import pandas as pd
import streamlit as st
import plotly.express as px
from datetime import datetime, date
import db_compat as utils

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

def calculate_metrics_servidor(df):
    """
    Calcula métricas e colunas derivadas para análise dos servidores.
    """
    df = df.dropna(subset=['data_conclusao_servidor']).copy()
    if df.empty:
        return df
        
    df['duracao_servidor'] = df.apply(
        lambda row: utils.calculate_calendar_days_minus_leave(
            start_date=row['data_atribuicao_servidor'].date(),
            end_date=row['data_conclusao_servidor'].date(),
            id_usuario=row['id_servidor_responsavel']
        ), axis=1
    )

    df['dias_afastamento_periodo'] = df.apply(
        lambda row: utils.get_leave_days_for_period(
            id_usuario=row['id_servidor_responsavel'],
            start_date=row['data_atribuicao_servidor'].date(),
            end_date=row['data_conclusao_servidor'].date()
        ), axis=1
    )
    
    df['prazo_servidor_ajustado'] = df['prazo_servidor_aplicado'] + df['dias_afastamento_periodo']
    
    df['data_final_teorica'] = df.apply(
        lambda row: utils.calculate_due_date(
            start_date=row['data_atribuicao_servidor'].date(),
            prazo_dias=row['prazo_servidor_ajustado'],
            tipo_contagem=row['tipo_contagem_prazo'],
            id_usuario=row['id_servidor_responsavel'],
            dias_suspensos=row['prazo_total_dias_suspenso']
        ), axis=1
    )
    
    df['no_prazo_servidor'] = df['data_conclusao_servidor'].dt.date <= df['data_final_teorica']
    
    return df

def calculate_metrics_chefe(df):
    """
    Calcula métricas e colunas derivadas para análise dos chefes.
    """
    df = df.dropna(subset=['data_conclusao_chefe', 'data_conclusao_servidor']).copy()
    if df.empty:
        return df
        
    df['duracao_revisao_chefe'] = df.apply(
        lambda row: utils.calculate_calendar_days_minus_leave(
            start_date=row['data_conclusao_servidor'].date(),
            end_date=row['data_conclusao_chefe'].date(),
            id_usuario=row['id_chefe_gabinete']
        ), axis=1
    )
    
    df['dias_afastamento_periodo_chefe'] = df.apply(
        lambda row: utils.get_leave_days_for_period(
            id_usuario=row['id_chefe_gabinete'],
            start_date=row['data_conclusao_servidor'].date(),
            end_date=row['data_conclusao_chefe'].date()
        ), axis=1
    )
    
    df['prazo_chefe_ajustado'] = df['prazo_chefe_aplicado'] + df['dias_afastamento_periodo_chefe']
    
    df['data_final_revisao_teorica'] = df.apply(
        lambda row: utils.calculate_due_date(
            start_date=row['data_conclusao_servidor'].date(),
            prazo_dias=row['prazo_chefe_ajustado'],
            tipo_contagem=row['tipo_contagem_prazo'],
            id_usuario=row['id_chefe_gabinete'],
            dias_suspensos=row['prazo_total_dias_suspenso']
        ), axis=1
    )
    
    df['revisao_no_prazo'] = df['data_conclusao_chefe'].dt.date <= df['data_final_revisao_teorica']
    
    return df

def calculate_acervo_snapshot(df, data_ref_ts):
    """
    Calcula o estado do acervo em uma data de referência específica.
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()
        
    # Acervo Servidores: Atribuído <= data_ref E (Sem Conclusão OU Concluído > data_ref)
    acervo_serv = df[
        (df['data_atribuicao_servidor'] <= data_ref_ts) &
        ( (df['data_conclusao_servidor'].isna()) | (df['data_conclusao_servidor'] > data_ref_ts) )
    ].copy()
    
    # Acervo Chefe: Concluido Servidor <= data_ref E (Sem Conclusão Chefe OU Concluido > data_ref)
    acervo_chefe = df[
        (df['data_conclusao_servidor'].notna()) &
        (df['data_conclusao_servidor'] <= data_ref_ts) &
        ( (df['data_conclusao_chefe'].isna()) | (df['data_conclusao_chefe'] > data_ref_ts) )
    ].copy()
    
    return acervo_serv, acervo_chefe

def prepare_devolucoes_dataframe(historico_data, usuarios_dict):
    """
    Processa dados históricos de devoluções.
    """
    if not historico_data:
        return pd.DataFrame()
        
    df = pd.DataFrame(historico_data)
    
    # Tenta mapear nomes, se as colunas de ID existirem no histórico ou precisar join manual
    # O histórico geralmente tem id_processo. Vamos assumir que recebemos dados já enriquecidos ou faremos join simples
    # Nesse caso, vamos simplificar assumindo que precisamos das contagens
    
    # Se o histórico vier raw, ele tem 'id_processo', precisamos saber quem era o responsável na época?
    # Geralmente a análise é "quantas devoluções ocorreram".
    
    # Vamos assumir que a view principal vai passar os dados filtrados
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
            st.plotly_chart(fig, width="stretch", key=title)
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
            # Para visualização temporal agrupada
            st.bar_chart(data)
        elif chart_type == "Linha":
            st.line_chart(data)
        else:
            st.area_chart(data)
            
        with st.expander("Ver dados"):
            st.dataframe(data, width=1500)
