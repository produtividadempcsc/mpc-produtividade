
import auth
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from sidebar import build_sidebar
from supabase_client import QueryBuilder
from db_compat import get_user_by_id, get_all_users, get_all_product_types, get_direct_servants
from pages.analytics_utils import (
    prepare_master_dataframe, calculate_metrics_servidor, calculate_metrics_chefe,
    create_metric_card, format_and_plot
)
import ui_utils

# --- Guarda e Configuração ---
auth.auth_guard()

st.set_page_config(
    page_title="Business Intelligence - MPC/SC",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carregar CSS
ui_utils.load_css()

st.session_state.active_page = "Página Analítica"
build_sidebar()

st.markdown('<h1 class="main-title">📊 Business Intelligence</h1>', unsafe_allow_html=True)
st.markdown('<p class="main-subtitle">Análise avançada de dados e indicadores de performance do MPC/SC</p>', unsafe_allow_html=True)

# --- Container Principal ---
with st.container():
    with st.spinner("🔄 Carregando e processando dados..."):
        
        # Contexto do Usuário
        perfil_usuario = st.session_state.active_perfil
        id_usuario = st.session_state.active_user_id
        
        # Carregar dados auxiliares
        all_users = get_all_users()
        usuarios_dict = {u['id']: u for u in all_users}
        all_types = get_all_product_types()
        tipos_dict = {t['id']: t for t in all_types}
        
        # --- Filtros Globais ---
        with st.expander("🎯 Filtros e Opções de Visualização", expanded=True):
            c1, c2 = st.columns(2)
            
            with c1:
                # Filtro de Servidor
                servidores_opts = [u for u in all_users if u.get('perfil') == "Servidor"]
                if perfil_usuario == "Chefe de Gabinete":
                    servidores_opts = get_direct_servants(id_usuario)
                
                nomes_servidores = {s['nome_completo']: s['id'] for s in servidores_opts}
                filtro_servidor = st.multiselect("👤 Servidores:", options=sorted(nomes_servidores.keys()))
                
                # Filtro de Chefe (apenas para Admins/Procuradores verem outros)
                chefes_opts = [u for u in all_users if u.get('perfil') == "Chefe de Gabinete"]
                nomes_chefes = {c['nome_completo']: c['id'] for c in chefes_opts}
                filtro_chefe = st.multiselect("👔 Chefes de Gabinete:", options=sorted(nomes_chefes.keys()))

            with c2:
                # Filtro de Data
                d_start = date(datetime.now().year, datetime.now().month, 1)
                last_day = d_start.replace(day=28) + timedelta(days=4)
                d_end = last_day - timedelta(days=last_day.day)
                
                cd1, cd2 = st.columns(2)
                f_ini = cd1.date_input("Início", value=d_start, format="DD/MM/YYYY")
                f_fim = cd2.date_input("Fim", value=d_end, format="DD/MM/YYYY")
                
                grouping = st.selectbox("Agrupar por:", ["Consolidado", "Mês a Mês", "Ano a Ano"])
                chart_type = st.selectbox("Gráfico:", ["Barra", "Linha", "Área"])

        # --- Carregar Dados Mestres ---
        qb = QueryBuilder("processos")
        
        # Filtros de Perfil na Query
        if perfil_usuario == "Servidor":
            qb.eq("id_servidor_responsavel", id_usuario)
        elif perfil_usuario == "Chefe de Gabinete":
            qb.eq("id_chefe_gabinete", id_usuario)
            
        # Filtros de Seleção na Query
        if filtro_servidor:
            ids = [nomes_servidores[n] for n in filtro_servidor if n in nomes_servidores]
            if ids: qb.in_list("id_servidor_responsavel", ids)
        if filtro_chefe:
            ids = [nomes_chefes[n] for n in filtro_chefe if n in nomes_chefes]
            if ids: qb.in_list("id_chefe_gabinete", ids)
            
        raw_data = qb.execute()
        
        if not raw_data:
            st.warning("Nenhum dado encontrado.")
            st.stop()
            
        # Preparar DataFrames com Utils
        df_master = prepare_master_dataframe(raw_data, usuarios_dict, tipos_dict)
        
        # Calcular métricas específicas
        df_servidor = calculate_metrics_servidor(df_master)
        df_chefe = calculate_metrics_chefe(df_master)

        # Filtros de Data nos DataFrames Calculados
        if not df_servidor.empty:
            df_servidor = df_servidor[
                (df_servidor['data_conclusao_servidor'].dt.date >= f_ini) &
                (df_servidor['data_conclusao_servidor'].dt.date <= f_fim)
            ]
            
        if not df_chefe.empty:
            df_chefe = df_chefe[
                (df_chefe['data_conclusao_chefe'].dt.date >= f_ini) &
                (df_chefe['data_conclusao_chefe'].dt.date <= f_fim)
            ]

        # --- Renderização das Abas ---
        tabs = st.tabs(["👤 Produtividade Servidor", "🏢 Produtividade Gabinete", "⚖️ Carga de Trabalho"])
        
        # --- ABA 1: SERVIDOR ---
        with tabs[0]:
            st.header("Análise de Produtividade - Servidores")
            if df_servidor.empty:
                st.info("Sem dados de conclusão neste período.")
            else:
                c1, c2, c3 = st.columns(3)
                total = len(df_servidor)
                tempo_medio = df_servidor['duracao_servidor'].mean()
                no_prazo = (df_servidor['no_prazo_servidor'].sum() / total * 100) if total > 0 else 0
                
                c1.markdown(create_metric_card(f"{total}", "Concluídos", "📋"), unsafe_allow_html=True)
                c2.markdown(create_metric_card(f"{tempo_medio:.1f}", "Média Dias", "⏱️"), unsafe_allow_html=True)
                c3.markdown(create_metric_card(f"{no_prazo:.1f}%", "No Prazo", "✅"), unsafe_allow_html=True)
                
                # Gráficos
                if grouping == "Consolidado":
                    data = df_servidor.groupby('servidor_nome')['id'].count().sort_values()
                    format_and_plot(data, "Barra", "Processos por Servidor")
                else:
                    period = 'M' if grouping == "Mês a Mês" else 'Y'
                    df_servidor['periodo'] = df_servidor['data_conclusao_servidor'].dt.to_period(period).astype(str)
                    data = df_servidor.pivot_table(index='periodo', columns='servidor_nome', values='id', aggfunc='count').fillna(0)
                    format_and_plot(data, chart_type, "Evolução Temporal")

        # --- ABA 2: GABINETE ---
        with tabs[1]:
            st.header("Análise de Produtividade - Gabinetes")
            if df_chefe.empty:
                st.info("Sem dados de revisão neste período.")
            else:
                c1, c2, c3 = st.columns(3)
                total = len(df_chefe)
                tempo_medio = df_chefe['duracao_revisao_chefe'].mean()
                no_prazo = (df_chefe['revisao_no_prazo'].sum() / total * 100) if total > 0 else 0
                
                c1.markdown(create_metric_card(f"{total}", "Revisados", "📋"), unsafe_allow_html=True)
                c2.markdown(create_metric_card(f"{tempo_medio:.1f}", "Média Dias", "⏱️"), unsafe_allow_html=True)
                c3.markdown(create_metric_card(f"{no_prazo:.1f}%", "No Prazo", "✅"), unsafe_allow_html=True)
                
                if grouping == "Consolidado":
                    data = df_chefe.groupby('chefe_gabinete_nome')['id'].count().sort_values()
                    format_and_plot(data, "Barra", "Revisões por Gabinete")
                else:
                    period = 'M' if grouping == "Mês a Mês" else 'Y'
                    df_chefe['periodo'] = df_chefe['data_conclusao_chefe'].dt.to_period(period).astype(str)
                    data = df_chefe.pivot_table(index='periodo', columns='chefe_gabinete_nome', values='id', aggfunc='count').fillna(0)
                    format_and_plot(data, chart_type, "Evolução de Revisões")

        # --- ABA 3: CARGA DE TRABALHO ---
        with tabs[2]:
            st.header("Carga de Trabalho Atual")
            
            # Processos Ativos (Sem Data Conclusão Chefe)
            df_ativos = df_master[pd.isna(df_master['data_conclusao_chefe'])].copy()
            
            if df_ativos.empty:
                st.success("Tudo em dia! Sem processos ativos.")
            else:
                # Separar etapas
                df_fase_servidor = df_ativos[pd.isna(df_ativos['data_conclusao_servidor'])].copy()
                df_fase_chefe = df_ativos[df_ativos['data_conclusao_servidor'].notna()].copy()
                
                c1, c2 = st.columns(2)
                c1.metric("Com Servidores", len(df_fase_servidor))
                c2.metric("Em Revisão", len(df_fase_chefe))
                
                st.subheader("Detalhamento por Responsável")
                
                if not df_fase_servidor.empty:
                    data_serv = df_fase_servidor['servidor_nome'].value_counts()
                    format_and_plot(data_serv, "Barra", "Processos com Servidores")
                    
                if not df_fase_chefe.empty:
                    data_chefe = df_fase_chefe['chefe_gabinete_nome'].value_counts()
                    format_and_plot(data_chefe, "Barra", "Processos em Revisão (Gabinete)")
