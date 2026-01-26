import auth
import streamlit as st
import pandas as pd
from datetime import date
from sidebar import build_sidebar

# Módulos do projeto
# Módulos do projeto
# from database import get_db, Usuario, Substituicao
from db_compat import (
    get_all_users, get_user_by_id, 
    get_all_substituicoes, get_substituicoes_by_chefe, 
    create_substituicao, delete_substituicao
)
from datetime import datetime

auth.auth_guard()

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
allowed_profiles = ["Administrador", "Chefe de Gabinete", "Procurador"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Você não tem permissão para acessar esta página.")
    st.stop()
# ==============================================================================

# CSS CUSTOMIZADO PARA LAYOUT PROFISSIONAL
st.markdown("""
<style>
    /* Variáveis CSS para cores do sistema */
    :root {
        --primary-color: #9E0520;
        --background-color: #E9E3DF;
        --secondary-background: #9CAFAA;
        --text-color: #000000;
        --card-shadow: 0 4px 12px rgba(158, 5, 32, 0.1);
        --border-radius: 12px;
        --transition: all 0.3s ease;
    }

    /* Estilização do título principal */
    .main-title {
        background: linear-gradient(135deg, var(--primary-color), #7a041a);
        color: white;
        padding: 2rem;
        border-radius: var(--border-radius);
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: var(--card-shadow);
    }

    .main-title h1 {
        margin: 0;
        font-size: 2.5rem;
        font-weight: 700;
        text-shadow: 0 2px 4px rgba(0,0,0,0.3);
    }

    .main-title p {
        margin: 0.5rem 0 0 0;
        font-size: 1.1rem;
        opacity: 0.9;
    }

    /* Cards profissionais */
    .professional-card {
        background: white;
        border-radius: var(--border-radius);
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: var(--card-shadow);
        border-left: 4px solid var(--primary-color);
        transition: var(--transition);
    }

    .professional-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(158, 5, 32, 0.15);
    }

    /* Seções com destaque */
    .section-header {
        background: var(--secondary-background);
        color: var(--text-color);
        padding: 1rem 1.5rem;
        border-radius: var(--border-radius);
        margin: 1.5rem 0 1rem 0;
        font-weight: 600;
        font-size: 1.2rem;
        border-left: 4px solid var(--primary-color);
    }

    /* Formulários elegantes */
    .stForm {
        background: white;
        border-radius: var(--border-radius);
        padding: 1.5rem;
        box-shadow: var(--card-shadow);
        border: 1px solid rgba(158, 5, 32, 0.1);
    }

    /* Botões customizados */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary-color), #7a041a);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 2rem;
        font-weight: 600;
        transition: var(--transition);
        box-shadow: 0 2px 8px rgba(158, 5, 32, 0.2);
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(158, 5, 32, 0.3);
    }

    /* Tabelas profissionais */
    .dataframe {
        border-radius: var(--border-radius);
        overflow: hidden;
        box-shadow: var(--card-shadow);
    }

    /* Status badges */
    .status-badge {
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        text-align: center;
        display: inline-block;
        min-width: 80px;
    }

    .status-ativa {
        background: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }

    .status-encerrada {
        background: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }

    .status-agendada {
        background: #d1ecf1;
        color: #0c5460;
        border: 1px solid #bee5eb;
    }

    /* Expander customizado */
    .streamlit-expanderHeader {
        background: var(--secondary-background);
        border-radius: var(--border-radius);
        font-weight: 600;
    }

    /* Alertas customizados */
    .stAlert {
        border-radius: var(--border-radius);
        border-left: 4px solid var(--primary-color);
    }

    /* Separadores elegantes */
    .custom-separator {
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--primary-color), transparent);
        margin: 2rem 0;
        border: none;
    }

    /* Métricas visuais */
    .metric-card {
        background: white;
        border-radius: var(--border-radius);
        padding: 1rem;
        text-align: center;
        box-shadow: var(--card-shadow);
        border-top: 3px solid var(--primary-color);
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--primary-color);
        margin: 0;
    }

    .metric-label {
        font-size: 0.9rem;
        color: #666;
        margin: 0.5rem 0 0 0;
    }

    /* Loading spinner customizado */
    .stSpinner {
        border-color: var(--primary-color);
    }
</style>
""", unsafe_allow_html=True)

st.session_state.active_page = "Gerenciar Substituições"
build_sidebar()

# Título profissional
st.markdown("""
<div class="main-title">
    <h1>🔄 Gerenciar Substituições</h1>
    <p>Designe servidores para assumir responsabilidades de chefia durante períodos específicos</p>
</div>
""", unsafe_allow_html=True)

# db = next(get_db()) # REMOVED
try:
    perfil_atual = st.session_state.active_perfil
    
    # Helpers
    all_users = get_all_users()
    all_subs = get_all_substituicoes()
    
    # Métricas rápidas
    total_substituicoes = len(all_subs)
    
    today = date.today()
    
    ativas = len([s for s in all_subs if 
                  datetime.fromisoformat(s['data_inicio']).date() <= today <= datetime.fromisoformat(s['data_fim']).date()])
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{total_substituicoes}</div>
            <div class="metric-label">Total de Substituições</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{ativas}</div>
            <div class="metric-label">Substituições Ativas</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        agendadas = len([s for s in all_subs if datetime.fromisoformat(s['data_inicio']).date() > today])
        
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{agendadas}</div>
            <div class="metric-label">Substituições Agendadas</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<hr class="custom-separator">', unsafe_allow_html=True)
    
    # --- FORMULÁRIO PARA REGISTRAR NOVA SUBSTITUIÇÃO ---
    st.markdown('<div class="section-header">➕ Registrar Nova Substituição</div>', unsafe_allow_html=True)
    
    with st.container():
        with st.form("add_substituicao_form", clear_on_submit=True):
            
            id_chefe_titular = None
            servidores_para_selecao = {}
            chefe_selecionado_nome = None

            # Get lists
            all_chefes = [u for u in all_users if u.get('perfil') == 'Chefe de Gabinete']
            all_servidores = [u for u in all_users if u.get('perfil') == 'Servidor']

            # Se for Admin ou Procurador, pode escolher qualquer Chefe e qualquer Servidor
            if perfil_atual in ["Administrador", "Procurador"]:
                all_chefes.sort(key=lambda x: x['nome_completo'])
                
                chefes_dict = {c['nome_completo']: c['id'] for c in all_chefes}
                chefe_selecionado_nome = st.selectbox(
                    "🎯 Selecione o Chefe de Gabinete Titular", 
                    options=list(chefes_dict.keys()),
                    help="Escolha o chefe que será substituído"
                )
                if chefe_selecionado_nome:
                    id_chefe_titular = chefes_dict[chefe_selecionado_nome]

                all_servidores.sort(key=lambda x: x['nome_completo'])
                servidores_para_selecao = {s['nome_completo']: s['id'] for s in all_servidores}

            # Se for Chefe de Gabinete, só pode escolher para si mesmo e de sua equipe
            elif perfil_atual == "Chefe de Gabinete":
                id_chefe_titular = st.session_state.active_user_id
                chefe_logado = get_user_by_id(id_chefe_titular)
                
                if chefe_logado:
                    st.text_input(
                        "👤 Chefe de Gabinete Titular", 
                        value=chefe_logado['nome_completo'], 
                        disabled=True,
                        help="Você só pode criar substituições para si mesmo"
                    )
                    
                    # Need to fetch related servidores for this chefe.
                    # Or simpler: all servers, since 'servidores' property in User object was handled by database.
                    # Here we need to find relations.
                    # Let's import update logic or just select relation.
                    from supabase_client import QueryBuilder
                    # Fetch linkage
                    # TODO: add `get_direct_servants` to db_compat? Yes, done in previous task.
                    from db_compat import get_direct_servants
                    servidores_equipe = get_direct_servants(id_chefe_titular)
                    
                    servidores_para_selecao = {s['nome_completo']: s['id'] for s in sorted(servidores_equipe, key=lambda x: x['nome_completo'])}

            # Campos comuns do formulário
            if not servidores_para_selecao:
                st.warning("⚠️ Não há servidores disponíveis para designar como substitutos.")
                st.form_submit_button("Registrar Substituição", disabled=True)
            else:
                col1, col2 = st.columns(2)
                
                with col1:
                    servidor_substituto_nome = st.selectbox(
                        "👥 Selecione o Servidor Substituto", 
                        options=list(servidores_para_selecao.keys()),
                        help="Escolha quem assumirá as responsabilidades"
                    )
                

                
                col3, col4 = st.columns(2)
                with col3:
                    data_inicio = st.date_input(
                        "📅 Data de Início", 
                        value=date.today(), 
                        format="DD/MM/YYYY",
                        help="Quando a substituição começará"
                    )
                with col4:
                    data_fim = st.date_input(
                        "📅 Data de Fim", 
                        value=date.today(), 
                        format="DD/MM/YYYY",
                        help="Quando a substituição terminará"
                    )
                
                st.markdown("</br>", unsafe_allow_html=True)
                
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    if st.form_submit_button("✅ Registrar Substituição", use_container_width=True):
                        if data_fim < data_inicio:
                            st.error("❌ A data de fim não pode ser anterior à data de início.")
                        elif servidor_substituto_nome and id_chefe_titular:
                            nova_substituicao = {
                                "id_chefe_titular": id_chefe_titular,
                                "id_servidor_substituto": servidores_para_selecao[servidor_substituto_nome],
                                "data_inicio": data_inicio.isoformat(),
                                "data_fim": data_fim.isoformat()
                            }
                            create_substituicao(nova_substituicao)

                            st.success(f"✅ Substituição registrada com sucesso!")
                            st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<hr class="custom-separator">', unsafe_allow_html=True)
    
    # --- VISUALIZAÇÃO E REMOÇÃO ---
    st.markdown('<div class="section-header">📊 Histórico de Substituições</div>', unsafe_allow_html=True)

    substituicoes = []
    if perfil_atual == "Chefe de Gabinete":
        # substituicoes_query = substituicoes_query.filter(Substituicao.id_chefe_titular == st.session_state.active_user_id)
        substituicoes = get_substituicoes_by_chefe(st.session_state.active_user_id)
    else:
        substituicoes = all_subs

    if not substituicoes:
        st.markdown("""
        <div>
            <div style="text-align: center; padding: 2rem;">
                <h3>📋 Nenhuma substituição registrada</h3>
                <p>Não há substituições para a visualização atual. Use o formulário acima para registrar a primeira substituição.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Cache de nomes para evitar queries repetidas
        user_names = {u['id']: u['nome_completo'] for u in all_users}
        
        df_data = []
        for sub in substituicoes:
            chefe_nome = user_names.get(sub['id_chefe_titular'], "Desconhecido")
            substituto_nome = user_names.get(sub['id_servidor_substituto'], "Desconhecido")
            
            d_ini = datetime.fromisoformat(sub['data_inicio']).date()
            d_fim = datetime.fromisoformat(sub['data_fim']).date()
            
            # Determinar status com formatação
            if d_ini <= today <= d_fim:
                status = "🟢 Ativa"
                status_class = "status-ativa"
            elif d_fim < today:
                status = "🔴 Encerrada"
                status_class = "status-encerrada"
            else:
                status = "🟡 Agendada"
                status_class = "status-agendada"
            
            row = {
                "ID": sub['id'], 
                "Chefe Titular": chefe_nome, 
                "Substituto": substituto_nome,
                "Data de Início": d_ini.strftime('%d/%m/%Y'),
                "Data de Fim": d_fim.strftime('%d/%m/%Y'),
                "Status": status
            }
            df_data.append(row)
        
        df_substituicoes = pd.DataFrame(df_data)
        
        # Configurar colunas visíveis
        column_config = {
            "ID": None,
            "Status": st.column_config.TextColumn(
                "Status",
                width="small"
            )
        }
        
        if perfil_atual == "Chefe de Gabinete":
            column_config["Chefe Titular"] = None
        
        st.dataframe(
            df_substituicoes, 
            use_container_width=True, 
            hide_index=True, 
            column_config=column_config
        )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<hr class="custom-separator">', unsafe_allow_html=True)
        
        # Seção de remoção
        st.markdown('<div class="section-header">🗑️ Remover Substituição</div>', unsafe_allow_html=True)
        
        
        if not df_substituicoes.empty:
            if perfil_atual in ["Administrador", "Procurador"]:
                options = df_substituicoes.apply(
                    lambda row: f"{row['Chefe Titular']} → {row['Substituto']} ({row['Data de Início']} a {row['Data de Fim']})", 
                    axis=1
                )
            else:  # Visão do Chefe de Gabinete
                options = df_substituicoes.apply(
                    lambda row: f"{row['Substituto']} ({row['Data de Início']} a {row['Data de Fim']})", 
                    axis=1
                )

            col1, col2 = st.columns([3, 1])
            
            with col1:
                sub_para_remover_label = st.selectbox(
                    "🔍 Selecione uma substituição para remover", 
                    options=options, 
                    index=None, 
                    placeholder="Selecione para remover...",
                    help="Escolha a substituição que deseja remover do sistema"
                )

            with col2:
                st.write("")  # Espaçamento
                
                if sub_para_remover_label and st.button("🗑️ Remover", type="primary", use_container_width=True):
                    idx_selecionado = options[options == sub_para_remover_label].index[0]
                    # db_id = df_substituicoes.loc[idx_selecionado, 'ID']
                    # Use iloc as index matches df if filtered? No, `options` and `df_substituicoes` are same length and ordered.
                    # But safest to get by label matching?
                    # The `options` series has the same index as `df_substituicoes`.
                    
                    db_id = df_substituicoes.loc[idx_selecionado, 'ID']
                    
                    delete_substituicao(db_id)
                    st.success("✅ Substituição removida com sucesso.")
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"❌ Ocorreu um erro ao carregar a página: {e}")
# finally:
#     db.close()