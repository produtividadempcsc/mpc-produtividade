import auth
import streamlit as st
import pandas as pd
from datetime import date
from sidebar import build_sidebar
from supabase_client import QueryBuilder
from utils.timezone import today_brazil
from utils.analytics_utils import (
    prepare_master_dataframe, calculate_metrics_servidor,
    calculate_acervo_snapshot
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
ui_utils.load_css("style.css")

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
    
    return processos, usuarios, tipos

# Mostrar loading enquanto carrega
loading_placeholder.markdown('''
<div class="loading-container">
    <div class="loading-spinner"></div>
    <div class="loading-text">🔄 Carregando dados e calculando indicadores...</div>
    <p style="color: #888; margin-top: 10px; font-size: 0.9em;">Isso pode levar alguns segundos</p>
</div>
''', unsafe_allow_html=True)

all_user_processes, all_users, all_types = load_user_data(user_id)

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

f_ini_ts = pd.to_datetime(f_ini)
f_fim_ts = pd.to_datetime(f_fim)

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
        (df_servidor['data_conclusao_servidor'].dt.normalize() >= f_ini_ts) &
        (df_servidor['data_conclusao_servidor'].dt.normalize() <= f_fim_ts)
    ].copy()
    
    if filtro_tipos:
        df_filtered = df_filtered[df_filtered['nome_produto'].isin(filtro_tipos)]

# Buscar processos pendentes de revisão (concluídos pelo servidor, aguardando chefe) using official logic
# Returns (acervo_servidor, acervo_chefe) - we want both
acervo_s_now, df_acervo_chefe = calculate_acervo_snapshot(df_master, pd.Timestamp.now())
processos_pendentes_servidor = len(acervo_s_now)  # Métrica 4 do Relatório
processos_pendentes_revisao = len(df_acervo_chefe)  # Métrica 8 do Relatório



# Limpar loading após processamento
loading_placeholder.empty()

# --- KPIs (alinhados com métricas do Relatório Mensal) ---
st.markdown("### 📈 Indicadores do Período")

c1, c2, c3 = st.columns(3)
c4, c5 = st.columns(2)

# Calcular KPIs
total_concluidos = len(df_filtered) if not df_filtered.empty else 0
tempo_medio = df_filtered['duracao_servidor'].mean() if not df_filtered.empty and 'duracao_servidor' in df_filtered.columns else 0
pct_no_prazo = (df_filtered['no_prazo_servidor'].sum() / total_concluidos * 100) if total_concluidos > 0 else 0
pendentes_servidor = processos_pendentes_servidor
pendentes_revisao = processos_pendentes_revisao

with c1:
    st.metric("✅ Concluídos", f"{total_concluidos}", help="Métrica 1 do Relatório Mensal — processos concluídos no período")

with c2:
    st.metric("⏱️ Tempo Médio", f"{tempo_medio:.1f} dias" if tempo_medio else "N/A", help="Métrica 2 do Relatório Mensal — média de dias para concluir")

with c3:
    st.metric("📊 No Prazo", f"{pct_no_prazo:.1f}%", help="Métrica 3 do Relatório Mensal — % concluídos dentro do prazo")

with c4:
    st.metric("📂 Acervo Pendente (Servidor)", f"{pendentes_servidor}", help="Métrica 4 do Relatório Mensal — processos não concluídos")

