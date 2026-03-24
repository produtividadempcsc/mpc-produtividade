import auth
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
from sidebar import build_sidebar
from supabase_client import QueryBuilder
from db_compat import get_all_users
from services.prazo_service import calculate_due_date
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

# CSS customizado para a página (agora centralizado)

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

# Adicionar nome do Procurador (Procuradoria de Contas)
df_master['procurador_nome'] = df_master['id_procurador'].map(
    lambda x: usuarios_dict.get(x, {}).get('nome_completo', 'N/A')
)

# Métrica segura: garantir que colunas numéricas não tenham NaN
cols_numericas = ['prazo_total_dias_suspenso', 'prazo_servidor_aplicado', 'prazo_chefe_aplicado']
for col in cols_numericas:
    if col in df_master.columns:
        df_master[col] = df_master[col].fillna(0)

# Mapeamento de meses para português
MESES_PT = {
    1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
    7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
}
def formatar_mes(dt):
    """Formata datetime para 'Jan/2025' etc."""
    return f"{MESES_PT[dt.month]}/{dt.year}"

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

f_ini_ts = pd.to_datetime(f_ini)
f_fim_ts = pd.to_datetime(f_fim)

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
    (df_servidor_calc['data_conclusao_servidor'].dt.normalize() >= f_ini_ts) &
    (df_servidor_calc['data_conclusao_servidor'].dt.normalize() <= f_fim_ts)
]

df_concluidos_chefe = df_chefe_calc[
    (df_chefe_calc['data_conclusao_chefe'].dt.normalize() >= f_ini_ts) &
    (df_chefe_calc['data_conclusao_chefe'].dt.normalize() <= f_fim_ts)
]

# --- Processos Produzidos (Ciclo Completo: Servidor + Chefe quando aplicável) ---
# Lógica alinhada com relatorios.py:
# - Se ignorar_revisao_chefe=True: produzido quando servidor conclui
# - Se ignorar_revisao_chefe=False: produzido quando chefe conclui a revisão

# Parte 1: Processos que pulam o chefe → data de produção = data_conclusao_servidor
df_prod_sem_chefe = df_servidor_calc[
    (df_servidor_calc['data_conclusao_servidor'].notna()) &
    (df_servidor_calc['ignorar_revisao_chefe'].fillna(False).astype(bool)) &
    (df_servidor_calc['data_conclusao_servidor'].dt.normalize() >= f_ini_ts) &
    (df_servidor_calc['data_conclusao_servidor'].dt.normalize() <= f_fim_ts)
].copy()
df_prod_sem_chefe['data_producao'] = df_prod_sem_chefe['data_conclusao_servidor'] if not df_prod_sem_chefe.empty else pd.NaT

# Parte 2: Processos revisados pelo chefe (excluindo os que pulam o chefe) → data de produção = data_conclusao_chefe
df_prod_com_chefe = df_concluidos_chefe[
    ~df_concluidos_chefe['ignorar_revisao_chefe'].fillna(False).astype(bool)
].copy()
df_prod_com_chefe['data_producao'] = df_prod_com_chefe['data_conclusao_chefe'] if not df_prod_com_chefe.empty else pd.NaT

# Combinar: produção total = processos sem chefe + processos com chefe (mutuamente exclusivos)
df_produzidos = pd.concat([df_prod_sem_chefe, df_prod_com_chefe], ignore_index=True)



# --- Cálculo dos KPIs Globais ---

# 1. Processos Registrados (Entradas)
df_master['data_atribuicao_servidor'] = pd.to_datetime(df_master['data_atribuicao_servidor'], errors='coerce')
df_entradas = df_master[
    (df_master['data_atribuicao_servidor'].dt.normalize() >= f_ini_ts) &
    (df_master['data_atribuicao_servidor'].dt.normalize() <= f_fim_ts)
]
kpi_registrados = len(df_entradas)

# 2. Concluídos Servidores
kpi_conc_serv = len(df_concluidos_servidor)

