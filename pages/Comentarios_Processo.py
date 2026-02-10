import streamlit as st
import auth
from datetime import datetime, date
from sidebar import build_sidebar
from supabase_client import select_all, QueryBuilder, insert
from db_compat import get_user_by_id, get_process_comments, mark_comments_as_read

auth.auth_guard()

st.set_page_config(
    page_title="Comentários do Processo - MPC-SC",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

build_sidebar()

# CSS personalizado seguindo o padrão do MPC-SC
st.markdown("""
<style>
    /* Importar fonte oficial */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    /* Reset e configurações gerais */
    .main {
        font-family: 'Inter', sans-serif;
        padding-top: 1rem;
        background-color: #FFFFFF;
    }
    
    /* Header principal do sistema */
    .mpc-header {
        background: linear-gradient(135deg, #D32F2F 0%, #B71C1C 100%);
        padding: 2.5rem 2rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 40px rgba(211, 47, 47, 0.15);
        position: relative;
        overflow: hidden;
    }
    
    .mpc-header::before {
        content: '';
        position: absolute;
        top: 0;
        right: 0;
        width: 200px;
        height: 200px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 50%;
        transform: translate(50%, -50%);
    }
    
    .mpc-header-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0;
        text-align: center;
        text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        z-index: 2;
        position: relative;
    }
    
    .mpc-header-subtitle {
        text-align: center;
        margin-top: 1rem;
        font-size: 1.3rem;
        opacity: 0.95;
        font-weight: 500;
        z-index: 2;
        position: relative;
    }
    
    /* Botão voltar institucional */
    .mpc-voltar-container {
        margin-bottom: 2rem;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #D32F2F 0%, #B71C1C 100%);
        color: white !important;
        border: none;
        padding: 0.75rem 2rem;
        border-radius: 50px;
        font-weight: 600;
        font-size: 1rem;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 20px rgba(211, 47, 47, 0.25);
        width: auto;
        min-width: 200px;
    }
    
    .stButton > button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(211, 47, 47, 0.35);
        background: linear-gradient(135deg, #B71C1C 0%, #D32F2F 100%);
    }
    
    .stButton > button:focus {
        box-shadow: 0 0 0 3px rgba(211, 47, 47, 0.2);
    }
    
    /* Container principal dos comentários */
    .comentarios-main-container {
        background: #F0F2F6;
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        border: 1px solid rgba(211, 47, 47, 0.1);
    }
    
    .comentarios-header {
        text-align: center;
        margin-bottom: 2rem;
        color: #000000;
    }
    
    .comentarios-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #D32F2F;
        margin-bottom: 0.5rem;
    }
    
    .comentarios-count {
        font-size: 1rem;
        color: #666666;
        font-weight: 500;
    }
    
    /* Estilo individual dos comentários */
    .comentario-card {
        background: #FFFFFF;
        padding: 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.06);
        border: 1px solid #E0E0E0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        border-left: 5px solid #D32F2F;
    }
    
    .comentario-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
        border-left-color: #B71C1C;
    }
    
    .comentario-header {
        display: flex;
        align-items: center;
        gap: 1rem;
        margin-bottom: 1.5rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid #F0F2F6;
    }
    
    .user-avatar {
        width: 50px;
        height: 50px;
        background: linear-gradient(135deg, #D32F2F, #B71C1C);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        font-size: 1.2rem;
        box-shadow: 0 4px 15px rgba(211, 47, 47, 0.3);
    }
    
    .comentario-autor-info {
        flex-grow: 1;
    }
    
    .comentario-autor-nome {
        color: #000000;
        font-weight: 700;
        font-size: 1.2rem;
        margin: 0;
        line-height: 1.2;
    }
    
    .comentario-data {
        color: #666666;
        font-size: 0.9rem;
        margin-top: 0.25rem;
        font-weight: 500;
    }
    
    .comentario-texto {
        color: #000000;
        line-height: 1.7;
        font-size: 1.05rem;
        margin: 0;
        font-weight: 400;
    }
    
    /* Formulário de novo comentário */
    .novo-comentario-container {
        background: #FFFFFF;
        padding: 2.5rem;
        border-radius: 20px;
        box-shadow: 0 6px 30px rgba(0, 0, 0, 0.08);
        border: 2px solid #F0F2F6;
        margin-bottom: 2rem;
    }
    
    .novo-comentario-header {
        text-align: center;
        margin-bottom: 2rem;
        color: #D32F2F;
        font-size: 1.6rem;
        font-weight: 700;
        position: relative;
    }
    
    .novo-comentario-header::after {
        content: '';
        position: absolute;
        bottom: -10px;
        left: 50%;
        transform: translateX(-50%);
        width: 60px;
        height: 4px;
        background: linear-gradient(90deg, #D32F2F, #B71C1C);
        border-radius: 2px;
    }
    
    /* Estilo do textarea */
    .stTextArea > div > div > textarea {
        border-radius: 12px !important;
        border: 2px solid #E0E0E0 !important;
        padding: 1.2rem !important;
        font-size: 1.05rem !important;
        line-height: 1.6 !important;
        resize: vertical !important;
        min-height: 140px !important;
        transition: all 0.3s ease !important;
        font-family: 'Inter', sans-serif !important;
        background: #FFFFFF !important;
    }
    
    .stTextArea > div > div > textarea:focus {
        border-color: #D32F2F !important;
        box-shadow: 0 0 0 3px rgba(211, 47, 47, 0.15) !important;
        outline: none !important;
    }
    
    /* Mensagem quando não há comentários */
    .no-comments {
        text-align: center;
        padding: 4rem 2rem;
        background: #FFFFFF;
        border-radius: 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
        border: 2px dashed #D32F2F;
    }
    
    .no-comments-icon {
        font-size: 4rem;
        color: #D32F2F;
        margin-bottom: 1.5rem;
        opacity: 0.7;
    }
    
    .no-comments-text {
        color: #666666;
        font-size: 1.2rem;
        font-weight: 500;
        line-height: 1.5;
    }
    
    /* Scroll customizado para comentários */
    .comentarios-scroll {
        max-height: 700px;
        overflow-y: auto;
        scrollbar-width: thin;
        scrollbar-color: #D32F2F #F0F2F6;
        padding-right: 10px;
    }
    
    .comentarios-scroll::-webkit-scrollbar {
        width: 8px;
    }
    
    .comentarios-scroll::-webkit-scrollbar-track {
        background: #F0F2F6;
        border-radius: 10px;
    }
    
    .comentarios-scroll::-webkit-scrollbar-thumb {
        background: #D32F2F;
        border-radius: 10px;
    }
    
    .comentarios-scroll::-webkit-scrollbar-thumb:hover {
        background: #B71C1C;
    }
    
    /* Animações */
    .fade-in {
        animation: fadeInUp 0.6s ease-out;
    }
    
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Rodapé informativo */
    .mpc-footer {
        text-align: center;
        color: #666666;
        font-size: 0.95rem;
        padding: 2rem;
        background: #F0F2F6;
        border-radius: 15px;
        margin-top: 2rem;
        border-top: 3px solid #D32F2F;
    }
    
    .mpc-footer strong {
        color: #D32F2F;
    }
    
    /* Responsividade */
    @media (max-width: 768px) {
        .mpc-header {
            padding: 2rem 1.5rem;
        }
        
        .mpc-header-title {
            font-size: 1.8rem;
        }
        
        .mpc-header-subtitle {
            font-size: 1.1rem;
        }
        
        .comentarios-main-container, 
        .novo-comentario-container {
            padding: 1.5rem;
        }
        
        .comentario-card {
            padding: 1.5rem;
        }
        
        .comentario-header {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.75rem;
        }
        
        .user-avatar {
            width: 45px;
            height: 45px;
            font-size: 1.1rem;
        }
        
        .comentario-autor-nome {
            font-size: 1.1rem;
        }
    }
    
    /* Estados especiais */
    .comentario-destaque {
        border-left-color: #D32F2F;
        border-left-width: 6px;
    }
    
    .comentario-recente {
        background: linear-gradient(135deg, #FFFFFF 0%, #FFF3F3 100%);
    }
</style>
""", unsafe_allow_html=True)



# Verificar se processo está selecionado
if 'processo_id' not in st.session_state:
    st.error("⚠️ Nenhum processo selecionado. Redirecionando...")
    st.switch_page("pages/Meus_Processos.py")
    st.stop()

processo_id = st.session_state['processo_id']
# Buscar processo pelo ID
processo_list = QueryBuilder("processos").eq("id", processo_id).select("*").execute()
processo = processo_list[0] if processo_list else None

if not processo:
    st.error("❌ Processo não encontrado.")
    st.switch_page("pages/Meus_Processos.py")
    st.stop()

# Header principal do sistema
st.markdown(f"""
<div class="mpc-header fade-in">
    <h1 class="mpc-header-title">💬 Sistema de Comentários</h1>
    <div class="mpc-header-subtitle">
        <strong>Processo:</strong> {processo.get('processo_numero')}
    </div>
</div>
""", unsafe_allow_html=True)

# Botão voltar
st.markdown('<div class="mpc-voltar-container">', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("⬅️ Voltar para Processos", key="voltar_btn"):
        if 'came_from' in st.session_state:
            st.switch_page(st.session_state['came_from'])
        else:
            st.switch_page("pages/Meus_Processos.py")
st.markdown('</div>', unsafe_allow_html=True)

# Buscar todos os comentários
comentarios = get_process_comments(processo_id)

# Marcar comentários como lidos (todos obtidos)
if comentarios:
    mark_comments_as_read(st.session_state.user_id, [c['id'] for c in comentarios])
    # db.commit() # Not needed with Supabase API calls

# Exibir comentários ou mensagem quando não houver
if not comentarios:
    st.markdown("""
    <div class="no-comments fade-in">
        <div class="no-comments-icon">💭</div>
        <div class="no-comments-text">
            Ainda não há comentários neste processo.<br>
            Seja o primeiro a compartilhar suas observações!
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown('<div class="comentarios-main-container fade-in">', unsafe_allow_html=True)
    
    # Header da seção de comentários
    st.markdown(f'''
    <div class="comentarios-header">
        <div class="comentarios-title">💬 Comentários do Processo</div>
        <div class="comentarios-count">{len(comentarios)} comentário(s) registrado(s)</div>
    </div>
    ''', unsafe_allow_html=True)
    
    # Container com scroll para comentários
    st.markdown('<div class="comentarios-scroll">', unsafe_allow_html=True)
    
    for i, comentario in enumerate(comentarios):
        cid = comentario['id']
        uid_autor = comentario['id_usuario']
        texto = comentario['texto']
        ts_str = comentario['timestamp']
        ts = datetime.fromisoformat(ts_str) if ts_str else datetime.now()
        
        autor = get_user_by_id(uid_autor)
        autor_nome = autor.get('nome_completo', 'Usuário Desconhecido') if autor else 'Usuário Desconhecido'
        
        # Criar iniciais para o avatar
        iniciais = ''.join([
            nome[0].upper() for nome in autor_nome.split()[:2]
        ])
        
        # Calcular tempo relativo
        agora = datetime.now() # naive
        # Supabase returns naive ISO usually (UTC) or with offset? 
        # Usually fromisoformat handles simple ISO. If ts is timezone aware, agora should be too.
        # Assuming database is storing UTC or local without timezone info, or Python client handles it.
        # But `datetime.now()` is local naive. `fromisoformat` without Z is naive.
        # If TS has Z, `fromisoformat` makes it aware.
        # Safe comparison:
        if ts.tzinfo is not None:
             agora = datetime.now(ts.tzinfo) # make 'agora' aware with same TZ
        
        diff = agora - ts
        
        if diff.days > 0:
            tempo_relativo = f"{diff.days} dia(s) atrás"
        elif diff.seconds > 3600:
            horas = diff.seconds // 3600
            tempo_relativo = f"{horas} hora(s) atrás"
        elif diff.seconds > 60:
            minutos = diff.seconds // 60
            tempo_relativo = f"{minutos} minuto(s) atrás"
        else:
            tempo_relativo = "Agora mesmo"
        
        # Verificar se é comentário recente (menos de 24h)
        classe_adicional = "comentario-recente" if diff.days == 0 and diff.seconds < 86400 else ""
        
        st.markdown(f"""
        <div class="comentario-card {classe_adicional}" style="animation-delay: {i * 0.1}s;">
            <div class="comentario-header">
                <div class="user-avatar">{iniciais}</div>
                <div class="comentario-autor-info">
                    <div class="comentario-autor-nome">{autor_nome}</div>
                    <div class="comentario-data">
                        📅 {ts.strftime('%d/%m/%Y às %H:%M')} • {tempo_relativo}
                    </div>
                </div>
            </div>
            <div class="comentario-texto">{texto}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)  # Fecha comentarios-scroll
    st.markdown('</div>', unsafe_allow_html=True)  # Fecha comentarios-main-container

# Formulário para novo comentário
st.markdown('<div class="novo-comentario-container fade-in">', unsafe_allow_html=True)
st.markdown('<div class="novo-comentario-header">✍️ Adicionar Novo Comentário</div>', unsafe_allow_html=True)

with st.form("new_comment_form", clear_on_submit=True):
    novo_comentario_texto = st.text_area(
        "Compartilhe suas observações sobre este processo:",
        placeholder="Digite seu comentário aqui...\n\nUse este espaço para:\n• Registrar informações importantes\n• Fazer observações técnicas\n• Comunicar atualizações\n• Esclarecer dúvidas",
        help="💡 **Dica:** Seja objetivo e claro em suas observações para facilitar a comunicação entre os membros da equipe.",
        key="comment_text"
    )
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        submit_comentario = st.form_submit_button("🚀 Publicar Comentário")

    if submit_comentario:
        if novo_comentario_texto and novo_comentario_texto.strip():
            try:
                # novo_comentario = Comentario(...)
                # db.add(novo_comentario)
                insert("comentarios", {
                    "id_processo": processo['id'],
                    "id_usuario": st.session_state.user_id,
                    "texto": novo_comentario_texto.strip()
                })
                # db.commit()
                
                st.success("✅ Comentário adicionado com sucesso!")
                st.balloons()
                
                # Delay para mostrar a mensagem antes do rerun
                import time
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Erro ao salvar comentário: {str(e)}")
                # db.rollback()
        else:
            st.warning("⚠️ Por favor, digite um comentário antes de publicar.")

st.markdown('</div>', unsafe_allow_html=True)  # Fecha novo-comentario-container

# Rodapé informativo institucional
ultimo_ts = comentarios[-1]['timestamp'] if comentarios else None
ultimo_data = datetime.fromisoformat(ultimo_ts) if ultimo_ts else datetime.now()

st.markdown(f"""
<div class="mpc-footer">
    <strong>Ministério Público de Contas de Santa Catarina</strong><br>
    Sistema de Comentários • Processo: <strong>{processo.get('processo_numero')}</strong><br>
    Total de comentários: <strong>{len(comentarios)}</strong> • 
    Última atualização: <strong>{ultimo_data.strftime('%d/%m/%Y às %H:%M')}</strong>
</div>
""", unsafe_allow_html=True)

# Cleanup do banco de dados
# Cleanup do banco de dados