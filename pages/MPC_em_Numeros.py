import auth
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from sidebar import build_sidebar
from supabase_client import QueryBuilder
from db_compat import get_all_product_types, get_all_users, calculate_due_date
from utils.timezone import today_brazil
from utils.analytics_utils import (
    prepare_master_dataframe, calculate_metrics_servidor, 
    calculate_metrics_chefe, calculate_acervo_snapshot
)
import ui_utils

# Helper function definition needed for calculation
def calculate_due_date_safe(row):
    return calculate_due_date(
        start_date=row['data_atribuicao_servidor'].date(),
        prazo_dias=row['prazo_servidor_aplicado'],
        tipo_contagem=row['tipo_contagem_prazo'],
        id_usuario=row['id_servidor_responsavel'],
        dias_suspensos=row.get('prazo_total_dias_suspenso', 0)
    )

# --- Guarda de Autenticação ---
auth.auth_guard()

# --- Cláusula de Guarda de Perfil ---
allowed_profiles = ["Procurador", "Administrador"]
current_profile = st.session_state.get("active_perfil")

if current_profile not in allowed_profiles:
    st.error("🚫 Acesso restrito a Procuradores e Administradores.")
    st.stop()

st.set_page_config(
    page_title="MPC em Números - Visão Global",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carregar CSS do sistema
ui_utils.load_css()

# CSS customizado para a página
st.markdown('''
<style>
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #ffffff, #f8f9fa);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-left: 4px solid #0D47A1;
        transition: all 0.3s ease;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(13, 71, 161, 0.15);
    }
    
    .section-title {
        background: linear-gradient(90deg, #0D47A1, transparent);
        padding: 12px 20px;
        border-radius: 10px;
        color: white;
        font-weight: 600;
        font-size: 1.2em;
        margin: 25px 0 15px 0;
    }
    
    [data-testid="stPlotlyChart"] {
        background: white;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    
    /* Loading Screen Animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.98); }
    }
    
    .loading-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 60px 20px;
        background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
        border-radius: 20px;
        margin: 20px 0;
    }
    
    .loading-spinner {
        width: 60px;
        height: 60px;
        border: 4px solid #f3f3f3;
        border-top: 4px solid #0D47A1;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin-bottom: 20px;
    }
    
    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }
</style>
''', unsafe_allow_html=True)

st.session_state.active_page = "MPC em Números"
build_sidebar()

# --- Header Principal ---
st.markdown('''
<div style="background: linear-gradient(135deg, #0D47A1 0%, #1976D2 100%); color: white; padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 30px; box-shadow: 0 8px 30px rgba(13, 71, 161, 0.35);">
    <h1 style="margin: 0; font-size: 2.4em; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">🏛️ MPC em Números</h1>
    <p style="margin: 12px 0 0 0; font-size: 1.15em; opacity: 0.95; font-weight: 400;">Visão Estratégica Global do Ministério Público de Contas</p>
</div>
''', unsafe_allow_html=True)

# --- Placeholder para Loading ---
loading_placeholder = st.empty()

@st.cache_data(ttl=300, show_spinner=False)
def load_global_data():
    """Carrega TODOS os processos do MPC."""
    
    processos_cols = "id,status_servidor,status_chefe,id_servidor_responsavel,id_chefe_gabinete,id_procurador,id_tipo_produto,data_atribuicao_servidor,data_conclusao_servidor,data_conclusao_chefe,data_finalizacao,prazo_servidor_aplicado,prazo_chefe_aplicado,prazo_total_dias_suspenso,nao_se_aplica_prazo_servidor,ignorar_revisao_chefe,ignorar_analise_procurador,processo_numero"
    
    # Sem filtro de procurador = Global
    processos = QueryBuilder("processos") \
        .select(processos_cols) \
        .execute()
        
    tipos = QueryBuilder("tipos_produto") \
        .select("id,nome_produto,tipo_contagem_prazo") \
        .execute()
        
    users = get_all_users()
    
    return processos, tipos, users

# Mostrar loading
loading_placeholder.markdown('''
<div class="loading-container">
    <div class="loading-spinner"></div>
    <div class="loading-text">🌍 Consolidando dados de todo o MPC...</div>
</div>
''', unsafe_allow_html=True)

raw_processos, raw_tipos, all_users_list = load_global_data()

loading_placeholder.empty()

if not raw_processos:
    st.info("Nenhum processo encontrado no banco de dados.")
    st.stop()

# --- Preparação dos Dados ---
usuarios_dict = {u['id']: u for u in all_users_list}
tipos_dict = {t['id']: t for t in raw_tipos}

# DataFrame Master Global
df_master = prepare_master_dataframe(raw_processos, usuarios_dict, tipos_dict)

# Métrica segura: garantir que colunas numéricas não tenham NaN
cols_numericas = ['prazo_total_dias_suspenso', 'prazo_servidor_aplicado', 'prazo_chefe_aplicado']
for col in cols_numericas:
    if col in df_master.columns:
        df_master[col] = df_master[col].fillna(0)

# --- Filtros Globais ---
st.markdown("### 🎯 Filtros Globais")

col1, col2, col3 = st.columns(3)

with col1:
    hoje = today_brazil()
    data_inicio_padrao = date(2024, 1, 1)
    data_fim_padrao = date(hoje.year, 12, 31)
    
    f_ini = st.date_input("📅 Data Início", value=data_inicio_padrao, format="DD/MM/YYYY")

with col2:
    f_fim = st.date_input("📅 Data Fim", value=data_fim_padrao, format="DD/MM/YYYY")

with col3:
    tipos_unicos = sorted(df_master['nome_produto'].dropna().unique().tolist())
    filtro_tipos = st.multiselect("📝 Tipo de Processo", options=tipos_unicos)

# --- Filtragem Base ---
df_servidor_calc = calculate_metrics_servidor(df_master)
df_chefe_calc = calculate_metrics_chefe(df_master)

if filtro_tipos:
    df_master = df_master[df_master['nome_produto'].isin(filtro_tipos)]
    df_servidor_calc = df_servidor_calc[df_servidor_calc['nome_produto'].isin(filtro_tipos)]
    df_chefe_calc = df_chefe_calc[df_chefe_calc['nome_produto'].isin(filtro_tipos)]

# Filtro de Data para Métricas de Fluxo
df_concluidos_servidor = df_servidor_calc[
    (df_servidor_calc['data_conclusao_servidor'].dt.date >= f_ini) &
    (df_servidor_calc['data_conclusao_servidor'].dt.date <= f_fim)
]

df_concluidos_chefe = df_chefe_calc[
    (df_chefe_calc['data_conclusao_chefe'].dt.date >= f_ini) &
    (df_chefe_calc['data_conclusao_chefe'].dt.date <= f_fim)
]

# Processos Finalizados
df_master['data_finalizacao'] = pd.to_datetime(df_master['data_finalizacao'], errors='coerce')
df_finalizados = df_master[
    (df_master['data_finalizacao'].dt.date >= f_ini) &
    (df_master['data_finalizacao'].dt.date <= f_fim)
]

# --- Cálculo dos KPIs Globais ---

# 1. Processos Registrados (Entradas)
df_entradas = df_master[
    (df_master['data_atribuicao_servidor'].dt.date >= f_ini) &
    (df_master['data_atribuicao_servidor'].dt.date <= f_fim)
]
kpi_registrados = len(df_entradas)

# 2. Concluídos Servidores
kpi_conc_serv = len(df_concluidos_servidor)

# 3. Revisados Chefe
kpi_rev_chefe = len(df_concluidos_chefe)

# 4. Aprovados Procurador
kpi_aprov_proc = len(df_finalizados)

# 5. Acervo Total (Em Aberto AGORA)
now_ts = pd.Timestamp.now()
acervo_s_now, acervo_c_now = calculate_acervo_snapshot(df_master, now_ts)
kpi_acervo_total = len(acervo_s_now) + len(acervo_c_now)

# 6. Percentual Prazo Global
pct_prazo_serv = (df_concluidos_servidor['no_prazo_servidor'].sum() / kpi_conc_serv * 100) if kpi_conc_serv > 0 else 0
pct_prazo_chefe = (df_concluidos_chefe['revisao_no_prazo'].sum() / kpi_rev_chefe * 100) if kpi_rev_chefe > 0 else 0

# 7. Tempo Médio Global
tm_serv = df_concluidos_servidor['duracao_servidor'].mean() if not df_concluidos_servidor.empty else 0
tm_chefe = df_concluidos_chefe['duracao_revisao_chefe'].mean() if not df_concluidos_chefe.empty else 0


st.markdown("### 📈 KPIs Globais do MPC")

# Grid 3x3
k1, k2, k3 = st.columns(3)
k4, k5, k6 = st.columns(3)
k7, k8, k9 = st.columns(3)

with k1: st.metric("📥 Processos Registrados (Entradas)", kpi_registrados, help="Total MPC")
with k2: st.metric("✅ Concluídos por Servidores", kpi_conc_serv, help="Total MPC")
with k3: st.metric("👀 Processos Revisados (Chefes)", kpi_rev_chefe, help="Total MPC")

with k4: st.metric("⚖️ Aprovados pelo Procurador", kpi_aprov_proc, help="Total MPC")
with k5: st.metric("📂 Acervo Total em Tramitação", kpi_acervo_total, help="Total Ativo no MPC Agora")
with k6: st.metric("🎯 % Revisão no Prazo (Chefes)", f"{pct_prazo_chefe:.1f}%", help="Média Global MPC")

with k7: st.metric("⏱️ Tempo Médio (Servidores)", f"{tm_serv:.1f} dias", help="Média Global MPC")
with k8: st.metric("⏱️ Tempo Médio de Revisão (Chefes)", f"{tm_chefe:.1f} dias", help="Média Global MPC")
with k9: st.metric("🎯 % Conclusão no Prazo (Serv)", f"{pct_prazo_serv:.1f}%", help="Média Global MPC")

st.markdown("---")

# --- CONTEXTO 1: SERVIDORES ---
st.markdown("## 🧑‍💻 Visão por Servidores (Todo o MPC)")

if not df_concluidos_servidor.empty:
    grp_serv = df_concluidos_servidor.groupby('servidor_nome').agg(
        concluidos=('id', 'count'),
        no_prazo=('no_prazo_servidor', 'sum'),
        tempo_medio=('duracao_servidor', 'mean')
    ).reset_index()
    
    grp_serv['pct_prazo'] = (grp_serv['no_prazo'] / grp_serv['concluidos'] * 100).fillna(0)
    
    c_s1, c_s2 = st.columns(2)
    
    with c_s1:
        st.markdown("#### 🏆 Produtividade (Servidores)")
        fig1 = px.bar(
            grp_serv, x='concluidos', y='servidor_nome', orientation='h',
            text='concluidos',
            color='pct_prazo', color_continuous_scale='RdYlGn', range_color=[0, 100],
            labels={'concluidos': 'Processos', 'servidor_nome': 'Servidor', 'pct_prazo': '% Prazo'}
        )
        fig1.update_layout(yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig1, width="stretch")

    with c_s2:
        st.markdown("#### ⏱️ Tempo Médio (Servidores)")
        fig2 = px.bar(
            grp_serv, x='tempo_medio', y='servidor_nome', orientation='h',
            text=grp_serv['tempo_medio'].apply(lambda x: f"{x:.1f}d"),
            color='tempo_medio', color_continuous_scale='Reds',
            labels={'tempo_medio': 'Dias', 'servidor_nome': 'Servidor'}
        )
        fig2.update_layout(yaxis={'categoryorder': 'total descending'}, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig2, width="stretch")

    # Gráfico Distribuído (Concluído vs Aberto) - Servidores
    st.markdown("#### 📊 Processos Distribuídos (Servidores)")
    
    df_chart_acervo_s = acervo_s_now.groupby('servidor_nome').size().reset_index(name='Em Aberto')
    df_chart_concluidos_s = grp_serv[['servidor_nome', 'concluidos']].rename(columns={'concluidos': 'Concluídos'})
    
    df_dist_s = pd.merge(df_chart_concluidos_s, df_chart_acervo_s, on='servidor_nome', how='outer').fillna(0)
    df_dist_s['Total'] = df_dist_s['Concluídos'] + df_dist_s['Em Aberto']
    df_dist_s = df_dist_s.sort_values('Total', ascending=True)
    
    df_dist_s_long = df_dist_s.melt(id_vars=['servidor_nome', 'Total'], value_vars=['Concluídos', 'Em Aberto'], 
                                var_name='Estado', value_name='Quantidade')
    
    fig3 = px.bar(
        df_dist_s_long, y='servidor_nome', x='Quantidade', color='Estado', orientation='h',
        color_discrete_map={'Concluídos': '#28a745', 'Em Aberto': '#dc3545'},
        labels={'servidor_nome': 'Servidor'}
    )
    # Adicionar Totais
    fig3.add_trace(go.Scatter(
        y=df_dist_s['servidor_nome'], x=df_dist_s['Total'],
        text=df_dist_s['Total'].apply(lambda x: str(int(x))),
        mode='text', textposition='middle right', showlegend=False,
        textfont=dict(color='black', size=12)
    ))
    fig3.update_layout(xaxis_range=[0, df_dist_s['Total'].max() * 1.15], plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig3, width="stretch")
else:
    st.info("Sem dados de conclusão de sevidores.")

st.markdown("---")

# --- CONTEXTO 2: CHEFES DE GABINETE ---
st.markdown("## 👔 Visão por Chefes de Gabinete (Todo o MPC)")

if not df_concluidos_chefe.empty:
    grp_chefe = df_concluidos_chefe.groupby('chefe_gabinete_nome').agg(
        revisados=('id', 'count'),
        no_prazo=('revisao_no_prazo', 'sum'),
        tempo_medio=('duracao_revisao_chefe', 'mean')
    ).reset_index()
    
    grp_chefe['pct_prazo'] = (grp_chefe['no_prazo'] / grp_chefe['revisados'] * 100).fillna(0)
    
    c_c1, c_c2 = st.columns(2)
    
    with c_c1:
        st.markdown("#### 🏆 Produtividade (Chefes)")
        fig4 = px.bar(
            grp_chefe, x='revisados', y='chefe_gabinete_nome', orientation='h',
            text='revisados',
            color='pct_prazo', color_continuous_scale='RdYlGn', range_color=[0, 100],
            labels={'revisados': 'Processos Revisados', 'chefe_gabinete_nome': 'Chefe', 'pct_prazo': '% Prazo'}
        )
        fig4.update_layout(yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig4, width="stretch")

    with c_c2:
        st.markdown("#### ⏱️ Tempo Médio (Chefes)")
        fig5 = px.bar(
            grp_chefe, x='tempo_medio', y='chefe_gabinete_nome', orientation='h',
            text=grp_chefe['tempo_medio'].apply(lambda x: f"{x:.1f}d"),
            color='tempo_medio', color_continuous_scale='Reds',
            labels={'tempo_medio': 'Dias', 'chefe_gabinete_nome': 'Chefe'}
        )
        fig5.update_layout(yaxis={'categoryorder': 'total descending'}, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig5, width="stretch")

    # Gráfico Distribuído Chefes (Revisados vs Pendentes de Revisão)
    # Pendentes de Revisão = Acervo Chefes (já concluídos por servidores mas não revisados)
    st.markdown("#### 📊 Processos Recebidos e Revisados (Chefes)")
    
    df_chart_acervo_c = acervo_c_now.groupby('chefe_gabinete_nome').size().reset_index(name='Pendente Revisão')
    df_chart_revisados = grp_chefe[['chefe_gabinete_nome', 'revisados']].rename(columns={'revisados': 'Revisados'})
    
    df_dist_c = pd.merge(df_chart_revisados, df_chart_acervo_c, on='chefe_gabinete_nome', how='outer').fillna(0)
    df_dist_c['Total'] = df_dist_c['Revisados'] + df_dist_c['Pendente Revisão']
    df_dist_c = df_dist_c.sort_values('Total', ascending=True)
    
    df_dist_c_long = df_dist_c.melt(id_vars=['chefe_gabinete_nome', 'Total'], value_vars=['Revisados', 'Pendente Revisão'], 
                                var_name='Estado', value_name='Quantidade')
    
    fig6 = px.bar(
        df_dist_c_long, y='chefe_gabinete_nome', x='Quantidade', color='Estado', orientation='h',
        color_discrete_map={'Revisados': '#28a745', 'Pendente Revisão': '#ffc107'},
        labels={'chefe_gabinete_nome': 'Chefe'}
    )
    # Totais
    fig6.add_trace(go.Scatter(
        y=df_dist_c['chefe_gabinete_nome'], x=df_dist_c['Total'],
        text=df_dist_c['Total'].apply(lambda x: str(int(x))),
        mode='text', textposition='middle right', showlegend=False,
        textfont=dict(color='black', size=12)
    ))
    fig6.update_layout(xaxis_range=[0, df_dist_c['Total'].max() * 1.15], plot_bgcolor='rgba(0,0,0,0)')
    st.plotly_chart(fig6, width="stretch")

else:
    st.info("Sem dados de revisão de chefes.")

st.markdown("---")

# --- HISTÓRICO DE ACERVO (Estratificado por Chefe) ---
st.markdown("### 📅 Evolução do Acervo (Por Chefe de Gabinete)")

dates_to_check = pd.date_range(start=f_ini, end=f_fim, freq='ME')

history_data = []

if len(dates_to_check) > 0:
    prog_bar = st.progress(0, text="Calculando histórico de acervo...")
    
    for i, date_ref in enumerate(dates_to_check):
        pct = int((i + 1) / len(dates_to_check) * 100)
        prog_bar.progress(pct, text=f"Calculando histórico: {date_ref.strftime('%m/%Y')}")
        
        # Snapshot na data
        acervo_s, acervo_c = calculate_acervo_snapshot(df_master, date_ref)
        
        # Agrupar acervo TOTAL (servidor + chefe) por CHEFE 
        # (Assumindo que cada processo tem um chefe responsável, mesmo se estiver com servidor)
        
        # Para processos com servidores, precisamos saber quem é o chefe deles (hierarquia)
        # OU usamos 'id_chefe_gabinete' que está no processo. O 'id_chefe_gabinete' costuma ser preenchido quando atribuído?
        # Sim, 'id_chefe_gabinete' deve estar no processo.
        
        # Vamos juntar os dois acervos (S e C) em um só para contar carga total do gabinete naquela data
        full_acervo = pd.concat([acervo_s, acervo_c])
        
        if not full_acervo.empty:
            # Agrupar por chefe_gabinete_nome (já enriquecido no prepare_master_dataframe)
            # Se prepare_master_dataframe não preencheu chefe_gabinete_nome para todos, pode ter NaN se o user nao existir no dict
            counts = full_acervo['chefe_gabinete_nome'].value_counts().reset_index()
            counts.columns = ['chefe_gabinete_nome', 'qtd']
            counts['data'] = date_ref
            history_data.append(counts)
            
    prog_bar.empty()
    
    if history_data:
        df_history = pd.concat(history_data)
        
        fig_hist = px.line(
            df_history, x='data', y='qtd', color='chefe_gabinete_nome', markers=True,
            title="Evolução do Acervo por Gabinete"
        )
        fig_hist.update_layout(plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified")
        st.plotly_chart(fig_hist, width="stretch")
    else:
        st.info("Sem dados históricos para exibir.")
else:
    st.warning("Selecione um intervalo maior.")