# 3. Revisados Chefe
kpi_rev_chefe = len(df_concluidos_chefe)



# 4. Acervo Servidores (Snapshot - Métrica 4 do Relatório)
now_ts = pd.Timestamp.now()
acervo_s_now, acervo_c_now = calculate_acervo_snapshot(df_master, now_ts)
kpi_acervo_servidores = len(acervo_s_now)

# 5. Acervo Chefes (Snapshot - Métrica 8 do Relatório)
kpi_acervo_chefes = len(acervo_c_now)

# 6. Percentual Prazo Global - Métricas 3 e 7 do Relatório
pct_prazo_serv = (df_concluidos_servidor['no_prazo_servidor'].sum() / kpi_conc_serv * 100) if kpi_conc_serv > 0 else 0
pct_prazo_chefe = (df_concluidos_chefe['revisao_no_prazo'].sum() / kpi_rev_chefe * 100) if kpi_rev_chefe > 0 else 0

# 7. Tempo Médio Global - Métricas 2 e 6 do Relatório
tm_serv = df_concluidos_servidor['duracao_servidor'].mean() if not df_concluidos_servidor.empty else 0
tm_chefe = df_concluidos_chefe['duracao_revisao_chefe'].mean() if not df_concluidos_chefe.empty else 0


st.markdown("### 📈 KPIs Globais do MPC")

# Grid de KPIs (alinhado com métricas do Relatório Mensal - 3x3)
k1, k2, k3 = st.columns(3)
k4, k5, k6 = st.columns(3)
k7, k8, k9 = st.columns(3)

with k1: st.metric("📥 Processos Registrados (Entradas)", kpi_registrados, help="Total MPC")
with k2: st.metric("✅ Concluídos por Servidores", kpi_conc_serv, help="Métrica 1 do Relatório Mensal — Total MPC")
with k3: st.metric("👀 Processos Revisados (Chefes)", kpi_rev_chefe, help="Métrica 5 do Relatório Mensal — Total MPC")

with k4: st.metric("📂 Acervo Servidores (Pendentes)", kpi_acervo_servidores, help="Métrica 4 do Relatório Mensal — processos não concluídos pelos servidores")
with k5: st.metric("📋 Acervo Chefes (Pend. Revisão)", kpi_acervo_chefes, help="Métrica 8 do Relatório Mensal — processos não revisados pelos chefes")
with k6: st.metric("⏱️ Tempo Médio (Servidores)", f"{tm_serv:.1f} dias", help="Métrica 2 do Relatório Mensal — Média Global MPC")

with k7: st.metric("⏱️ Tempo Médio de Revisão (Chefes)", f"{tm_chefe:.1f} dias", help="Métrica 6 do Relatório Mensal — Média Global MPC")
with k8: st.metric("🎯 % Conclusão no Prazo (Serv)", f"{pct_prazo_serv:.1f}%", help="Métrica 3 do Relatório Mensal — Média Global MPC")
with k9: st.metric("🎯 % Revisão no Prazo (Chefes)", f"{pct_prazo_chefe:.1f}%", help="Métrica 7 do Relatório Mensal — Média Global MPC")

st.markdown("---")

# ============================================================
# INDICADORES OFICIAIS DO MPC/SC
# ============================================================

st.markdown("## 📊 Indicadores Oficiais")

# --- INDICADOR 1: Produção por Ano e Mês (Ciclo Completo) ---
st.markdown("### 📅 Indicador 1 – Processos Produzidos por Ano e Mês")
st.caption("Consolidação da quantidade de processos e procedimentos produzidos no MPC/SC, por ano e por mês. Considera o ciclo completo: conclusão do servidor + revisão do chefe (quando aplicável).")

