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
allowed_profiles = ["Chefe de Gabinete", "Procurador"]
current_profile = st.session_state.get("active_perfil")

if current_profile not in allowed_profiles:
    st.error("🚫 Acesso restrito a Chefes de Gabinete e Procuradores.")
    st.stop()

st.set_page_config(
    page_title="Gabinete em Números - MPC/SC",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Carregar CSS do sistema
ui_utils.load_css()

# CSS customizado para a página (agora centralizado)

st.session_state.active_page = "Gabinete em Números"
build_sidebar()

# --- Header Principal ---
st.markdown('''
<div style="background: linear-gradient(135deg, #9E0520 0%, #B8062A 100%); color: white; padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 30px; box-shadow: 0 8px 30px rgba(158, 5, 32, 0.35);">
    <h1 style="margin: 0; font-size: 2.4em; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">📊 Gabinete em Números</h1>
    <p style="margin: 12px 0 0 0; font-size: 1.15em; opacity: 0.95; font-weight: 400;">Visão consolidada de produtividade e carga de trabalho do gabinete</p>
</div>
''', unsafe_allow_html=True)

# --- Placeholder para Loading ---
loading_placeholder = st.empty()

# --- Identificação do Contexto (Hierarquia) ---
current_user_id = st.session_state.user_id

@st.cache_data(ttl=300, show_spinner=False)
def get_gabinete_context(user_id, profile, admin_target_id=None):
    """Identifica o Procurador alvo e todos os membros do gabinete."""
    target_procurador_id = None
    
    if profile == "Procurador":
        target_procurador_id = user_id
    elif profile == "Chefe de Gabinete":
        # Buscar procurador vinculado
        link = QueryBuilder("procurador_chefes").eq("chefe_id", user_id).execute()
        if link:
            target_procurador_id = link[0]['procurador_id']
    elif profile == "Administrador" and admin_target_id:
        target_procurador_id = admin_target_id
    
    if not target_procurador_id:
        return None, [], []
        
    # Buscar todos os chefes vinculados a este procurador
    chefes_links = QueryBuilder("procurador_chefes").eq("procurador_id", target_procurador_id).execute()
    chefes_ids = [c['chefe_id'] for c in chefes_links]
    
    # Buscar todos os servidores vinculados a estes chefes (ou diretamente ao gabinete se houver outra tabela, 
    # mas assumiremos a estrutura hierárquica via chefe->servidores ou todos do gabinete)
    # Estrutura comum: Procurador -> Chefes -> Servidores
    # Mas também precisamos pegar processos diretamente atribuídos
    
    # Vamos buscar TODOS os usuários e filtrar depois para garantir consistência
    all_users = get_all_users()
    
    # Filtrar membros relevantes
    # (Opcional: Refinar essa busca se o banco for muito grande)
    
    # Buscar servidores ATUALMENTE vinculados ao gabinete
    servidores_atuais_ids = []
    for chefe_id in chefes_ids:
        servs = QueryBuilder("gabinete_servidores").eq("chefe_id", chefe_id).execute()
        for s in servs:
            if s['servidor_id'] not in servidores_atuais_ids:
                servidores_atuais_ids.append(s['servidor_id'])
    
    return target_procurador_id, chefes_ids, all_users, servidores_atuais_ids

@st.cache_data(ttl=300, show_spinner=False)
def load_gabinete_data(procurador_id):
    """Carrega dados de processos para todo o gabinete do procurador."""
    if not procurador_id:
        return [], []
        
    # Buscar processos onde o procurador é o dono do gabinete
    # A tabela processos tem 'id_procurador' - isso facilita muito!
    # Não precisamos reconstruir a hierarquia complexa para buscar os processos, basta filtrar pelo id_procurador.
    
    processos_cols = "id,status_servidor,status_chefe,id_servidor_responsavel,id_chefe_gabinete,id_procurador,id_tipo_produto,data_atribuicao_servidor,data_conclusao_servidor,data_conclusao_chefe,data_finalizacao,prazo_servidor_aplicado,prazo_chefe_aplicado,prazo_total_dias_suspenso,nao_se_aplica_prazo_servidor,ignorar_revisao_chefe,ignorar_analise_procurador,processo_numero"
    
    processos = QueryBuilder("processos") \
        .eq("id_procurador", procurador_id) \
        .select(processos_cols) \
        .execute()
        
    tipos = QueryBuilder("tipos_produto") \
        .select("id,nome_produto,tipo_contagem_prazo") \
        .execute()
        
    return processos, tipos

# Mostrar loading
loading_placeholder.markdown('''
<div class="loading-container">
    <div class="loading-spinner"></div>
    <div class="loading-text">🔄 Consolidando dados do gabinete...</div>
</div>
''', unsafe_allow_html=True)

# Executar cargas
admin_target = None
if current_profile == "Administrador":
    # Buscar lista de procuradores para o admin selecionar
    all_users_temp = get_all_users()
    procuradores_opts = {u['nome_completo']: u['id'] for u in all_users_temp if u['perfil'] == 'Procurador'}
    
    if not procuradores_opts:
        st.error("Nenhum procurador encontrado no sistema.")
        st.stop()
        
    selected_proc_name = st.selectbox(
        "👮‍♂️ [Modo Admin] Selecione o Gabinete para Visualizar:", 
        options=list(procuradores_opts.keys())
    )
    admin_target = procuradores_opts[selected_proc_name]

target_procurador_id, chefes_ids, all_users_list, servidores_atuais_ids = get_gabinete_context(current_user_id, current_profile, admin_target)

if not target_procurador_id:
    loading_placeholder.empty()
    st.error("Não foi possível identificar o gabinete vinculado. Contate o suporte.")
    st.stop()

raw_processos, raw_tipos = load_gabinete_data(target_procurador_id)

loading_placeholder.empty()

if not raw_processos:
    st.info("Nenhum processo encontrado para este gabinete.")
    st.stop()

# --- Preparação dos Dados ---
usuarios_dict = {u['id']: u for u in all_users_list}
tipos_dict = {t['id']: t for t in raw_tipos}

df_master = prepare_master_dataframe(raw_processos, usuarios_dict, tipos_dict)

# Métrica segura: garantir que colunas numéricas não tenham NaN
cols_numericas = ['prazo_total_dias_suspenso', 'prazo_servidor_aplicado', 'prazo_chefe_aplicado']
for col in cols_numericas:
    if col in df_master.columns:
        df_master[col] = df_master[col].fillna(0)

# --- Filtros ---
st.markdown("### 🎯 Filtros do Gabinete")

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

# Filtro de servidores atuais (checkbox, ativo por padrão)
filtro_servidores_atuais = st.checkbox(
    "👥 Apenas servidores vinculados atualmente",
    value=True,
    help="Quando ativo, exibe dados apenas dos servidores que estão vinculados ao gabinete no momento. Desmarque para incluir servidores que já foram vinculados anteriormente."
)

if filtro_servidores_atuais and servidores_atuais_ids:
    df_master = df_master[df_master['id_servidor_responsavel'].isin(servidores_atuais_ids)]

# --- Filtragem Base (por data de conclusão ou movimentação) ---
# Para KPIs gerais, consideramos o período selecionado.
# Regra: data_conclusao dentro do período OU data_atribuicao (para entrada)

# Vamos criar um DF filtrado para "Concluídos no Período" (Métricas de produtividade)
df_servidor_calc = calculate_metrics_servidor(df_master)
df_chefe_calc = calculate_metrics_chefe(df_master)

# Filtrar para exibir estatísticas
# Se o usuário selecionar um tipo, filtra tudo
if filtro_tipos:
    df_master = df_master[df_master['nome_produto'].isin(filtro_tipos)]
    df_servidor_calc = df_servidor_calc[df_servidor_calc['nome_produto'].isin(filtro_tipos)]
    df_chefe_calc = df_chefe_calc[df_chefe_calc['nome_produto'].isin(filtro_tipos)]

# Filtro de Data para Métricas de Fluxo (Conclusões)
df_concluidos_servidor = df_servidor_calc[
    (df_servidor_calc['data_conclusao_servidor'].dt.normalize() >= f_ini_ts) &
    (df_servidor_calc['data_conclusao_servidor'].dt.normalize() <= f_fim_ts)
]

df_concluidos_chefe = df_chefe_calc[
    (df_chefe_calc['data_conclusao_chefe'].dt.normalize() >= f_ini_ts) &
    (df_chefe_calc['data_conclusao_chefe'].dt.normalize() <= f_fim_ts)
]

# Processos Finalizados (Pelo Procurador) - Usando data_finalizacao
df_master['data_finalizacao'] = pd.to_datetime(df_master['data_finalizacao'], errors='coerce')
df_finalizados = df_master[
    (df_master['data_finalizacao'].dt.normalize() >= f_ini_ts) &
    (df_master['data_finalizacao'].dt.normalize() <= f_fim_ts)
]

# --- Cálculo dos KPIs ---

# 1. Processos Registrados (Total no banco para este gabinete, independente de filtro de data de conclusão?)
# O pedido diz: "Processos Registrados no Gabinete". Geralmente refere-se à entrada no período ou total da base.
# Vamos assumir "Entrada no período" para ser consistente com o filtro de data (Atribuídos ao servidor no período).
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

# 4. Aprovados Procurador (REMOVIDO A PEDIDO DO USUÁRIO)
# kpi_aprov_proc = len(df_finalizados)

# 5. Acervo Servidores (Snapshot - Métrica 4 do Relatório)
# Calcular Snapshot AGORA para o KPI de topo
now_ts = pd.Timestamp.now()
acervo_s_now, acervo_c_now = calculate_acervo_snapshot(df_master, now_ts)
kpi_acervo_servidores = len(acervo_s_now)

# 6. Acervo Chefes (Snapshot - Métrica 8 do Relatório)
kpi_acervo_chefes = len(acervo_c_now)

# 7. No Prazo Servidores (%) - Métrica 3 do Relatório
pct_prazo_serv = (df_concluidos_servidor['no_prazo_servidor'].sum() / kpi_conc_serv * 100) if kpi_conc_serv > 0 else 0

# 8. Percentual Prazo Chefe - Métrica 7 do Relatório
pct_prazo_chefe = (df_concluidos_chefe['revisao_no_prazo'].sum() / kpi_rev_chefe * 100) if kpi_rev_chefe > 0 else 0

# 9. Tempo Médio Servidores - Métrica 2 do Relatório
tm_serv = df_concluidos_servidor['duracao_servidor'].mean() if not df_concluidos_servidor.empty else 0

# 10. Tempo Médio Chefes - Métrica 6 do Relatório
tm_chefe = df_concluidos_chefe['duracao_revisao_chefe'].mean() if not df_concluidos_chefe.empty else 0


st.markdown("### 📈 KPIs do Gabinete")

# Grid de KPIs (alinhado com métricas do Relatório Mensal)
# Row 1
k1, k2, k3 = st.columns(3)
with k1: st.metric("📥 Processos Registrados (Entradas)", kpi_registrados, help="Processos atribuídos aos servidores neste período")
with k2: st.metric("✅ Concluídos por Servidores", kpi_conc_serv, help="Métrica 1 do Relatório Mensal")
with k3: st.metric("👀 Processos Revisados (Chefes)", kpi_rev_chefe, help="Métrica 5 do Relatório Mensal")

# Row 2
k4, k5, k6 = st.columns(3)
with k4: st.metric("📂 Acervo Servidores (Pendentes)", kpi_acervo_servidores, help="Métrica 4 do Relatório Mensal — processos não concluídos pelos servidores")
with k5: st.metric("📋 Acervo Chefes (Pend. Revisão)", kpi_acervo_chefes, help="Métrica 8 do Relatório Mensal — processos não revisados pelos chefes")
with k6: st.metric("⏱️ Tempo Médio (Servidores)", f"{tm_serv:.1f} dias", help="Métrica 2 do Relatório Mensal")

# Row 3
k7, k8, k9 = st.columns(3)
with k7: st.metric("⏱️ Tempo Médio de Revisão (Chefes)", f"{tm_chefe:.1f} dias", help="Métrica 6 do Relatório Mensal")
with k8: st.metric("🎯 % Conclusão no Prazo (Serv)", f"{pct_prazo_serv:.1f}%", help="Métrica 3 do Relatório Mensal")
with k9: st.metric("🎯 % Revisão no Prazo (Chefes)", f"{pct_prazo_chefe:.1f}%", help="Métrica 7 do Relatório Mensal")

st.markdown("---")

# --- Gráficos Detalhados por Servidor ---

# Preparar dados agrupados por servidor
if not df_concluidos_servidor.empty:
    grp_serv = df_concluidos_servidor.groupby('servidor_nome').agg(
        concluidos=('id', 'count'),
        no_prazo=('no_prazo_servidor', 'sum'),
        tempo_medio=('duracao_servidor', 'mean')
    ).reset_index()
    
    grp_serv['pct_prazo'] = (grp_serv['no_prazo'] / grp_serv['concluidos'] * 100).fillna(0)
    
    # Altura dinâmica baseada no número de servidores (union de quem concluiu e quem tem acervo)
    # Isso garante que a altura seja suficiente mesmo que alguns servidores só apareçam no gráfico de acervo
    set_servidores = set(grp_serv['servidor_nome'].unique())
    if not acervo_s_now.empty:
        set_servidores.update(acervo_s_now['servidor_nome'].unique())
    
    num_servidores = len(set_servidores) if set_servidores else 1
    chart_height = max(400, num_servidores * 35 + 100) # Aumentado para 35px por servidor para melhor legibilidade
    
    # 1) Processos concluídos por servidor (Métrica 1 do Relatório)
    st.markdown("#### 🏆 1. Produtividade por Servidor (Concluídos)")
    fig1 = px.bar(
        grp_serv, 
        x='concluidos', 
        y='servidor_nome', 
        orientation='h',
        text='concluidos',
        color='concluidos', 
        color_continuous_scale='Greens',
        labels={'concluidos': 'Processos Concluídos', 'servidor_nome': 'Servidor'}
    )
    fig1.update_traces(textposition='outside')
    fig1.update_layout(
        yaxis={'categoryorder': 'total ascending'}, 
        plot_bgcolor='rgba(0,0,0,0)',
        height=chart_height
    )
    st.plotly_chart(fig1, use_container_width=True)
    st.markdown("---")
        
    # 2) Tempo Médio por Servidor (Métrica 2 do Relatório)
    st.markdown("#### ⏱️ 2. Tempo Médio por Servidor")
    fig2 = px.bar(
        grp_serv, 
        x='tempo_medio', 
        y='servidor_nome', 
        orientation='h',
        text=grp_serv['tempo_medio'].apply(lambda x: f"{x:.1f} dias"),
        color='tempo_medio', 
        color_continuous_scale='Reds', # Vermelho pois maior tempo é pior
        labels={'tempo_medio': 'Tempo Médio (Dias)', 'servidor_nome': 'Servidor'}
    )
    fig2.update_traces(textposition='outside')
    fig2.update_layout(
        yaxis={'categoryorder': 'total descending'}, 
        plot_bgcolor='rgba(0,0,0,0)',
        height=chart_height
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.markdown("---")

    # 3) Percentual no Prazo por Servidor (Métrica 3 do Relatório)
    st.markdown("#### 🎯 3. Percentual de Processos Concluídos no Prazo por Servidor")
    fig_prazo = px.bar(
        grp_serv, 
        x='pct_prazo', 
        y='servidor_nome', 
        orientation='h',
        text=grp_serv['pct_prazo'].apply(lambda x: f"{x:.1f}%"),
        color='pct_prazo', 
        color_continuous_scale='RdYlGn', 
        range_color=[0, 100],
        labels={'pct_prazo': '% no Prazo', 'servidor_nome': 'Servidor'}
    )
    fig_prazo.update_traces(textposition='outside')
    fig_prazo.update_layout(
        yaxis={'categoryorder': 'total ascending'}, 
        plot_bgcolor='rgba(0,0,0,0)',
        height=chart_height
    )
    st.plotly_chart(fig_prazo, use_container_width=True)
    st.markdown("---")

    # 4) Distribuição Detalhada (Concluido vs Acervo)
    st.markdown("#### 📊 4. Processos Distribuídos por Servidor (Concluídos vs Aberto)")
    
    # Snapshot AGORA para o gráfico
    df_chart_acervo = acervo_s_now.groupby('servidor_nome').size().reset_index(name='Em Aberto')
    df_chart_concluidos = grp_serv[['servidor_nome', 'concluidos']].rename(columns={'concluidos': 'Concluídos'})
    
    # Merge
    df_dist = pd.merge(df_chart_concluidos, df_chart_acervo, on='servidor_nome', how='outer').fillna(0)
    df_dist['Total'] = df_dist['Concluídos'] + df_dist['Em Aberto']
    df_dist = df_dist.sort_values('Total', ascending=True)
    
    # Transformar para formato longo para gráfico empilhado
    df_dist_long = df_dist.melt(id_vars=['servidor_nome', 'Total'], value_vars=['Concluídos', 'Em Aberto'], 
                                var_name='Estado', value_name='Quantidade')
    
    fig_dist = px.bar(
        df_dist_long, 
        y='servidor_nome', 
        x='Quantidade', 
        color='Estado',
        orientation='h',
        text='Quantidade',
        color_discrete_map={'Concluídos': '#28a745', 'Em Aberto': '#dc3545'},
        labels={'servidor_nome': 'Servidor', 'Quantidade': 'Processos', 'Estado': 'Situação'}
    )
    fig_dist.update_traces(textposition='inside')
    fig_dist.update_layout(
        barmode='stack', 
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    # Adicionar totais ao final da barra
    fig_dist.add_trace(go.Scatter(
        y=df_dist['servidor_nome'],
        x=df_dist['Total'],
        text=df_dist['Total'].apply(lambda x: str(int(x))),
        mode='text',
        textposition='middle right',
        showlegend=False,
        textfont=dict(color='black', size=12)
    ))
    
    # Ajustar ranges para caber o texto do total e definir altura
    max_val = df_dist['Total'].max()
    fig_dist.update_layout(
        xaxis_range=[0, max_val * 1.15],
        height=chart_height
    )
    
    st.plotly_chart(fig_dist, use_container_width=True)

else:
    st.info("Sem dados de conclusão de servidores para o período selecionado.")

st.markdown("---")

# --- Acervo Histórico (Mês a Mês) ---
st.markdown("### 📅 Evolução do Acervo (Estoque)")

# Determinar limite do gráfico: não deve ultrapassar o mês corrente
hoje = pd.Timestamp.now()
data_limite_hist = hoje + pd.offsets.MonthEnd(0)  # Último dia do mês corrente
f_fim_limitado = min(pd.Timestamp(f_fim), data_limite_hist)

# Função para calcular histórico (pode ser pesada, avisar usuário)
# Vamos calcular snapshots mensais para o ano corrente ou período selecionado
dates_to_check = pd.date_range(start=f_ini, end=f_fim_limitado, freq='ME') # Month End

history_data = []

if len(dates_to_check) > 0:
    prog_bar = st.progress(0, text="Calculando histórico de acervo...")
    
    for i, date_ref in enumerate(dates_to_check):
        idx = i + 1
        pct = int(idx / len(dates_to_check) * 100)
        prog_bar.progress(pct, text=f"Calculando histórico: {date_ref.strftime('%m/%Y')}")
        
        # Calcular snapshot para esta data
        # Usamos o df_master inteiro (sem filtro de conclusão) para ver o estado nela
        acervo_s, acervo_c = calculate_acervo_snapshot(df_master, date_ref, filter_terminal_status=False)
        
        history_data.append({
            'data': date_ref,
            'mes_ano': date_ref.strftime('%b/%Y'),
            'Acervo Servidores': len(acervo_s),
            'Acervo Chefes': len(acervo_c)
        })
    
    prog_bar.empty()
    
    df_history = pd.DataFrame(history_data)
    
    if not df_history.empty:
        # Gráfico de Linhas Comparativo
        fig_hist = go.Figure()
        fig_hist.add_trace(go.Scatter(
            x=df_history['data'], y=df_history['Acervo Servidores'],
            mode='lines+markers', name='Com Servidores',
            line=dict(color='#0D47A1', width=3)
        ))
        fig_hist.add_trace(go.Scatter(
            x=df_history['data'], y=df_history['Acervo Chefes'],
            mode='lines+markers', name='Com Chefes',
            line=dict(color='#9E0520', width=3)
        ))
        
        fig_hist.update_layout(
            title="Evolução do Acervo (Final do Mês)",
            xaxis_title="Mês",
            yaxis_title="Processos Pendentes",
            plot_bgcolor='rgba(0,0,0,0)',
            hovermode="x unified"
        )
        st.plotly_chart(fig_hist, use_container_width=True)
else:
    st.warning("Selecione um intervalo de datas maior para ver a evolução histórica.")

st.markdown("---")

# --- Acervo Atual Detalhado ---
st.markdown("### 📋 Carga de Trabalho Atual (Em Aberto)")

# Calcular Snapshot AGORA
now = pd.Timestamp.now()
# df_acervo_atual_serv foi calculado lá em cima como acervo_s_now, reutilizar
df_acervo_atual_serv = acervo_s_now

if not df_acervo_atual_serv.empty:
    # Agrupar por servidor
    # Métrica 1: Total Acervo
    # Métrica 2: Atrasados (prazo excedido hoje)
    
    # Calcular atraso atual
    # Precisamos recalcular o prazo para o momento atual para saber se esta atrasado HOJE
    # A funcao calculate_metrics_servidor ja calcula 'data_final_teorica' e 'no_prazo_servidor' baseado na DATA DE CONCLUSAO
    # Para processos EM ABERTO, precisamos comparar HOJE com data_final_teorica
    
    # Reutilizar logica de prazo
    df_ativo_calc = df_acervo_atual_serv.copy()
    
    # Recalcular data final teorica (garantir que existe)
    if 'data_final_teorica' not in df_ativo_calc.columns:
        df_ativo_calc['data_final_teorica'] = df_ativo_calc.apply(
            lambda row: calculate_due_date_safe(row), axis=1
        )
        
    # Verificar atraso (Hoje > Data Final)
    hoje_ts = pd.Timestamp(today_brazil())
    df_ativo_calc['esta_atrasado'] = df_ativo_calc['data_final_teorica'] < hoje_ts.date()
    
    # Agrupar
    resumo_carga = df_ativo_calc.groupby('servidor_nome').agg(
        total_acervo=('id', 'count'),
        total_atrasado=('esta_atrasado', 'sum')
    ).reset_index().sort_values('total_acervo', ascending=False)
    
    resumo_carga.columns = ['Servidor', 'Acervo Total', 'Atrasados']
    
    # Tabela de Carga (Com tooltip e sem gráfico lateral)
    st.dataframe(
        resumo_carga, 
        hide_index=True,
        column_config={
            "Acervo Total": st.column_config.ProgressColumn(
                "Total em Aberto",
                format="%d",
                min_value=0,
                max_value=int(resumo_carga['Acervo Total'].max() * 1.2) if not resumo_carga.empty else 100,
                help="Quantidade total de processos sob responsabilidade do servidor. A barra indica a carga relativa comparada aos demais membros da equipe."
            ),
            "Atrasados": st.column_config.NumberColumn(
                "⚠️ Atrasados",
                format="%d",
                help="Processos cujo prazo já expirou."
            )
        },
        use_container_width=True
    )

else:
    st.info("A equipe não possui processos pendentes no momento.")

# --- Metodologia ---
st.markdown("---")
with st.expander("ℹ️ Metodologia e Memória de Cálculo"):
     st.markdown("""
    ### 📝 Metodologia dos Indicadores
    
    Os dados apresentados consolidam as informações de **todo o gabinete** vinculado ao Procurador (incluindo todos os servidores e chefes associados).
    
    #### 1. KPIs Principais
    - **Registrados:** Processos que entraram na fase de servidor (data de atribuição) dentro do período selecionado.
    - **Concluídos Servidores:** Processos que tiveram a data de conclusão do servidor registrada no período.
    - **Revisados Chefes:** Processos que tiveram a data de conclusão do chefe registrada no período.
    - **Aprovados Procurador:** Processos finalizados (arquivados/enviados) no período.
    
    #### 2. Tempos e Prazos
    - **Tempo Médio:** Média de dias úteis ou corridos (conforme tipo do processo) gastos para concluir a etapa, descontando suspensões.
    - **% No Prazo:** Percentual de processos entregues antes ou na data limite calculada.
    
    #### 3. Acervo (Estoque)
    - **Acervo Servidores:** Processos atualmente com servidores (não concluídos e não devolvidos).
    - **Acervo Chefes:** Processos concluídos por servidores mas ainda não revisados pelos chefes.
    - **Atrasados:** Processos cujo prazo calculado já venceu em relação à data de hoje.
    """)

