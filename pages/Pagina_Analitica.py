
import auth
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from sidebar import build_sidebar
from supabase_client import QueryBuilder, select_all
from db_compat import get_all_users, get_all_product_types, get_direct_servants
from utils.analytics_utils import (
    prepare_master_dataframe, calculate_metrics_servidor, calculate_metrics_chefe,
    create_metric_card, format_and_plot, calculate_acervo_snapshot
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
    with st.spinner("🔄 Carregando dados completos... Isso pode levar alguns segundos."):
        
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

        # --- Carregar Dados Mestres (Fetch All) ---
        @st.cache_data(ttl=300, show_spinner=False)
        def load_processos_data(perfil, uid, s_ids, c_ids):
            """
            Carrega dados do Supabase com cache para performance.
            Argumentos simples (strings/listas) para chave de cache eficiente.
            """
            qb = QueryBuilder("processos")
            
            # Filtros de Perfil
            if perfil == "Servidor":
                qb.eq("id_servidor_responsavel", uid)
            elif perfil == "Chefe de Gabinete":
                qb.eq("id_chefe_gabinete", uid)
                
            # Filtros de Seleção (listas de IDs)
            if s_ids: qb.in_list("id_servidor_responsavel", s_ids)
            if c_ids: qb.in_list("id_chefe_gabinete", c_ids)
            
            return qb.fetch_all()

        # Preparar argumentos para cache key
        s_ids_param = [nomes_servidores[n] for n in filtro_servidor if n in nomes_servidores] if filtro_servidor else []
        c_ids_param = [nomes_chefes[n] for n in filtro_chefe if n in nomes_chefes] if filtro_chefe else []
        
        raw_data = load_processos_data(perfil_usuario, id_usuario, s_ids_param, c_ids_param)
        
        if not raw_data:
            st.warning("Nenhum dado encontrado.")
            st.stop()
            
        # Preparar DataFrames com Utils
        df_master = prepare_master_dataframe(raw_data, usuarios_dict, tipos_dict)
        
        # Calcular métricas específicas
        df_servidor = calculate_metrics_servidor(df_master)
        df_chefe = calculate_metrics_chefe(df_master)

        # Filtros de Data nos DataFrames Calculados (Para abas de Produtividade)
        df_servidor_filtered = pd.DataFrame()
        if not df_servidor.empty:
            df_servidor_filtered = df_servidor[
                (df_servidor['data_conclusao_servidor'].dt.date >= f_ini) &
                (df_servidor['data_conclusao_servidor'].dt.date <= f_fim)
            ]
            
        df_chefe_filtered = pd.DataFrame()
        if not df_chefe.empty:
            df_chefe_filtered = df_chefe[
                (df_chefe['data_conclusao_chefe'].dt.date >= f_ini) &
                (df_chefe['data_conclusao_chefe'].dt.date <= f_fim)
            ]

        # --- Renderização das Abas Completas ---
        tabs = st.tabs([
            "👤 Produtividade Servidor", 
            "🏢 Produtividade Gabinete", 
            "⚖️ Carga de Trabalho",
            "📊 Análise de Distribuição",
            "📚 Análise de Acervo",
            "↩️ Análise de Devoluções"
        ])
        
        # --- ABA 1: SERVIDOR ---
        with tabs[0]:
            st.header("Análise de Produtividade - Servidores")
            if df_servidor_filtered.empty:
                st.info("Sem dados de conclusão neste período.")
            else:
                c1, c2, c3 = st.columns(3)
                total = len(df_servidor_filtered)
                tempo_medio = df_servidor_filtered['duracao_servidor'].mean()
                no_prazo = (df_servidor_filtered['no_prazo_servidor'].sum() / total * 100) if total > 0 else 0
                
                c1.markdown(create_metric_card(f"{total}", "Concluídos", "📋"), unsafe_allow_html=True)
                c2.markdown(create_metric_card(f"{tempo_medio:.1f}", "Média Dias", "⏱️"), unsafe_allow_html=True)
                c3.markdown(create_metric_card(f"{no_prazo:.1f}%", "No Prazo", "✅"), unsafe_allow_html=True)
                
                # Gráficos
                if grouping == "Consolidado":
                    data = df_servidor_filtered.groupby('servidor_nome')['id'].count().sort_values()
                    format_and_plot(data, "Barra", "Processos por Servidor")
                else:
                    period = 'M' if grouping == "Mês a Mês" else 'Y'
                    df_servidor_filtered['periodo'] = df_servidor_filtered['data_conclusao_servidor'].dt.to_period(period).astype(str)
                    data = df_servidor_filtered.pivot_table(index='periodo', columns='servidor_nome', values='id', aggfunc='count').fillna(0)
                    format_and_plot(data, chart_type, "Evolução Temporal")

        # --- ABA 2: GABINETE ---
        with tabs[1]:
            st.header("Análise de Produtividade - Gabinetes")
            if df_chefe_filtered.empty:
                st.info("Sem dados de revisão neste período.")
            else:
                c1, c2, c3 = st.columns(3)
                total = len(df_chefe_filtered)
                tempo_medio = df_chefe_filtered['duracao_revisao_chefe'].mean()
                no_prazo = (df_chefe_filtered['revisao_no_prazo'].sum() / total * 100) if total > 0 else 0
                
                c1.markdown(create_metric_card(f"{total}", "Revisados", "📋"), unsafe_allow_html=True)
                c2.markdown(create_metric_card(f"{tempo_medio:.1f}", "Média Dias", "⏱️"), unsafe_allow_html=True)
                c3.markdown(create_metric_card(f"{no_prazo:.1f}%", "No Prazo", "✅"), unsafe_allow_html=True)
                
                if grouping == "Consolidado":
                    data = df_chefe_filtered.groupby('chefe_gabinete_nome')['id'].count().sort_values()
                    format_and_plot(data, "Barra", "Revisões por Gabinete")
                else:
                    period = 'M' if grouping == "Mês a Mês" else 'Y'
                    df_chefe_filtered['periodo'] = df_chefe_filtered['data_conclusao_chefe'].dt.to_period(period).astype(str)
                    data = df_chefe_filtered.pivot_table(index='periodo', columns='chefe_gabinete_nome', values='id', aggfunc='count').fillna(0)
                    format_and_plot(data, chart_type, "Evolução de Revisões")

        # --- ABA 3: CARGA DE TRABALHO (Atual) ---
        with tabs[2]:
            st.header("Carga de Trabalho Atual")
            
            # Processos Ativos Totais (Sem Data Conclusão Chefe ou Servidor)
            # Para carga atual, olhamos o "Retrato de Agora"
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

        # --- ABA 4: DISTRIBUIÇÃO ---
        with tabs[3]:
            st.header("Análise de Distribuição (Entrada)")
            st.caption("Processos que entraram (foram atribuídos) no período selecionado.")
            
            df_entrada = df_master[
                (df_master['data_atribuicao_servidor'].dt.date >= f_ini) &
                (df_master['data_atribuicao_servidor'].dt.date <= f_fim)
            ]
            
            if df_entrada.empty:
                st.info("Nenhuma distribuição no período.")
            else:
                st.metric("Total Distribuído", len(df_entrada))
                
                if grouping == "Consolidado":
                    data_serv = df_entrada['servidor_nome'].value_counts()
                    format_and_plot(data_serv, "Barra", "Distribuição por Servidor")
                    
                    data_chefe = df_entrada['chefe_gabinete_nome'].value_counts()
                    format_and_plot(data_chefe, "Barra", "Distribuição por Gabinete")
                else:
                    period = 'M' if grouping == "Mês a Mês" else 'Y'
                    df_entrada['periodo'] = df_entrada['data_atribuicao_servidor'].dt.to_period(period).astype(str)
                    
                    data = df_entrada.pivot_table(index='periodo', columns='servidor_nome', values='id', aggfunc='count').fillna(0)
                    format_and_plot(data, chart_type, "Evolução da Distribuição")
        
        # --- ABA 5: ACERVO (Retrato no Tempo) ---
        with tabs[4]:
            st.header("Análise de Acervo (Retrato Histórico)")
            st.caption("Como estava a fila de processos em uma data específica do passado.")
            
            data_ref = st.date_input("📅 Data de Referência", value=date.today())
            data_ref_ts = pd.to_datetime(data_ref)
            
            acervo_serv_snap, acervo_chefe_snap = calculate_acervo_snapshot(df_master, data_ref_ts)
            
            c1, c2 = st.columns(2)
            c1.metric(f"Acervo Servidores em {data_ref.strftime('%d/%m')}", len(acervo_serv_snap))
            c2.metric(f"Acervo Revisão em {data_ref.strftime('%d/%m')}", len(acervo_chefe_snap))
            
            if not acervo_serv_snap.empty:
                format_and_plot(acervo_serv_snap['servidor_nome'].value_counts(), "Barra", "Acervo por Servidor (Snapshot)")
                
            if not acervo_chefe_snap.empty:
                format_and_plot(acervo_chefe_snap['chefe_gabinete_nome'].value_counts(), "Barra", "Acervo por Gabinete (Snapshot)")

        # --- ABA 6: DEVOLUÇÕES ---
        with tabs[5]:
            st.header("Análise de Devoluções")
            st.caption("Processos que retornaram do Chefe para o Servidor.")
            
            # Buscar histórico de devoluções separadamente para não pesar a query principal se não precisar
            # Mas aqui faremos query específica
            qb_dev = QueryBuilder("processos_historico")
            qb_dev.eq("evento", "Devolvido pelo Chefe")
            # Filtrar por data do evento se possível, mas processes_histórico pode não ter data fácil de filtrar direto se for JSON
            # Assumindo coluna 'timestamp' ou 'created_at'
            # Vamos pegar tudo e filtrar no pandas por segurança se não soubermos o nome exato da coluna de data
            # Ajuste conforme seu schema real: 'created_at'
            
            with st.spinner("Buscando histórico de devoluções..."):
                hist_data = qb_dev.fetch_all() # Pode ser pesado, ideal filtrar por data
            
            if not hist_data:
                st.info("Nenhuma devolução registrada.")
            else:
                df_hist = pd.DataFrame(hist_data)
                df_hist['created_at'] = pd.to_datetime(df_hist['created_at'], errors='coerce') # Ajuste nome coluna se precisar
                
                # Filtrar período
                df_hist_filtered = df_hist[
                    (df_hist['created_at'].dt.date >= f_ini) &
                    (df_hist['created_at'].dt.date <= f_fim)
                ]
                
                if df_hist_filtered.empty:
                    st.info("Nenhuma devolução neste período.")
                else:
                    # Precisamos saber QUEM sofreu a devolução. O histórico tem id_processo.
                    # Join manual com df_master
                    df_join = df_hist_filtered.merge(
                        df_master[['id', 'servidor_nome', 'chefe_gabinete_nome']], 
                        left_on='id_processo', 
                        right_on='id', 
                        how='inner'
                    )
                    
                    st.metric("Total Devoluções", len(df_join))
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        format_and_plot(df_join['servidor_nome'].value_counts(), "Barra", "Devoluções por Servidor")
                    with c2:
                        format_and_plot(df_join['chefe_gabinete_nome'].value_counts(), "Barra", "Devoluções por Gabinete")
