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
    create_metric_card, format_and_plot, calculate_acervo_snapshot
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

# CSS customizado para a página Meus Dados
st.markdown('''
<style>
    /* Loading Screen Animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(0.98); }
    }
    
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
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
    
    .loading-text {
        font-size: 1.2em;
        color: #555;
        font-weight: 500;
    }
    
    /* KPI Cards Premium */
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
    
    [data-testid="stMetric"] [data-testid="stMetricLabel"] {
        font-weight: 600;
        color: #555;
        font-size: 0.95em;
    }
    
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-weight: 700;
        color: #1a1a1a;
        font-size: 1.8em;
    }
    
    /* Section Headers */
    .section-title {
        background: linear-gradient(90deg, #9E0520, transparent);
        padding: 12px 20px;
        border-radius: 10px;
        color: white;
        font-weight: 600;
        font-size: 1.2em;
        margin: 25px 0 15px 0;
    }
    
    /* Chart Containers */
    [data-testid="stPlotlyChart"] {
        background: white;
        border-radius: 15px;
        padding: 15px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        transition: all 0.3s ease;
    }
    
    [data-testid="stPlotlyChart"]:hover {
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    
    /* Filter Section */
    .filter-container {
        background: linear-gradient(135deg, #f8f9fa 0%, #ffffff 100%);
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 25px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
    }
    
    /* Date Inputs */
    [data-testid="stDateInput"] {
        background: white;
        border-radius: 10px;
    }
    
    /* Dividers */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent, #9E0520, transparent);
        margin: 30px 0;
    }
</style>
''', unsafe_allow_html=True)

st.session_state.active_page = "Meus Dados"
build_sidebar()

# --- Header Principal ---
st.markdown('''
<div style="background: linear-gradient(135deg, #9E0520 0%, #B8062A 100%); color: white; padding: 30px; border-radius: 20px; text-align: center; margin-bottom: 30px; box-shadow: 0 8px 30px rgba(158, 5, 32, 0.35);">
    <h1 style="margin: 0; font-size: 2.4em; font-weight: 700; text-shadow: 0 2px 4px rgba(0,0,0,0.2);">📊 Meus Dados</h1>
    <p style="margin: 12px 0 0 0; font-size: 1.15em; opacity: 0.95; font-weight: 400;">Painel de indicadores pessoais de produtividade</p>
</div>
''', unsafe_allow_html=True)

# --- Placeholder para Loading ---
loading_placeholder = st.empty()

# --- Carregar Dados com Cache ---
user_id = st.session_state.user_id

@st.cache_data(ttl=300, show_spinner=False)
def load_user_data(uid):
    """Carrega dados do usuário com cache e queries otimizadas."""
    # Selecionar apenas colunas necessárias para processos (reduz ~70% do payload)
    processos_cols = "id,status_servidor,status_chefe,id_servidor_responsavel,id_chefe_gabinete,id_tipo_produto,data_atribuicao_servidor,data_conclusao_servidor,data_conclusao_chefe,prazo_servidor_aplicado,prazo_total_dias_suspenso,nao_se_aplica_prazo_servidor,ignorar_revisao_chefe"
    processos = QueryBuilder("processos") \
        .eq("id_servidor_responsavel", uid) \
        .select(processos_cols) \
        .execute()
    
    # Selecionar apenas colunas necessárias para usuários (id e nome)
    usuarios = QueryBuilder("usuarios") \
        .select("id,nome_completo") \
        .execute()
    
    # Selecionar apenas colunas necessárias para tipos de produto
    tipos = QueryBuilder("tipos_produto") \
        .select("id,nome_produto,tipo_contagem_prazo") \
        .execute()
    
    # Buscar histórico de devoluções (em chunks para evitar erro de URL muito longa)
    process_ids = [p['id'] for p in processos]
    historico_devolucoes = []
    
    if process_ids:
        chunk_size = 100
        for i in range(0, len(process_ids), chunk_size):
            chunk = process_ids[i:i + chunk_size]
            try:
                hist_chunk = QueryBuilder("processo_historico") \
                    .eq("evento", "Devolvido pelo Chefe") \
                    .in_list("id_processo", chunk) \
                    .execute()
                historico_devolucoes.extend(hist_chunk)
            except Exception as e:
                print(f"[MEUS_DADOS] Erro ao buscar chunk de histórico: {e}")
                
    return processos, usuarios, tipos, historico_devolucoes

