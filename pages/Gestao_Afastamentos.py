
import streamlit as st
import auth
import pandas as pd
from datetime import date, datetime
from utils.timezone import today_brazil
from sidebar import build_sidebar
import ui_utils
from db_compat import (
    get_all_users, get_user_by_id, 
    get_direct_servants
)
from repositories.afastamento_repository import get_user_leaves, get_leaves_filtered, create_leave, delete_leave
from supabase_client import QueryBuilder

# --- Guarda e Configuração ---
auth.auth_guard()
st.session_state.active_page = "Gestão de Afastamentos"

# Configuração da Página
st.set_page_config(page_title="Gestão de Afastamentos", page_icon="🗓️", layout="wide")

build_sidebar()
ui_utils.load_css()
ui_utils.load_css("styles/afastamentos.css")

# --- Funções de Renderização das Abas ---

def render_servidores_afastados():
    st.markdown("""
    <div class="custom-header">
        <h1>🏝️ Servidores Afastados</h1>
        <p>Relação de todos os servidores em licença ou férias.</p>
    </div>
    """, unsafe_allow_html=True)
    
    try:
        hoje = today_brazil()
        hoje_str = hoje.isoformat()
        
        with st.spinner("Carregando dados de afastamentos..."):
            # Otimização: Usar COUNT em vez de trazer tudo
            # Precisamos importar get_all_leaves_count. Como ele pode não estar no import do topo,
            # vou usar QueryBuilder otimizado aqui mesmo se preferir, mas melhor usar a função.
            # O arquivo não importa get_all_leaves_count ainda.
            # Vou substituir a query 'todos' por query 'select id'.
            
            todos_afastamentos_count = len(QueryBuilder("afastamentos").select("id").execute())
            afastamentos_ativos = QueryBuilder("afastamentos").lte("data_inicio", hoje_str).gte("data_fim", hoje_str).execute()
        
        all_users = get_all_users()
        users_dict = {u.get('id'): u for u in all_users}
        
        st.markdown(f"**Data de Referência:** {hoje.strftime('%d/%m/%Y')}")
        
        # Estatísticas
        col1, col2, col3 = st.columns(3)
        total_ativos = len(afastamentos_ativos)
        total_geral = todos_afastamentos_count
        
        col1.metric("Afastamentos Ativos", total_ativos)
        col2.metric("Total de Registros", total_geral)
        pct = (total_ativos / max(total_geral, 1)) * 100
        col3.metric("Percentual Ativo", f"{pct:.1f}%")
        
        st.markdown("---")
        
        if not afastamentos_ativos:
            st.info("🟢 Não há servidores afastados no momento.")
        else:
            df_data = []
            for af in afastamentos_ativos:
                user_id = af.get('id_usuario')
                servidor = users_dict.get(user_id, {})
                
                din = datetime.fromisoformat(af.get('data_inicio')).date() if af.get('data_inicio') else None
                dout = datetime.fromisoformat(af.get('data_fim')).date() if af.get('data_fim') else None
                
                dias_rest = (dout - hoje).days if dout else 0
                status_dias = f"{dias_rest} dias restantes" if dias_rest > 0 else "Último dia"
                
                df_data.append({
                    "Servidor": servidor.get('nome_completo', 'Desconhecido'),
                    "Descrição": af.get('descricao', ''),
                    "Início": din.strftime('%d/%m/%Y') if din else '-',
                    "Fim": dout.strftime('%d/%m/%Y') if dout else '-',
                    "Status": status_dias
                })
            
            df = pd.DataFrame(df_data).sort_values("Servidor")
            st.dataframe(df, width='stretch', hide_index=True)
            
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")

def render_meus_afastamentos():
    st.markdown("## 🌴 Meus Afastamentos")
    
    user_id = st.session_state.user_id
    afastamentos = get_user_leaves(user_id)
    
    if not afastamentos:
        st.info("Você não possui afastamentos registrados.")
    else:
        st.metric("Total de Afastamentos", len(afastamentos))
        
        for i, af in enumerate(afastamentos):
            din = datetime.fromisoformat(af.get('data_inicio')).date()
            dout = datetime.fromisoformat(af.get('data_fim')).date()
            duracao = (dout - din).days + 1
            
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"**Descrição:**\n{af.get('descricao')}")
                c2.markdown(f"**Início:**\n{din.strftime('%d/%m/%Y')}")
                c3.markdown(f"**Fim:**\n{dout.strftime('%d/%m/%Y')}")
                c4.markdown(f"**Duração:**\n{duracao} dias")

