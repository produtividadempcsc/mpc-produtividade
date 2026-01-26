import streamlit as st
import auth
from utils.ui import load_logo
from supabase_client import supabase, QueryBuilder, select_where, count as sb_count

MENU_ITEMS = {
    "Início": "app.py",
    "Meu Perfil": "pages/Meu_Perfil.py",
    "Administração": "pages/Administracao.py",
    "Meus Processos": "pages/Meus_Processos.py",
    "Processos MPC": "pages/Processos_MPC.py",
    "Processos no Gabinete": "pages/Processos_no_Gabinete.py",
    "Processos para Revisão": "pages/Processos_para_Revisao.py",
    "Processos com Procurador": "pages/Processos_com_Procurador.py",
    "Gerenciar Usuários": "pages/Gerenciar_Usuarios.py",
    "Central IA": "pages/AI_Central.py",
    "Gestão de Afastamentos": "pages/Gestao_Afastamentos.py",
    "Gerenciar Substituições": "pages/Gerenciar_Substituicoes.py",
    "Manual do Usuário": "pages/Manual_do_Usuario.py",
    "Página Analítica": "pages/Pagina_Analitica.py"
}

PROFILE_MENUS = {
    "Administrador": ["Meu Perfil", "Administração", "Gerenciar Usuários", "Processos MPC", "Gestão de Afastamentos", "Gerenciar Substituições", "Página Analítica", "Central IA", "Manual do Usuário"],
    "Servidor": ["Meu Perfil", "Meus Processos", "Página Analítica", "Central IA", "Gestão de Afastamentos", "Manual do Usuário"],
    "Chefe de Gabinete": ["Meu Perfil", "Meus Processos", "Processos no Gabinete", "Processos para Revisão", "Processos com Procurador", "Gerenciar Usuários", "Gestão de Afastamentos", "Gerenciar Substituições", "Página Analítica", "Central IA", "Manual do Usuário"],
    "Procurador": ["Meu Perfil", "Processos MPC", "Página Analítica", "Central IA", "Gestão de Afastamentos", "Gerenciar Substituições", "Manual do Usuário"]
}