# Mostrar loading enquanto carrega
loading_placeholder.markdown('''
<div class="loading-container">
    <div class="loading-spinner"></div>
    <div class="loading-text">🔄 Carregando dados e calculando indicadores...</div>
    <p style="color: #888; margin-top: 10px; font-size: 0.9em;">Isso pode levar alguns segundos</p>
</div>
''', unsafe_allow_html=True)

all_user_processes, all_users, all_types, all_history = load_user_data(user_id)

# Loading movido para após o processamento

if not all_user_processes:
    loading_placeholder.empty()
    st.info("📋 Você ainda não possui processos atribuídos.")
    st.stop()

usuarios_dict = {u['id']: u for u in all_users}
tipos_dict = {t['id']: t for t in all_types}

# Preparar DataFrame
df_master = prepare_master_dataframe(all_user_processes, usuarios_dict, tipos_dict)

# --- Filtros ---
st.markdown("### 🎯 Filtros")

col1, col2, col3 = st.columns(3)

with col1:
    hoje = today_brazil()
    # Data padrão: 01/01/2024 até 31/12 do ano corrente
    data_inicio_padrao = date(2024, 1, 1)
    data_fim_padrao = date(hoje.year, 12, 31)
    
    f_ini = st.date_input("📅 Data Início", value=data_inicio_padrao, format="DD/MM/YYYY")

with col2:
    f_fim = st.date_input("📅 Data Fim", value=data_fim_padrao, format="DD/MM/YYYY")

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

# Buscar processos pendentes de revisão (concluídos pelo servidor, aguardando chefe) using official logic
# Returns (acervo_servidor, acervo_chefe) - we want acervo_chefe count
_, df_acervo_chefe = calculate_acervo_snapshot(df_master, pd.Timestamp.now())
processos_pendentes_revisao = len(df_acervo_chefe)

# Filtrar devoluções do histórico cacheado
historico_devolucoes = []
if all_history:
    for h in all_history:
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

total_devolucoes = len(historico_devolucoes)

# Limpar loading após processamento
loading_placeholder.empty()

# --- KPIs ---
st.markdown("### 📈 Indicadores do Período")

c1, c2, c3, c4, c5 = st.columns(5)