def render_gerenciar_afastamentos():
    st.markdown("## 🗓️ Gerenciar Afastamentos")
    
    usuarios_gerenciaveis = []
    if st.session_state.active_perfil == "Chefe de Gabinete":
        uid = st.session_state.active_user_id
        me = get_user_by_id(uid)
        subs = get_direct_servants(uid)
        usuarios_gerenciaveis = [me] + subs if me else subs
    elif st.session_state.active_perfil in ["Administrador", "Procurador"]:
        usuarios_gerenciaveis = get_all_users()
    else:
        st.warning("Seu perfil não permite gerenciar afastamentos de terceiros.")
        return

    usuarios_gerenciaveis.sort(key=lambda u: u.get('nome_completo', ''))
    usuarios_dict = {u['nome_completo']: u['id'] for u in usuarios_gerenciaveis}
    ids_gerenciaveis = list(usuarios_dict.values())
    
    # Form
    with st.expander("➕ Registrar Novo Afastamento", expanded=False):
        with st.form("new_leave"):
            c1, c2 = st.columns(2)
            user_name = c1.selectbox("Usuário", list(usuarios_dict.keys()))
            desc = c1.text_input("Descrição", placeholder="Ex: Férias")
            d_ini = c2.date_input("Início", value=today_brazil())
            d_fim = c2.date_input("Fim", value=today_brazil())
            
            if st.form_submit_button("Registrar", type="primary"):
                if d_fim < d_ini:
                    st.error("Data final deve ser posterior a inicial.")
                elif not desc:
                    st.error("Descrição obrigatória.")
                else:
                    create_leave(usuarios_dict[user_name], d_ini, d_fim, desc)
                    st.success("Registrado!")
                    st.rerun()
    
    # Listagem
    st.markdown("### Registros")
    leaves = get_leaves_filtered(ids_gerenciaveis)
    
    if not leaves:
        st.info("Nenhum registro encontrado.")
    else:
        # Filtros
        fc1, fc2, fc3 = st.columns(3)
        f_user = fc1.selectbox("Filtrar Usuário", ["Todos"] + list(usuarios_dict.keys()))
        f_desc = fc3.text_input("Filtrar Descrição")
        
        filtered = []
        for l in leaves:
            u_name = next((n for n, i in usuarios_dict.items() if i == l['id_usuario']), "Desconhecido")
            if f_user != "Todos" and u_name != f_user: continue
            if f_desc and f_desc.lower() not in l.get('descricao', '').lower(): continue
            
            filtered.append({
                "ID": l['id'],
                "Usuário": u_name,
                "Descrição": l.get('descricao'),
                "Início": date.fromisoformat(l['data_inicio']).strftime('%d/%m/%Y'),
                "Fim": date.fromisoformat(l['data_fim']).strftime('%d/%m/%Y')
            })
            
        st.dataframe(pd.DataFrame(filtered), width='stretch', hide_index=True)
        
        # Remoção
        st.markdown("---")
        st.subheader("Remover Registro")
        opts = [f"{l['ID']} - {l['Usuário']} ({l['Descrição']})" for l in filtered]
        sel_del = st.selectbox("Selecione para remover", [None] + opts)
        if sel_del and st.button("🗑️ Remover", type="primary"):
            lid = int(sel_del.split(' - ')[0])
            if delete_leave(lid):
                st.success("Removido!")
                st.rerun()
            else:
                st.error("Erro ao remover.")

# --- Layout Principal ---

tabs = st.tabs(["🏝️ Servidores Afastados", "🌴 Meus Afastamentos", "🗓️ Gerenciar"])

with tabs[0]:
    render_servidores_afastados()

with tabs[1]:
    render_meus_afastamentos()

with tabs[2]:
    render_gerenciar_afastamentos()