def build_sidebar():
    """
    Renderiza a sidebar completa e consistente em todas as páginas,
    com o novo estilo visual inspirado no módulo de comentários.
    """
    
    # CSS personalizado para a sidebar
    st.markdown("""
    <style>
        /* Importar a fonte Inter, usada em todo o sistema para consistência */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

        /* Ocultar a navegação padrão do Streamlit, que não é utilizada no projeto */
        [data-testid='stSidebarNav'] {
            display: none;
        }

        /* Container principal da sidebar */
        [data-testid="stSidebar"] {
            background-color: #F0F2F6; /* Cinza claro suave para um visual limpo */
            border-right: 2px solid #E0E0E0;
        }

        /* Logo na sidebar */
        [data-testid="stSidebar"] .stImage {
            padding: 1rem;
            border-bottom: 2px solid #E0E0E0;
            margin-bottom: 1rem;
        }

        /* Título de boas-vindas e nome do usuário */
        [data-testid="stSidebar"] .stHeadingContainer h1 {
            font-family: 'Inter', sans-serif;
            color: #B71C1C; /* Vermelho institucional escuro */
            font-weight: 700;
            font-size: 1.5rem; /* Tamanho ajustado para hierarquia */
            padding-top: 0;
        }
        
        [data-testid="stSidebar"] .stSidebarHeader {
            font-family: 'Inter', sans-serif;
            color: #1E1E1E;
            font-weight: 700;
            font-size: 1.3rem;
            padding-left: 0.5rem;
            padding-right: 0.5rem;
        }

        /* Texto geral na sidebar (Perfil Ativo) */
        [data-testid="stSidebar"] .stMarkdown p {
            font-family: 'Inter', sans-serif;
            color: #333333;
            font-weight: 500;
            font-size: 1rem;
            padding-left: 0.5rem;
        }
        
        /* Destaque para o nome do perfil */
        [data-testid="stSidebar"] .stMarkdown p strong {
            color: #D32F2F; /* Vermelho institucional principal */
            font-weight: 700;
        }

        /* Estilo base comum para todos os botões na sidebar */
        [data-testid="stSidebar"] .stButton > button {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            font-size: 0.95rem;
            border-radius: 50px; /* Bordas totalmente arredondadas */
            border: 2px solid transparent;
            transition: all 0.3s ease;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 0.75rem 1rem;
            margin-bottom: 0.5rem; /* Espaçamento entre os botões */
        }

        /* Estilo para botões de página ATIVA (type="primary") com a cor personalizada */
        [data-testid="stSidebar"] .stButton > button[kind="primary"] {
            background-color: #9E0520;
            color: white;
            border-color: #8B041C; /* Um tom ligeiramente mais escuro para a borda */
            box-shadow: 0 4px 15px rgba(158, 5, 32, 0.3);
        }
        
        /* Manter o botão ativo sem efeito de hover para não distrair */
        [data-testid="stSidebar"] .stButton > button[kind="primary"]:hover {
            transform: none;
            box-shadow: 0 4px 15px rgba(158, 5, 32, 0.3);
        }

        /* Estilo para botões de página INATIVA (type="secondary") */
        [data-testid="stSidebar"] .stButton > button[kind="secondary"] {
            background-color: #4C4D4F;
            color: #FFFFFF;
            border: 2px solid #3C3D3F; /* Borda um pouco mais escura para profundidade */
        }

        /* Efeito HOVER para botões de página INATIVA */
        [data-testid="stSidebar"] .stButton > button[kind="secondary"]:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(211, 47, 47, 0.2);
            background: linear-gradient(135deg, #D32F2F, #B71C1C);
            color: white;
            border-color: transparent;
        }

        /* Botão de SAIR - Estilo distinto e final */
        [data-testid="stSidebar"] .stButton:last-of-type > button {
            background: #333333;
            color: white;
            border: 2px solid #333333;
        }
        
        [data-testid="stSidebar"] .stButton:last-of-type > button:hover {
            background: linear-gradient(135deg, #B71C1C, #D32F2F);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            border-color: transparent;
            transform: translateY(-2px);
        }
        
        /* Linha divisória */
        [data-testid="stSidebar"] hr {
            border-top: 2px solid #D32F2F;
            margin: 1rem 0;
        }

        /* Popover de notificações */
        [data-testid="stSidebar"] [data-testid="stPopover"] > button {
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            font-size: 0.95rem;
            border-radius: 50px;
            border: 2px solid #D32F2F;
            background-color: #FFFFFF;
            color: #D32F2F;
            transition: all 0.3s ease;
            width: 100%;
            margin-bottom: 0.5rem;
        }
        
        [data-testid="stSidebar"] [data-testid="stPopover"] > button:hover {
            background: linear-gradient(135deg, #D32F2F, #B71C1C);
            color: white;
            border-color: transparent;
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(211, 47, 47, 0.2);
        }
    </style>
    """, unsafe_allow_html=True)
    
    logo = load_logo()
    if logo:
        st.sidebar.image(logo, width='stretch')
    st.sidebar.title(f"Bem-vindo(a),")
    st.sidebar.header(st.session_state.get("user_nome", "")) 
    st.sidebar.markdown(f"Perfil Ativo: **{st.session_state.get('active_perfil', '')}**")
    st.sidebar.markdown("---")

    # Seção de notificações (usando Supabase REST API)
    if st.session_state.get("user_id"):
        try:
            user_id = st.session_state.user_id
            
            # Contar notificações não lidas
            unread_notifs = QueryBuilder("notificacoes") \
                .eq("id_usuario_destino", user_id) \
                .eq("lida", False) \
                .execute()
            unread_count = len(unread_notifs)
            
            bell_label = f"🔔 Notificações ({unread_count} novas)" if unread_count > 0 else "🔔 Notificações"
            
            with st.sidebar.popover(bell_label, width='stretch'):
                st.markdown("#### Últimas Notificações")
                
                # Buscar últimas 10 notificações
                notificacoes = QueryBuilder("notificacoes") \
                    .eq("id_usuario_destino", user_id) \
                    .order("timestamp", desc=True) \
                    .limit(10) \
                    .execute()
                
                if not notificacoes:
                    st.write("Nenhuma notificação.")
                else:
                    for n in notificacoes:
                        icon = "🔵" if not n.get('lida') else "⚪"
                        timestamp = n.get('timestamp', '')[:16].replace('T', ' ')  # Format timestamp
                        st.markdown(f"{icon} **{timestamp}** - {n.get('mensagem', '')}")
                
                # Marcar como lidas ao abrir
                if unread_count > 0:
                    for notif in unread_notifs:
                        supabase.table("notificacoes").update({"lida": True}).eq("id", notif['id']).execute()
        except Exception as e:
            print(f"[SIDEBAR] Erro ao carregar notificações: {e}")

    # Menus de navegação baseados no perfil
    allowed_menus = PROFILE_MENUS.get(st.session_state.get("active_perfil"), [])
    active_page = st.session_state.get("active_page", "Início")

    for page_label in allowed_menus:
        is_active = (page_label == active_page)
        button_type = "primary" if is_active else "secondary"
        if st.sidebar.button(page_label, width='stretch', type=button_type, key=f"btn_{page_label}"):
            if not is_active:
                st.switch_page(MENU_ITEMS[page_label])
    
    st.sidebar.markdown("---")
    
    # Botão de Logout
    if st.sidebar.button('🔴 Sair do Sistema', width='stretch', key="btn_logout"):
        auth.logout_user()
        st.rerun()