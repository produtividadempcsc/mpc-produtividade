import auth
import streamlit as st
import pandas as pd
from datetime import date
from utils.timezone import today_brazil
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

# CSS CUSTOMIZADO PARA LAYOUT PROFISSIONAL (Centralizado)
import ui_utils
ui_utils.load_css("style.css")

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
    
    today = today_brazil()
    
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
                        value=today_brazil(), 
                        format="DD/MM/YYYY",
                        help="Quando a substituição começará"
                    )
                with col4:
                    data_fim = st.date_input(
                        "📅 Data de Fim", 
                        value=today_brazil(), 
                        format="DD/MM/YYYY",
                        help="Quando a substituição terminará"
                    )
                
                st.markdown("</br>", unsafe_allow_html=True)
                
                col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
                with col_btn2:
                    if st.form_submit_button("✅ Registrar Substituição", width='stretch'):
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
            width='stretch', 
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
                
                if sub_para_remover_label and st.button("🗑️ Remover", type="primary", width='stretch'):
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