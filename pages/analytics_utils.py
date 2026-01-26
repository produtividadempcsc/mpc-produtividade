
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
        
    # Vectorized operations where possible or optimized apply
    # Nota: calculate_calendar_days_minus_leave complexidade encapsulada no utils
    # Idealmente, mover lógica temporal para vetorização se possível no futuro
    
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

def create_metric_card(value, label, icon="📊"):
    return f"""
    <div class="metric-card">
        <div class="metric-value">{icon} {value}</div>
        <div class="metric-label">{label}</div>
    </div>
    """

def plot_bar_chart(df, x_col, y_col, color_col, title, orientation='h'):
    fig = px.bar(
        df, x=x_col, y=y_col, color=color_col,
        orientation=orientation, title=title,
        color_discrete_sequence=px.colors.qualitative.Vivid,
        text=x_col if orientation=='h' else y_col
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        font_color='#1e293b', title_font_size=16
    )
    fig.update_traces(textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

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
            st.plotly_chart(fig, use_container_width=True)
        elif chart_type == "Linha":
            st.line_chart(data)
        else:
            st.area_chart(data)
            
        with st.expander("Ver dados"):
            st.dataframe(df_display, use_container_width=True, hide_index=True)
            
    elif isinstance(data, pd.DataFrame):
        if data.empty:
            st.info("Sem dados.")
            return
            
        if chart_type == "Barra":
            # Assume formato pivot table ou similar
            # Melt para formato long se necessário, mas pivot table já vem "wide" para index
            # Se index for periodo, plotamos
            st.bar_chart(data)
        elif chart_type == "Linha":
            st.line_chart(data)
        else:
            st.area_chart(data)
            
        with st.expander("Ver dados"):
            st.dataframe(data, use_container_width=True)