if not df_produzidos.empty:
    df_ind1 = df_produzidos.copy()
    df_ind1['ano'] = df_ind1['data_producao'].dt.year
    df_ind1['mes_num'] = df_ind1['data_producao'].dt.month
    df_ind1['mes_dt'] = df_ind1['data_producao'].dt.to_period('M').dt.to_timestamp()
    df_ind1['mes'] = df_ind1['data_producao'].apply(formatar_mes)

    # Agrupamento mensal
    prod_mes = df_ind1.groupby(['mes_dt', 'mes', 'ano']).size().reset_index(name='Quantidade')
    prod_mes = prod_mes.sort_values('mes_dt')

    fig_ind1 = px.bar(
        prod_mes, x='mes', y='Quantidade', color='ano',
        text='Quantidade',
        color_discrete_sequence=px.colors.qualitative.Set2,
        labels={'mes': 'Mês', 'Quantidade': 'Processos Produzidos', 'ano': 'Ano'}
    )
    fig_ind1.update_traces(textposition='outside')
    fig_ind1.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis={'categoryorder': 'array', 'categoryarray': prod_mes['mes'].tolist()},
        xaxis_title='Mês/Ano',
        yaxis_title='Processos Produzidos'
    )
    st.plotly_chart(fig_ind1, use_container_width=True)
else:
    st.info("Sem dados de produção para o período selecionado.")

st.markdown("---")

# --- INDICADOR 2: Produção por Procuradoria (Ciclo Completo) ---
st.markdown("### 🏛️ Indicador 2 – Processos Produzidos por Procuradoria de Contas")
st.caption("Consolidação da quantidade de processos e procedimentos produzidos no MPC/SC, por Procuradoria de Contas no período selecionado. Considera o ciclo completo.")

if not df_produzidos.empty:
    grp_proc = df_produzidos.groupby('procurador_nome').agg(
        produzidos=('id', 'count')
    ).reset_index()
    grp_proc = grp_proc.sort_values('produzidos', ascending=True)

    fig_ind2 = px.bar(
        grp_proc, x='produzidos', y='procurador_nome', orientation='h',
        text='produzidos',
        color='produzidos', color_continuous_scale='Blues',
        labels={'produzidos': 'Processos Produzidos', 'procurador_nome': 'Procuradoria'}
    )
    fig_ind2.update_traces(textposition='outside')
    fig_ind2.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title='Processos Produzidos',
        yaxis_title='Procuradoria de Contas'
    )
    st.plotly_chart(fig_ind2, use_container_width=True)
else:
    st.info("Sem dados de produção por Procuradoria.")

st.markdown("---")

# --- INDICADOR 3: Acervo Não Revisado pelo Chefe por Procuradoria/Mês ---
st.markdown("### 📦 Indicador 3 – Acervo Não Revisado por Procuradoria de Contas")
st.caption("Consolidação da quantidade de processos não revisados pelos chefes de gabinete, por Procuradoria de Contas do MPC/SC por mês. Alinhado com a Métrica 8 do Relatório Mensal.")

# ============================================================
# LOOP ÚNICO DE ACERVO HISTÓRICO (otimização: 24 iterações em vez de 72)
# Calcula snapshots para Procuradoria, Servidor e Chefe simultaneamente
# ============================================================
hoje_dt_hist = today_brazil()
# Garantir que o gráfico pare no mês corrente (não avance para meses futuros)
mes_atual_fim_hist = pd.Timestamp(hoje_dt_hist.replace(day=1)) + pd.offsets.MonthEnd(0)
dates_to_check_hist = pd.date_range(end=mes_atual_fim_hist, periods=24, freq='ME')
# Filtrar para não incluir datas futuras
dates_to_check_hist = dates_to_check_hist[dates_to_check_hist <= pd.Timestamp(hoje_dt_hist)]

history_proc = []   # Para Indicador 3 (Métrica 8 - Acervo Chefe por Procuradoria)
history_serv = []   # Para gráfico Servidor
history_chefe = []  # Para gráfico Chefe

