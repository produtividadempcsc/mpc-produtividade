import streamlit as st
from db_compat import get_all_prompts, create_prompt, get_all_users
from forms import display_edit_prompt_form

def render_prompt_bank():
    st.markdown("## 📚 Banco de Prompts")
    
    # Roteador Modal de Edição
    if 'prompt_para_editar_id' in st.session_state:
        display_edit_prompt_form(st.session_state['prompt_para_editar_id'])
        if st.button("Voltar para Lista"):
            del st.session_state['prompt_para_editar_id']
            st.rerun()
        return

    # Links Rápidos
    with st.expander("🔗 Links de IAs"):
        cols = st.columns(4)
        cols[0].link_button("ChatGPT", "https://chat.openai.com/")
        cols[1].link_button("Gemini", "https://gemini.google.com/")
        cols[2].link_button("Claude", "https://claude.ai/")
        cols[3].link_button("Copilot", "https://copilot.microsoft.com/")

    # Novo Prompt
    with st.expander("➕ Adicionar Prompt"):
        with st.form("new_prompt"):
            titulo = st.text_input("Título")
            conteudo = st.text_area("Conteúdo")
            publico = st.checkbox("Público?")
            if st.form_submit_button("Salvar") and titulo and conteudo:
                create_prompt({
                    "titulo": titulo, 
                    "conteudo": conteudo, 
                    "id_criador": st.session_state.user_id, 
                    "e_publico": publico
                })
                st.success("Salvo!")
                st.rerun()

    # Filtros
    c1, c2, c3 = st.columns([3, 1, 1])
    search = c1.text_input("Buscar", placeholder="Título ou conteúdo...")
    vis_filter = c2.selectbox("Visibilidade", ["Todos", "Públicos", "Privados"])
    creator_filter = c3.selectbox("Criador", ["Todos", "Meus"])

    # Listagem
    with st.spinner("Carregando prompts..."):
        prompts = get_all_prompts(st.session_state.user_id, include_public=True)
        
        if search:
            prompts = [p for p in prompts if search.lower() in p['titulo'].lower() or search.lower() in p['conteudo'].lower()]
        if vis_filter == "Públicos": prompts = [p for p in prompts if p['e_publico']]
        if vis_filter == "Privados": prompts = [p for p in prompts if not p['e_publico']]
        if creator_filter == "Meus": prompts = [p for p in prompts if p['id_criador'] == st.session_state.user_id]

    users = {u['id']: u['nome_completo'] for u in get_all_users()}

    for p in prompts:
        container = st.container(border=True)
        with container:
            pc1, pc2 = st.columns([5, 1])
            pc1.subheader(f"📌 {p['titulo']}")
            with pc2:
                if p['id_criador'] == st.session_state.user_id:
                    if st.button("✏️", key=f"ed_{p['id']}"):
                        st.session_state['prompt_para_editar_id'] = p['id']
                        st.rerun()
            
            st.code(p['conteudo'], language="mb")
            
            meta = f"👤 {users.get(p['id_criador'], 'Desconhecido')} | {'🌐 Público' if p['e_publico'] else '🔒 Privado'}"
            st.caption(meta)
