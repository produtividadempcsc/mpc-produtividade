import streamlit as st
import auth
from datetime import datetime, timezone
from utils.timezone import now_brazil, BRAZIL_TZ
from sidebar import build_sidebar
from supabase_client import QueryBuilder, insert
from db_compat import get_user_by_id, get_process_comments, mark_comments_as_read, create_notification

auth.auth_guard()

st.set_page_config(
    page_title="Comentários do Processo - MPC-SC",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)

build_sidebar()

# CSS personalizado seguindo o padrão do MPC-SC (Agora centralizado)
import ui_utils
ui_utils.load_css("style.css")
ui_utils.load_css("comentarios_style.css")



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
        ts = datetime.fromisoformat(ts_str) if ts_str else now_brazil()
        
        autor = get_user_by_id(uid_autor)
        autor_nome = autor.get('nome_completo', 'Usuário Desconhecido') if autor else 'Usuário Desconhecido'
        
        # Criar iniciais para o avatar
        iniciais = ''.join([
            nome[0].upper() for nome in autor_nome.split()[:2]
        ])
        
        # Calcular tempo relativo
        agora = now_brazil() # timezone-aware Brazil time
        # Garantir que ts é timezone-aware para subtração compatível
        if ts.tzinfo is None:
            # Supabase geralmente armazena em UTC; assumir UTC se naive
            ts = ts.replace(tzinfo=timezone.utc)
        
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
                
                # Notificar outros participantes do processo
                user_nome = st.session_state.get('user_nome', 'Usuário')
                p_num = processo.get('processo_numero', '')
                p_id = processo.get('id')
                current_user_id = st.session_state.user_id
                
                participantes = set()
                for campo in ['id_servidor_responsavel', 'id_chefe_gabinete', 'id_procurador']:
                    uid = processo.get(campo)
                    if uid and uid != current_user_id:
                        participantes.add(uid)
                
                for uid in participantes:
                    create_notification(
                        uid,
                        f"{user_nome} comentou no processo '{p_num}'.",
                        tipo="comentario",
                        id_processo=p_id
                    )
                
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
ultimo_data = datetime.fromisoformat(ultimo_ts) if ultimo_ts else now_brazil()

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