if len(dates_to_check_hist) > 0:
    prog_hist = st.progress(0, text="Calculando histórico de acervo...")
    for i, date_ref in enumerate(dates_to_check_hist):
        pct = int((i + 1) / len(dates_to_check_hist) * 100)
        prog_hist.progress(pct, text=f"Histórico de acervo: {date_ref.strftime('%m/%Y')}")
        
        acervo_s, acervo_c = calculate_acervo_snapshot(df_master, date_ref, filter_terminal_status=False)
        
        # Indicador 3: Métrica 8 do Relatório — Acervo NÃO revisado pelo Chefe, por Procuradoria
        if not acervo_c.empty:
            counts_p = acervo_c.groupby('procurador_nome').size().reset_index(name='qtd')
            counts_p['data'] = date_ref
            history_proc.append(counts_p)
        
        # Agrupamento por Servidor (para gráfico posterior)
        if not acervo_s.empty:
            counts_s = acervo_s['servidor_nome'].value_counts().reset_index()
            counts_s.columns = ['servidor_nome', 'qtd']
            counts_s['data'] = date_ref
            history_serv.append(counts_s)
        
        # Agrupamento por Chefe (para gráfico posterior)
        if not acervo_c.empty:
            counts_c = acervo_c['chefe_gabinete_nome'].value_counts().reset_index()
            counts_c.columns = ['chefe_gabinete_nome', 'qtd']
            counts_c['data'] = date_ref
            history_chefe.append(counts_c)
    
    prog_hist.empty()

# Exibir Indicador 3 (Acervo Chefe por Procuradoria)
if history_proc:
    df_hist_proc = pd.concat(history_proc)
    fig_ind3 = px.line(
        df_hist_proc, x='data', y='qtd', color='procurador_nome', markers=True,
        labels={'data': 'Mês', 'qtd': 'Processos Não Revisados', 'procurador_nome': 'Procuradoria'}
    )
    fig_ind3.update_layout(
        plot_bgcolor='rgba(0,0,0,0)', hovermode='x unified',
        xaxis_title='Mês',
        yaxis_title='Processos em Estoque'
    )
    st.plotly_chart(fig_ind3, use_container_width=True)
else:
    st.info("Sem dados históricos de estoque por Procuradoria.")

st.markdown("---")

# --- INDICADOR 4: Produção por Tipo de Produto ---
st.markdown("### 📋 Indicador 4 – Processos por Tipo de Produto")
st.caption("Quantidade de processos ou procedimentos por tipo de produto/processo no MPC/SC no período selecionado.")

if not df_produzidos.empty:
    tipos_count = df_produzidos['nome_produto'].value_counts().reset_index()
    tipos_count.columns = ['Tipo de Produto', 'Quantidade']
    tipos_count = tipos_count.sort_values('Quantidade', ascending=True)

    fig_ind4 = px.bar(
        tipos_count, x='Quantidade', y='Tipo de Produto', orientation='h',
        text='Quantidade',
        color='Quantidade', color_continuous_scale='Blues',
        labels={'Quantidade': 'Processos Produzidos', 'Tipo de Produto': 'Tipo'}
    )
    fig_ind4.update_traces(textposition='outside')
    fig_ind4.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis={'categoryorder': 'total ascending'},
        showlegend=False,
        height=max(400, len(tipos_count) * 35),
        xaxis_title='Processos Produzidos',
        yaxis_title=''
    )
    st.plotly_chart(fig_ind4, use_container_width=True)
else:
    st.info("Sem dados de tipos de produto.")

st.markdown("---")

# --- INDICADOR 5: Tempo Médio de Produção Total por Procuradoria (Métrica 9 do Relatório) ---
st.markdown("### ⏱️ Indicador 5 – Tempo Médio de Produção por Procuradoria de Contas")
st.caption("Tempo médio de produção de produtos do MPC por Procuradoria de Contas. Considera o ciclo completo: da atribuição ao servidor até a revisão do chefe (Métrica 9 do Relatório Mensal).")

