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

# CSS customizado para a página (reutilizando Meus_Dados.py)
st.markdown('''
<style>
    /* Estilos reutilizados de Meus_Dados.py */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #ffffff, #f8f9fa);
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.08);
        border-left: 4px solid #9E0520;
        transition: all 0.3s ease;
    }
    
    [data-testid="stMetric"]:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(158, 5, 32, 0.15);
    }
    
    .section-title {
        background: linear-gradient(90deg, #9E0520, transparent);
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
        border-top: 4px solid #9E0520;
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
def get_gabinete_context(user_id, profile):
    """Identifica o Procurador alvo e todos os membros do gabinete."""
    target_procurador_id = None
    
    if profile == "Procurador":
        target_procurador_id = user_id
    elif profile == "Chefe de Gabinete":
        # Buscar procurador vinculado
        link = QueryBuilder("procurador_chefes").eq("chefe_id", user_id).execute()
        if link:
            target_procurador_id = link[0]['procurador_id']
    
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
    
    return target_procurador_id, chefes_ids, all_users

@st.cache_data(ttl=300, show_spinner=False)
def load_gabinete_data(procurador_id):
    """Carrega dados de processos para todo o gabinete do procurador."""
    if not procurador_id:
        return [], []
        
    # Buscar processos onde o procurador é o dono do gabinete
    # A tabela processos tem 'id_procurador' - isso facilita muito!
    # Não precisamos reconstruir a hierarquia complexa para buscar os processos, basta filtrar pelo id_procurador.
    
    processos_cols = "id,status_servidor,status_chefe,id_servidor_responsavel,id_chefe_gabinete,id_procurador,id_tipo_produto,data_atribuicao_servidor,data_conclusao_servidor,data_conclusao_chefe,data_finalizacao,prazo_servidor_aplicado,prazo_total_dias_suspenso,nao_se_aplica_prazo_servidor,ignorar_revisao_chefe,ignorar_analise_procurador,processo_numero"
    
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
target_procurador_id, chefes_ids, all_users_list = get_gabinete_context(current_user_id, current_profile)

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

with col3:
    tipos_unicos = sorted(df_master['nome_produto'].dropna().unique().tolist())
    filtro_tipos = st.multiselect("📝 Tipo de Processo", options=tipos_unicos)

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
    (df_servidor_calc['data_conclusao_servidor'].dt.date >= f_ini) &
    (df_servidor_calc['data_conclusao_servidor'].dt.date <= f_fim)
]

df_concluidos_chefe = df_chefe_calc[
    (df_chefe_calc['data_conclusao_chefe'].dt.date >= f_ini) &
    (df_chefe_calc['data_conclusao_chefe'].dt.date <= f_fim)
]

# Processos Finalizados (Pelo Procurador) - Usando data_finalizacao
df_master['data_finalizacao'] = pd.to_datetime(df_master['data_finalizacao'], errors='coerce')
df_finalizados = df_master[
    (df_master['data_finalizacao'].dt.date >= f_ini) &
    (df_master['data_finalizacao'].dt.date <= f_fim)
]

# --- Cálculo dos KPIs ---

# 1. Processos Registrados (Total no banco para este gabinete, independente de filtro de data de conclusão?)
# O pedido diz: "Processos Registrados no Gabinete". Geralmente refere-se à entrada no período ou total da base.
# Vamos assumir "Entrada no período" para ser consistente com o filtro de data (Atribuídos ao servidor no período).
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

# 5. No Prazo Servidores (%)
pct_prazo_serv = (df_concluidos_servidor['no_prazo_servidor'].sum() / kpi_conc_serv * 100) if kpi_conc_serv > 0 else 0

# 6. Quantidade de Servidores (Ativos no período/nos dados)
# Conta servidores distintos que tiveram alguma movimentação ou estão no quadro
# Vamos pegar todos os servidores presentes na tabela 'processos' deste gabinete
qtd_servidores = df_master['id_servidor_responsavel'].nunique()

# 7. Tempo Médio Servidores
tm_serv = df_concluidos_servidor['duracao_servidor'].mean() if not df_concluidos_servidor.empty else 0

# 8. Tempo Médio Chefes
tm_chefe = df_concluidos_chefe['duracao_revisao_chefe'].mean() if not df_concluidos_chefe.empty else 0


st.markdown("### 📈 KPIs do Gabinete")

k1, k2, k3, k4 = st.columns(4)
with k1: st.metric("📥 Registrados (Período)", kpi_registrados, help="Processos atribuídos aos servidores neste período")
with k2: st.metric("✅ Concl. Servidores", kpi_conc_serv)
with k3: st.metric("👀 Revisados Chefes", kpi_rev_chefe)
with k4: st.metric("⚖️ Aprov. Procurador", kpi_aprov_proc, help="Processos finalizados pelo Procurador")

k5, k6, k7, k8 = st.columns(4)
with k5: st.metric("👥 Servidores Ativos", qtd_servidores)
with k6: st.metric("⏱️ T. Médio Servidores", f"{tm_serv:.1f} dias")
with k7: st.metric("⏱️ T. Médio Chefes", f"{tm_chefe:.1f} dias")
with k8: st.metric("🎯 % No Prazo (Serv)", f"{pct_prazo_serv:.1f}%")

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
    
    # 1) Processos concluídos por servidor (+ % prazo)
    c_g1, c_g2 = st.columns(2)
    
    with c_g1:
        st.markdown("#### 🏆 Produtividade por Servidor")
        fig1 = px.bar(
            grp_serv, x='concluidos', y='servidor_nome', orientation='h',
            text='concluidos',
            color='pct_prazo', color_continuous_scale='RdYlGn',
            labels={'concluidos': 'Processos Concluídos', 'servidor_nome': 'Servidor', 'pct_prazo': '% no Prazo'}
        )
        fig1.update_traces(textposition='outside')
        fig1.update_layout(yaxis={'categoryorder': 'total ascending'}, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig1, use_container_width=True)
        
    # 2) Tempo Médio por Servidor
    with c_g2:
        st.markdown("#### ⏱️ Tempo Médio por Servidor")
        fig2 = px.bar(
            grp_serv, x='tempo_medio', y='servidor_nome', orientation='h',
            text=grp_serv['tempo_medio'].apply(lambda x: f"{x:.1f} dias"),
            color='tempo_medio', color_continuous_scale='Reds', # Vermelho pois maior tempo é pior
            labels={'tempo_medio': 'Tempo Médio (Dias)', 'servidor_nome': 'Servidor'}
        )
        fig2.update_traces(textposition='outside')
        fig2.update_layout(yaxis={'categoryorder': 'total descending'}, plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig2, use_container_width=True)

    # 3) Distribuição (Pizza/Pie)
    st.markdown("#### 🥧 Distribuição de Carga (Concluídos)")
    fig3 = px.pie(grp_serv, values='concluidos', names='servidor_nome', hole=0.4)
    st.plotly_chart(fig3, use_container_width=True)

else:
    st.info("Sem dados de conclusão de servidores para o período selecionado.")

st.markdown("---")

# --- Acervo Histórico (Mês a Mês) ---
st.markdown("### 📅 Evolução do Acervo (Estoque)")

# Função para calcular histórico (pode ser pesada, avisar usuário)
# Vamos calcular snapshots mensais para o ano corrente ou período selecionado
dates_to_check = pd.date_range(start=f_ini, end=f_fim, freq='ME') # Month End

history_data = []

if len(dates_to_check) > 0:
    prog_bar = st.progress(0, text="Calculando histórico de acervo...")
    
    for i, date_ref in enumerate(dates_to_check):
        idx = i + 1
        pct = int(idx / len(dates_to_check) * 100)
        prog_bar.progress(pct, text=f"Calculando histórico: {date_ref.strftime('%m/%Y')}")
        
        # Calcular snapshot para esta data
        # Usamos o df_master inteiro (sem filtro de conclusão) para ver o estado nela
        acervo_s, acervo_c = calculate_acervo_snapshot(df_master, date_ref)
        
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
df_acervo_atual_serv, _ = calculate_acervo_snapshot(df_master, now)

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
    hoje_ts = pd.Timestamp(date.today())
    df_ativo_calc['esta_atrasado'] = df_ativo_calc['data_final_teorica'] < hoje_ts.date()
    
    # Agrupar
    resumo_carga = df_ativo_calc.groupby('servidor_nome').agg(
        total_acervo=('id', 'count'),
        total_atrasado=('esta_atrasado', 'sum')
    ).reset_index().sort_values('total_acervo', ascending=False)
    
    resumo_carga.columns = ['Servidor', 'Acervo Total', 'Atrasados']
    
    col_t1, col_t2 = st.columns([2, 1])
    
    with col_t1:
        st.dataframe(
            resumo_carga, 
            hide_index=True,
            column_config={
                "Acervo Total": st.column_config.ProgressColumn(
                    "Total em Aberto",
                    format="%d",
                    min_value=0,
                    max_value=int(resumo_carga['Acervo Total'].max() * 1.2) if not resumo_carga.empty else 100,
                ),
                "Atrasados": st.column_config.NumberColumn(
                    "⚠️ Atrasados",
                    format="%d"
                )
            },
            use_container_width=True
        )
        
    with col_t2:
        # Gráfico rápido de atrasados
        if resumo_carga['Atrasados'].sum() > 0:
            fig_atraso = px.bar(
                resumo_carga, x='Servidor', y='Atrasados',
                title="Processos Atrasados por Servidor",
                color='Atrasados', color_continuous_scale='Reds'
            )
            st.plotly_chart(fig_atraso, use_container_width=True)
        else:
            st.success("🎉 Nenhum processo atrasado na equipe!")

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

# Helper function definition needed for calculation above if not in utils
def calculate_due_date_safe(row):
    return calculate_due_date(
        start_date=row['data_atribuicao_servidor'].date(),
        prazo_dias=row['prazo_servidor_aplicado'],
        tipo_contagem=row['tipo_contagem_prazo'],
        id_usuario=row['id_servidor_responsavel'],
        dias_suspensos=row.get('prazo_total_dias_suspenso', 0)
    )
