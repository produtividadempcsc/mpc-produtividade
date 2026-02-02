import auth
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from sidebar import build_sidebar
from supabase_client import QueryBuilder, select_all
from db_compat import get_all_product_types
from utils.timezone import today_brazil
from utils.analytics_utils import (
    prepare_master_dataframe, calculate_metrics_servidor,
    create_metric_card, format_and_plot
)
import ui_utils
import plotly.express as px

# --- Guarda de Autenticação ---
auth.auth_guard()

# --- Cláusula de Guarda de Perfil ---
allowed_profiles = ["Servidor", "Chefe de Gabinete"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Apenas usuários com perfil 'Servidor' ou 'Chefe de Gabinete' podem acessar esta página.")
    st.stop()

st.set_page_config(
    page_title="Meus Dados - MPC/SC",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carregar CSS do sistema
ui_utils.load_css()

st.session_state.active_page = "Meus Dados"
build_sidebar()

# --- Header Principal ---
st.markdown('''
<div style="background: linear-gradient(135deg, #9E0520 0%, #B8062A 100%); color: white; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(158, 5, 32, 0.3);">
    <h1 style="margin: 0; font-size: 2.2em; font-weight: 700;">📊 Meus Dados</h1>
    <p style="margin: 10px 0 0 0; font-size: 1.1em; opacity: 0.9;">Painel de indicadores pessoais de produtividade</p>
</div>
''', unsafe_allow_html=True)

# --- Carregar Dados ---
with st.spinner("🔄 Carregando seus dados..."):
    user_id = st.session_state.user_id
    
    # Buscar processos do usuário
    all_user_processes = QueryBuilder("processos").eq("id_servidor_responsavel", user_id).execute()
    
    if not all_user_processes:
        st.info("📋 Você ainda não possui processos atribuídos.")
        st.stop()
    
    # Carregar dados auxiliares
    all_users = select_all("usuarios")
    usuarios_dict = {u['id']: u for u in all_users}
    all_types = get_all_product_types()
    tipos_dict = {t['id']: t for t in all_types}
    
    # Preparar DataFrame
    df_master = prepare_master_dataframe(all_user_processes, usuarios_dict, tipos_dict)

# --- Filtros ---
st.markdown("### 🎯 Filtros")

col1, col2, col3 = st.columns(3)

with col1:
    hoje = today_brazil()
    primeiro_dia_mes = date(hoje.year, hoje.month, 1)
    ultimo_dia_mes = (primeiro_dia_mes.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    
    f_ini = st.date_input("📅 Data Início", value=primeiro_dia_mes, format="DD/MM/YYYY")

with col2:
    f_fim = st.date_input("📅 Data Fim", value=ultimo_dia_mes, format="DD/MM/YYYY")

with col3:
    tipos_unicos = sorted(df_master['nome_produto'].dropna().unique().tolist())
    filtro_tipos = st.multiselect("📝 Tipo de Processo", options=tipos_unicos)

# --- Processar Dados ---
# Calcular métricas para servidor
df_servidor = calculate_metrics_servidor(df_master)

# Filtrar por período (processos concluídos no período)
df_filtered = pd.DataFrame()
if not df_servidor.empty:
    df_filtered = df_servidor[
        (df_servidor['data_conclusao_servidor'].dt.date >= f_ini) &
        (df_servidor['data_conclusao_servidor'].dt.date <= f_fim)
    ].copy()
    
    if filtro_tipos:
        df_filtered = df_filtered[df_filtered['nome_produto'].isin(filtro_tipos)]

# Buscar processos pendentes de revisão (concluídos pelo servidor, aguardando chefe)
processos_pendentes_revisao = [
    p for p in all_user_processes 
    if p.get('status_servidor') == 'Concluído' and p.get('status_chefe') in ['Aguardando Análise', 'Revisão Atrasada']
]

# Buscar devoluções
historico_devolucoes = []
try:
    # Buscar histórico de devoluções para processos do usuário
    process_ids = [p['id'] for p in all_user_processes]
    if process_ids:
        hist_data = QueryBuilder("processo_historico") \
            .eq("evento", "Devolvido pelo Chefe") \
            .in_list("id_processo", process_ids) \
            .execute()
        
        for h in hist_data:
            ts = h.get('timestamp') or h.get('created_at')
            if ts:
                try:
                    dt = datetime.fromisoformat(ts[:10]) if isinstance(ts, str) else ts
                    if isinstance(dt, datetime):
                        dt = dt.date()
                    if f_ini <= dt <= f_fim:
                        historico_devolucoes.append(h)
                except:
                    pass
except Exception as e:
    print(f"[MEUS_DADOS] Erro ao buscar devoluções: {e}")

total_devolucoes = len(historico_devolucoes)

# --- KPIs ---
st.markdown("### 📈 Indicadores do Período")

c1, c2, c3, c4, c5 = st.columns(5)

# Calcular KPIs
total_concluidos = len(df_filtered) if not df_filtered.empty else 0
tempo_medio = df_filtered['duracao_servidor'].mean() if not df_filtered.empty and 'duracao_servidor' in df_filtered.columns else 0
pct_no_prazo = (df_filtered['no_prazo_servidor'].sum() / total_concluidos * 100) if total_concluidos > 0 else 0
pendentes_revisao = len(processos_pendentes_revisao)

with c1:
    st.metric("✅ Concluídos", f"{total_concluidos}")

with c2:
    st.metric("⏱️ Tempo Médio", f"{tempo_medio:.1f} dias" if tempo_medio else "N/A")

with c3:
    st.metric("📊 No Prazo", f"{pct_no_prazo:.1f}%")

with c4:
    st.metric("🔍 Pendentes Revisão", f"{pendentes_revisao}")

with c5:
    st.metric("↩️ Devoluções", f"{total_devolucoes}")

st.markdown("---")

# --- Gráficos Mês a Mês ---
if not df_filtered.empty:
    st.markdown("### 📉 Evolução Mês a Mês")
    
    # Preparar dados mensais
    df_filtered['mes'] = df_filtered['data_conclusao_servidor'].dt.to_period('M').astype(str)
    
    # Gráfico 1: Processos Concluídos por Mês
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown("#### 📋 Processos Concluídos")
        concluidos_mes = df_filtered.groupby('mes').size().reset_index(name='Quantidade')
        if not concluidos_mes.empty:
            fig1 = px.bar(concluidos_mes, x='mes', y='Quantidade', 
                          color='Quantidade', color_continuous_scale='viridis',
                          text='Quantidade')
            fig1.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Mês",
                yaxis_title="Processos"
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")
    
    with col_g2:
        st.markdown("#### ⏱️ Tempo Médio (dias)")
        tempo_mes = df_filtered.groupby('mes')['duracao_servidor'].mean().reset_index(name='Tempo Médio')
        if not tempo_mes.empty:
            fig2 = px.line(tempo_mes, x='mes', y='Tempo Médio', markers=True)
            fig2.update_traces(line_color='#9E0520', line_width=3)
            fig2.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Mês",
                yaxis_title="Dias"
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")
    
    col_g3, col_g4 = st.columns(2)
    
    with col_g3:
        st.markdown("#### ✅ % Entrega no Prazo")
        prazo_mes = df_filtered.groupby('mes').agg(
            total=('id', 'count'),
            no_prazo=('no_prazo_servidor', 'sum')
        ).reset_index()
        prazo_mes['Percentual'] = (prazo_mes['no_prazo'] / prazo_mes['total'] * 100).fillna(0)
        
        if not prazo_mes.empty:
            fig3 = px.bar(prazo_mes, x='mes', y='Percentual',
                          color='Percentual', color_continuous_scale='RdYlGn',
                          text=prazo_mes['Percentual'].apply(lambda x: f'{x:.1f}%'))
            fig3.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Mês",
                yaxis_title="%"
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")
    
    with col_g4:
        st.markdown("#### ↩️ Devoluções por Mês")
        if historico_devolucoes:
            df_dev = pd.DataFrame(historico_devolucoes)
            df_dev['timestamp'] = pd.to_datetime(df_dev.get('timestamp', df_dev.get('created_at')), errors='coerce')
            df_dev['mes'] = df_dev['timestamp'].dt.to_period('M').astype(str)
            dev_mes = df_dev.groupby('mes').size().reset_index(name='Devoluções')
            
            fig4 = px.bar(dev_mes, x='mes', y='Devoluções',
                          color='Devoluções', color_continuous_scale='Reds',
                          text='Devoluções')
            fig4.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Mês",
                yaxis_title="Quantidade"
            )
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Nenhuma devolução no período.")
    
    st.markdown("---")
    
    # --- Gráfico Consolidado por Tipo de Processo ---
    st.markdown("### 📊 Distribuição por Tipo de Processo")
    
    tipos_count = df_filtered['nome_produto'].value_counts().reset_index()
    tipos_count.columns = ['Tipo', 'Quantidade']
    
    if not tipos_count.empty:
        fig5 = px.pie(tipos_count, values='Quantidade', names='Tipo',
                      color_discrete_sequence=px.colors.sequential.RdBu)
        fig5.update_traces(textposition='inside', textinfo='percent+label')
        fig5.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig5, use_container_width=True)
        
        with st.expander("📋 Ver dados detalhados"):
            st.dataframe(tipos_count, use_container_width=True, hide_index=True)
    else:
        st.info("Sem dados de tipos de processo para exibir.")

else:
    st.info("📋 Nenhum processo concluído no período selecionado. Ajuste os filtros de data.")