# Usar df_concluidos_chefe com duracao_total_producao (Métrica 9)
df_ind5 = df_concluidos_chefe.dropna(subset=['duracao_total_producao']).copy() if not df_concluidos_chefe.empty else pd.DataFrame()

if not df_ind5.empty:
    grp_tm_proc = df_ind5.groupby('procurador_nome').agg(
        tempo_medio=('duracao_total_producao', 'mean'),
        produzidos=('id', 'count')
    ).reset_index()
    grp_tm_proc = grp_tm_proc.sort_values('tempo_medio', ascending=True)

    fig_ind5 = px.bar(
        grp_tm_proc, x='tempo_medio', y='procurador_nome', orientation='h',
        text=grp_tm_proc['tempo_medio'].apply(lambda x: f"{x:.1f} dias"),
        color='tempo_medio', color_continuous_scale='RdYlGn_r',
        labels={'tempo_medio': 'Tempo Médio (Dias)', 'procurador_nome': 'Procuradoria', 'produzidos': 'Processos'},
        hover_data=['produzidos']
    )
    fig_ind5.update_traces(textposition='outside')
    fig_ind5.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis={'categoryorder': 'total ascending'},
        xaxis_title='Tempo Médio (Dias)',
        yaxis_title='Procuradoria de Contas'
    )
    st.plotly_chart(fig_ind5, use_container_width=True)
else:
    st.info("Sem dados de tempo médio por Procuradoria.")

st.markdown("---")

# ============================================================
# VISÕES DETALHADAS
# ============================================================
st.markdown("## 🧑‍💻 Visão por Servidores (Todo o MPC)")

if not df_concluidos_servidor.empty:
    grp_serv = df_concluidos_servidor.groupby('servidor_nome').agg(
        concluidos=('id', 'count'),
        no_prazo=('no_prazo_servidor', 'sum'),
        tempo_medio=('duracao_servidor', 'mean')
    ).reset_index()
    
    grp_serv['pct_prazo'] = (grp_serv['no_prazo'] / grp_serv['concluidos'] * 100).fillna(0)
    
    # --- Métrica 1: Número de processos concluídos pelos servidores ---
    st.markdown("### 🏆 Métrica 1 – Processos Concluídos por Servidor")
    st.caption("Número de processos concluídos pelos pareceristas no período selecionado.")
    grp_serv_sorted_conc = grp_serv.sort_values('concluidos', ascending=True)
    fig_s1 = px.bar(
        grp_serv_sorted_conc, x='concluidos', y='servidor_nome', orientation='h',
        text='concluidos',
        color='concluidos', color_continuous_scale='Blues',
        labels={'concluidos': 'Processos Concluídos', 'servidor_nome': 'Servidor'}
    )
    fig_s1.update_traces(textposition='outside')
    fig_s1.update_layout(
        yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False, height=max(400, len(grp_serv) * 35),
        xaxis_title='Processos Concluídos', yaxis_title=''
    )
    st.plotly_chart(fig_s1, use_container_width=True)
    
    st.markdown("---")

    # --- Métrica 2: Média de dias para concluir (Servidor) ---
    st.markdown("### ⏱️ Métrica 2 – Tempo Médio de Conclusão por Servidor")
    st.caption("Média de dias que os pareceristas demoraram para concluir o processo no período selecionado.")
    grp_serv_sorted_tm = grp_serv.sort_values('tempo_medio', ascending=True)
    fig_s2 = px.bar(
        grp_serv_sorted_tm, x='tempo_medio', y='servidor_nome', orientation='h',
        text=grp_serv_sorted_tm['tempo_medio'].apply(lambda x: f"{x:.1f} dias"),
        color='tempo_medio', color_continuous_scale='RdYlGn_r',
        labels={'tempo_medio': 'Tempo Médio (Dias)', 'servidor_nome': 'Servidor'}
    )
    fig_s2.update_traces(textposition='outside')
    fig_s2.update_layout(
        yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False, height=max(400, len(grp_serv) * 35),
        xaxis_title='Tempo Médio (Dias)', yaxis_title=''
    )
    st.plotly_chart(fig_s2, use_container_width=True)

    st.markdown("---")

    # --- Métrica 3: Percentual de processos concluídos no prazo (Servidor) ---
    st.markdown("### ✅ Métrica 3 – Percentual de Conclusão no Prazo por Servidor")
    st.caption("Percentual de processos concluídos pelos pareceristas dentro do prazo no período selecionado.")
    grp_serv_sorted_pct = grp_serv.sort_values('pct_prazo', ascending=True)
    fig_s3 = px.bar(
        grp_serv_sorted_pct, x='pct_prazo', y='servidor_nome', orientation='h',
        text=grp_serv_sorted_pct['pct_prazo'].apply(lambda x: f"{x:.1f}%"),
        color='pct_prazo', color_continuous_scale='RdYlGn', range_color=[0, 100],
        labels={'pct_prazo': '% No Prazo', 'servidor_nome': 'Servidor', 'concluidos': 'Total Concluídos'},
        hover_data=['concluidos']
    )
    fig_s3.update_traces(textposition='outside')
    fig_s3.update_layout(
        yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False, height=max(400, len(grp_serv) * 35),
        xaxis_title='% Concluídos no Prazo', yaxis_title='',
        xaxis_range=[0, 110]
    )
    st.plotly_chart(fig_s3, use_container_width=True)