with c5:
    st.metric("🔍 Pendentes Revisão", f"{pendentes_revisao}", help="Métrica 8 do Relatório Mensal — processos aguardando revisão do chefe")

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
    
    # Gráfico 1: Processos Concluídos por Mês (Métrica 1 - igual ao relatorios.py)
    st.markdown("#### 📋 Processos Concluídos por Mês")
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
        st.plotly_chart(fig1, width='stretch')
    else:
        st.info("Sem dados para exibir.")
    
    st.markdown("---")
    
    # Gráfico 2: Tempo Médio por Servidor (Métrica 2 - igual ao relatorios.py)
    st.markdown("#### ⏱️ Tempo Médio de Conclusão (dias)")
    tempo_mes = df_filtered.groupby(['mes_dt', 'mes'])['duracao_servidor'].mean().reset_index(name='Tempo Médio')
    tempo_mes = tempo_mes.sort_values('mes_dt')
    tempo_mes['Tempo Médio'] = tempo_mes['Tempo Médio'].round(2)
    if not tempo_mes.empty:
        fig2 = px.bar(tempo_mes, x='mes', y='Tempo Médio',
                      color='Tempo Médio', color_continuous_scale='blues',
                      text=tempo_mes['Tempo Médio'].apply(lambda x: f'{x:.2f}'))
        fig2.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Mês",
            yaxis_title="Dias",
            xaxis={'categoryorder': 'array', 'categoryarray': tempo_mes['mes'].tolist()}
        )
        st.plotly_chart(fig2, width='stretch')
    else:
        st.info("Sem dados para exibir.")
    
    st.markdown("---")
    
    # Gráfico 3: Percentual de Processos Concluídos no Prazo (Métrica 3 - igual ao relatorios.py)
    st.markdown("#### ✅ Percentual de Processos Concluídos no Prazo")
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
            yaxis_range=[0, 105],
            xaxis={'categoryorder': 'array', 'categoryarray': prazo_mes['mes'].tolist()}
        )
        st.plotly_chart(fig3, width='stretch')
    else:
        st.info("Sem dados para exibir.")
    
    st.markdown("---")
    
    # --- Gráfico: Distribuição por Tipo de Processo (em barras) ---
    st.markdown("### 📊 Distribuição por Tipo de Processo")
    
    tipos_count = df_filtered['nome_produto'].value_counts().reset_index()
    tipos_count.columns = ['Tipo', 'Quantidade']
    
    if not tipos_count.empty:
        tipos_count = tipos_count.sort_values('Quantidade', ascending=True)
        fig5 = px.bar(tipos_count, x='Quantidade', y='Tipo',
                      orientation='h',
                      color='Quantidade', color_continuous_scale='viridis',
                      text='Quantidade')
        fig5.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', 
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis_title="Quantidade",
            yaxis_title="",
            height=max(350, len(tipos_count) * 40)
        )
        st.plotly_chart(fig5, width='stretch')
    else:
        st.info("Sem dados de tipos de processo para exibir.")

else:
    st.info("📋 Nenhum processo concluído no período selecionado. Ajuste os filtros de data.")

st.markdown("---")
with st.expander("ℹ️ Metodologia e Memória de Cálculo"):
    st.markdown("""
    ### 📝 Como os indicadores são calculados?
    
    Esta página utiliza a **mesma metodologia oficial** do Relatório Mensal de Produtividade (MPC/SC), garantindo consistência entre seus dados pessoais e o relatório institucional.
    
    #### 1. Processos Concluídos (Métrica 1)
    Contabiliza o número de processos concluídos pelo servidor no período selecionado.
    
    #### 2. Tempo Médio (Métrica 2)
    Calcula a média de dias entre a **Data de Atribuição** e a **Data de Conclusão** de cada processo.
    - **Dias Úteis:** Para processos com contagem em dias úteis, descontamos fins de semana e feriados oficiais.
    - **Suspensão:** Dias de suspensão manual (lançados no sistema) são descontados da duração total.
    - **Afastamentos:** O sistema respeita as regras de contagem baseadas no tipo de prazo.
    
    #### 3. Percentual No Prazo (Métrica 3)
    Um processo é considerado "No Prazo" se:  
    `Data Conclusão <= Data Atribuição + Prazo (em dias) + Suspensões`
    
    #### 4. Pendentes Revisão
    Reflete o **estado atual** da sua fila de espera. Inclui:
    - Processos que você já concluiu, mas o Chefe ainda não revisou.
    - Processos que foram **devolvidos** pelo Chefe ou Procurador e aguardam nova atuação.
    - *Exclui:* Processos marcados como "Não se aplica prazo" ou que pulam a etapa de revisão.
    """)