# Calcular KPIs
total_concluidos = len(df_filtered) if not df_filtered.empty else 0
tempo_medio = df_filtered['duracao_servidor'].mean() if not df_filtered.empty and 'duracao_servidor' in df_filtered.columns else 0
pct_no_prazo = (df_filtered['no_prazo_servidor'].sum() / total_concluidos * 100) if total_concluidos > 0 else 0
pendentes_revisao = processos_pendentes_revisao

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
    
    # Mapeamento de meses para português
    MESES_PT = {
        1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
        7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'
    }
    
    def formatar_mes(dt):
        """Formata datetime para 'Jan/2025' etc."""
        return f"{MESES_PT[dt.month]}/{dt.year}"
    
    # Preparar dados mensais com formato correto
    df_filtered['mes_dt'] = df_filtered['data_conclusao_servidor'].dt.to_period('M').dt.to_timestamp()
    df_filtered['mes'] = df_filtered['data_conclusao_servidor'].apply(formatar_mes)
    
    # Gráfico 1: Processos Concluídos por Mês
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        st.markdown("#### 📋 Processos Concluídos")
        concluidos_mes = df_filtered.groupby(['mes_dt', 'mes']).size().reset_index(name='Quantidade')
        concluidos_mes = concluidos_mes.sort_values('mes_dt')
        if not concluidos_mes.empty:
            fig1 = px.bar(concluidos_mes, x='mes', y='Quantidade', 
                          color='Quantidade', color_continuous_scale='viridis',
                          text='Quantidade')
            fig1.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Mês",
                yaxis_title="Processos",
                xaxis={'categoryorder': 'array', 'categoryarray': concluidos_mes['mes'].tolist()}
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")
    
    with col_g2:
        st.markdown("#### ⏱️ Tempo Médio (dias)")
        tempo_mes = df_filtered.groupby(['mes_dt', 'mes'])['duracao_servidor'].mean().reset_index(name='Tempo Médio')
        tempo_mes = tempo_mes.sort_values('mes_dt')
        if not tempo_mes.empty:
            fig2 = px.line(tempo_mes, x='mes', y='Tempo Médio', markers=True)
            fig2.update_traces(line_color='#9E0520', line_width=3)
            fig2.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Mês",
                yaxis_title="Dias",
                xaxis={'categoryorder': 'array', 'categoryarray': tempo_mes['mes'].tolist()}
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")
    
    col_g3, col_g4 = st.columns(2)
    
    with col_g3:
        st.markdown("#### ✅ % Entrega no Prazo")
        prazo_mes = df_filtered.groupby(['mes_dt', 'mes']).agg(
            total=('id', 'count'),
            no_prazo=('no_prazo_servidor', 'sum')
        ).reset_index()
        prazo_mes = prazo_mes.sort_values('mes_dt')
        prazo_mes['Percentual'] = (prazo_mes['no_prazo'] / prazo_mes['total'] * 100).fillna(0)
        
        if not prazo_mes.empty:
            fig3 = px.bar(prazo_mes, x='mes', y='Percentual',
                          color='Percentual', color_continuous_scale='RdYlGn',
                          text=prazo_mes['Percentual'].apply(lambda x: f'{x:.1f}%'))
            fig3.update_layout(
                plot_bgcolor='rgba(0,0,0,0)', 
                paper_bgcolor='rgba(0,0,0,0)',
                xaxis_title="Mês",
                yaxis_title="%",
                xaxis={'categoryorder': 'array', 'categoryarray': prazo_mes['mes'].tolist()}
            )
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sem dados para exibir.")
    
    with col_g4:
        st.markdown("#### ↩️ Devoluções por Mês")
        if historico_devolucoes:
            df_dev = pd.DataFrame(historico_devolucoes)
            df_dev['timestamp'] = pd.to_datetime(df_dev.get('timestamp', df_dev.get('created_at')), errors='coerce')
            df_dev = df_dev.dropna(subset=['timestamp'])
            if not df_dev.empty:
                df_dev['mes_dt'] = df_dev['timestamp'].dt.to_period('M').dt.to_timestamp()
                df_dev['mes'] = df_dev['timestamp'].apply(formatar_mes)
                dev_mes = df_dev.groupby(['mes_dt', 'mes']).size().reset_index(name='Devoluções')
                dev_mes = dev_mes.sort_values('mes_dt')
                
                fig4 = px.bar(dev_mes, x='mes', y='Devoluções',
                              color='Devoluções', color_continuous_scale='Reds',
                              text='Devoluções')
                fig4.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)', 
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis_title="Mês",
                    yaxis_title="Quantidade",
                    xaxis={'categoryorder': 'array', 'categoryarray': dev_mes['mes'].tolist()}
                )
                st.plotly_chart(fig4, use_container_width=True)
            else:
                st.info("Nenhuma devolução no período.")
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
    else:
        st.info("Sem dados de tipos de processo para exibir.")

else:
    st.info("📋 Nenhum processo concluído no período selecionado. Ajuste os filtros de data.")

st.markdown("---")
with st.expander("ℹ️ Metodologia e Memória de Cálculo"):
    st.markdown("""
    ### 📝 Como os indicadores são calculados?
    
    Esta página utiliza a **mesma metodologia oficial** do Relatório Mensal de Produtividade (MPC/SC), garantindo consistência entre seus dados pessoais e o relatório institucional.
    
    #### 1. Tempo Médio (Duração)
    Calcula a média de dias entre a **Data de Atribuição** e a **Data de Conclusão** de cada processo, em regra, contado em dias corridos descontados afastamentos.
    - **Dias Úteis:** Para processos com contagem em dias úteis, descontamos fins de semana, afastamento e feriados oficiais.
    - **Suspensão:** Dias de suspensão manual (lançados no sistema) são descontados da duração total.
    - **Afastamentos:** O sistema respeita as regras de contagem baseadas no tipo de prazo.
    
    #### 2. Percentual No Prazo
    Um processo é considerado "No Prazo" se:  
    `Data Conclusão <= Data Atribuição + Prazo (em dias) + Suspensões e afastamentos`
    
    #### 3. Pendentes Revisão
    Reflete o **estado atual** da sua fila de espera. Inclui:
    - Processos que você já concluiu, mas o Chefe ainda não revisou.
    - Processos que foram **devolvidos** pelo Chefe ou Procurador e aguardam nova atuação.
    - *Exclui:* Processos marcados como "Não se aplica prazo" ou que pulam a etapa de revisão.
    
    #### 4. Devoluções
    Contabiliza quantas vezes um processo retornou para sua fase (devolvido pelo Chefe) dentro do período selecionado.
    """)