else:
    st.info("Sem dados de conclusão de servidores.")

st.markdown("---")

# --- Métrica 4: Evolução do Acervo (Por Servidor) ---
st.markdown("### 📅 Métrica 4 – Evolução do Acervo por Servidor")
st.caption("Acervo de processos não concluídos ao encerrar o mês, por parecerista. Alinhado com a Métrica 4 do Relatório Mensal.")

# Usar dados já calculados no loop consolidado acima
if history_serv:
    df_history_s = pd.concat(history_serv)
    fig_hist_s = px.line(
        df_history_s, x='data', y='qtd', color='servidor_nome', markers=True,
        labels={'data': 'Mês', 'qtd': 'Processos em Acervo', 'servidor_nome': 'Servidor'}
    )
    fig_hist_s.update_layout(plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified",
                              xaxis_title='Mês', yaxis_title='Processos em Acervo')
    st.plotly_chart(fig_hist_s, use_container_width=True)
else:
    st.info("Sem dados históricos de servidores para exibir.")


# --- CONTEXTO 2: CHEFES DE GABINETE ---
st.markdown("## 👔 Visão por Chefes de Gabinete (Todo o MPC)")

if not df_concluidos_chefe.empty:
    grp_chefe = df_concluidos_chefe.groupby('chefe_gabinete_nome').agg(
        revisados=('id', 'count'),
        no_prazo=('revisao_no_prazo', 'sum'),
        tempo_medio=('duracao_revisao_chefe', 'mean')
    ).reset_index()
    
    grp_chefe['pct_prazo'] = (grp_chefe['no_prazo'] / grp_chefe['revisados'] * 100).fillna(0)
    
    # --- Métrica 5: Número de processos revisados pelo chefe ---
    st.markdown("### 🏆 Métrica 5 – Processos Revisados por Chefe de Gabinete")
    st.caption("Número de processos revisados no período selecionado, por chefe de gabinete.")
    grp_chefe_sorted_rev = grp_chefe.sort_values('revisados', ascending=True)
    fig_c5 = px.bar(
        grp_chefe_sorted_rev, x='revisados', y='chefe_gabinete_nome', orientation='h',
        text='revisados',
        color='revisados', color_continuous_scale='Blues',
        labels={'revisados': 'Processos Revisados', 'chefe_gabinete_nome': 'Chefe de Gabinete'}
    )
    fig_c5.update_traces(textposition='outside')
    fig_c5.update_layout(
        yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False, height=max(400, len(grp_chefe) * 35),
        xaxis_title='Processos Revisados', yaxis_title=''
    )
    st.plotly_chart(fig_c5, use_container_width=True)

    st.markdown("---")

    # --- Métrica 6: Média de dias de revisão (Chefe) ---
    st.markdown("### ⏱️ Métrica 6 – Tempo Médio de Revisão por Chefe de Gabinete")
    st.caption("Média de dias que os chefes de gabinete demoraram para finalizar a revisão do processo no período selecionado.")
    grp_chefe_sorted_tm = grp_chefe.sort_values('tempo_medio', ascending=True)
    fig_c6 = px.bar(
        grp_chefe_sorted_tm, x='tempo_medio', y='chefe_gabinete_nome', orientation='h',
        text=grp_chefe_sorted_tm['tempo_medio'].apply(lambda x: f"{x:.1f} dias"),
        color='tempo_medio', color_continuous_scale='RdYlGn_r',
        labels={'tempo_medio': 'Tempo Médio (Dias)', 'chefe_gabinete_nome': 'Chefe de Gabinete'}
    )
    fig_c6.update_traces(textposition='outside')
    fig_c6.update_layout(
        yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False, height=max(400, len(grp_chefe) * 35),
        xaxis_title='Tempo Médio (Dias)', yaxis_title=''
    )
    st.plotly_chart(fig_c6, use_container_width=True)

    st.markdown("---")

    # --- Métrica 7: Percentual de processos revisados no prazo (Chefe) ---
    st.markdown("### ✅ Métrica 7 – Percentual de Revisão no Prazo por Chefe de Gabinete")
    st.caption("Percentual de processos revisados pelos chefes de gabinete dentro do prazo no período selecionado.")
    grp_chefe_sorted_pct = grp_chefe.sort_values('pct_prazo', ascending=True)
    fig_c7 = px.bar(
        grp_chefe_sorted_pct, x='pct_prazo', y='chefe_gabinete_nome', orientation='h',
        text=grp_chefe_sorted_pct['pct_prazo'].apply(lambda x: f"{x:.1f}%"),
        color='pct_prazo', color_continuous_scale='RdYlGn', range_color=[0, 100],
        labels={'pct_prazo': '% No Prazo', 'chefe_gabinete_nome': 'Chefe de Gabinete', 'revisados': 'Total Revisados'},
        hover_data=['revisados']
    )
    fig_c7.update_traces(textposition='outside')
    fig_c7.update_layout(
        yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False, height=max(400, len(grp_chefe) * 35),
        xaxis_title='% Revisados no Prazo', yaxis_title='',
        xaxis_range=[0, 110]
    )
    st.plotly_chart(fig_c7, use_container_width=True)

else:
    st.info("Sem dados de revisão de chefes.")

st.markdown("---")

# --- Métrica 8: Evolução do Acervo (Por Chefe de Gabinete) ---
st.markdown("### 📅 Métrica 8 – Evolução do Acervo por Chefe de Gabinete")
st.caption("Acervo de processos não revisados ao encerrar o mês, por chefe de gabinete. Alinhado com a Métrica 8 do Relatório Mensal.")

# Usar dados já calculados no loop consolidado acima
if history_chefe:
    df_history_c = pd.concat(history_chefe)
    fig_hist_c = px.line(
        df_history_c, x='data', y='qtd', color='chefe_gabinete_nome', markers=True,
        labels={'data': 'Mês', 'qtd': 'Processos Não Revisados', 'chefe_gabinete_nome': 'Chefe de Gabinete'}
    )
    fig_hist_c.update_layout(plot_bgcolor='rgba(0,0,0,0)', hovermode="x unified",
                              xaxis_title='Mês', yaxis_title='Processos Não Revisados')
    st.plotly_chart(fig_hist_c, use_container_width=True)
else:
    st.info("Sem dados históricos para exibir.")

