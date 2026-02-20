import streamlit as st
import auth
from utils.ui import load_logo
from supabase_client import supabase, QueryBuilder, select_where, count as sb_count

MENU_ITEMS = {
    "Início": "app.py",
    "Meu Perfil": "pages/Meu_Perfil.py",
    "Administração": "pages/Administracao.py",
    "Meus Processos": "pages/Meus_Processos.py",
    "Meus Dados": "pages/Meus_Dados.py",
    "Processos MPC": "pages/Processos_MPC.py",
    "Processos no Gabinete": "pages/Processos_no_Gabinete.py",
    "Processos para Revisão": "pages/Processos_para_Revisao.py",
    "Processos com Procurador": "pages/Processos_com_Procurador.py",
    "Gerenciar Usuários": "pages/Gerenciar_Usuarios.py",
    "Central IA": "pages/AI_Central.py",
    "Gestão de Afastamentos": "pages/Gestao_Afastamentos.py",
    "Gerenciar Substituições": "pages/Gerenciar_Substituicoes.py",
    "Manual do Usuário": "pages/Manual_do_Usuario.py",
    "Gabinete em Números": "pages/Gabinete_em_Numeros.py",
    "MPC em Números": "pages/MPC_em_Numeros.py"
}

PROFILE_MENUS = {
    "Administrador": ["Meu Perfil", "Administração", "Gerenciar Usuários", "Processos MPC", "MPC em Números", "Gabinete em Números", "Gestão de Afastamentos", "Gerenciar Substituições", "Central IA", "Manual do Usuário"],
    "Servidor": ["Meu Perfil", "Meus Processos", "Meus Dados", "Central IA", "Gestão de Afastamentos", "Manual do Usuário"],
    "Chefe de Gabinete": ["Meu Perfil", "Meus Processos", "Processos no Gabinete", "Gabinete em Números", "Processos para Revisão", "Processos com Procurador", "Gerenciar Usuários", "Gestão de Afastamentos", "Gerenciar Substituições", "Central IA", "Manual do Usuário"],
    "Procurador": ["Meu Perfil", "Processos MPC", "MPC em Números", "Gabinete em Números", "Central IA", "Gestão de Afastamentos", "Gerenciar Substituições", "Manual do Usuário"]
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
            
            # Ícone do sino com animação quando há notificações
            if unread_count > 0:
                st.sidebar.markdown("""
                <style>
                    @keyframes bellPulse {
                        0% { transform: scale(1); }
                        50% { transform: scale(1.15); }
                        100% { transform: scale(1); }
                    }
                    .notif-badge {
                        display: inline-block;
                        animation: bellPulse 1.5s ease-in-out infinite;
                    }
                </style>
                """, unsafe_allow_html=True)
                bell_label = f"🔔 Notificações ({unread_count} novas)"
            else:
                bell_label = "🔔 Notificações"
            
            # Mapear tipos para ícones
            TIPO_ICONS = {
                "prazo": "🔴",
                "devolucao": "🔄",
                "conclusao": "✅",
                "comentario": "💬",
                "atribuicao": "📋",
                "sistema": "⚙️",
            }
            
            TIPO_LABELS = {
                "prazo": "Prazo",
                "devolucao": "Devolução",
                "conclusao": "Conclusão",
                "comentario": "Comentário",
                "atribuicao": "Atribuição",
                "sistema": "Sistema",
            }
            
            with st.sidebar.popover(bell_label, width='stretch'):
                st.markdown("#### 🔔 Central de Notificações")
                
                # Buscar últimas 20 notificações
                notificacoes = QueryBuilder("notificacoes") \
                    .eq("id_usuario_destino", user_id) \
                    .order("timestamp", desc=True) \
                    .limit(20) \
                    .execute()
                
                if not notificacoes:
                    st.info("📭 Nenhuma notificação no momento.")
                else:
                    for n in notificacoes:
                        is_unread = not n.get('lida', True)
                        tipo = n.get('tipo', 'sistema')
                        tipo_icon = TIPO_ICONS.get(tipo, "⚙️")
                        tipo_label = TIPO_LABELS.get(tipo, "Sistema")
                        
                        timestamp = n.get('timestamp', '')[:16].replace('T', ' ')
                        mensagem = n.get('mensagem', '')
                        id_processo = n.get('id_processo')
                        
                        # Indicador visual de não lida
                        bg = "background: #FFF3E0; border-left: 3px solid #FF9800;" if is_unread else "border-left: 3px solid #E0E0E0;"
                        weight = "font-weight: 600;" if is_unread else ""
                        
                        st.markdown(f"""
                        <div style="padding: 8px 10px; margin-bottom: 6px; border-radius: 6px; {bg} font-size: 0.82rem;">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px;">
                                <span style="color: #888; font-size: 0.72rem;">{tipo_icon} {tipo_label}</span>
                                <span style="color: #999; font-size: 0.72rem;">{timestamp}</span>
                            </div>
                            <div style="{weight} color: #333; line-height: 1.3;">{mensagem}</div>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    # Botão para marcar todas como lidas
                    if unread_count > 0:
                        if st.button("✅ Marcar todas como lidas", key="btn_mark_all_read", use_container_width=True):
                            for notif in unread_notifs:
                                supabase.table("notificacoes").update({"lida": True}).eq("id", notif['id']).execute()
                            st.rerun()
                    
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