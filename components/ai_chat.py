import streamlit as st
import uuid
from datetime import datetime
from google.genai import types
from file_utils import process_uploaded_files

def init_chat_session_state():
    if "chats" not in st.session_state:
        first_chat_id = str(uuid.uuid4())
        st.session_state.chats = {
            first_chat_id: {
                "title": "Nova Conversa",
                "messages": [],
                "created_at": datetime.now(),
                "total_tokens": 0
            }
        }
        st.session_state.active_chat_id = first_chat_id
    
    if "temperature" not in st.session_state:
        st.session_state.temperature = 1.0
    if "top_p" not in st.session_state:
        st.session_state.top_p = 0.95
    if "show_sidebar" not in st.session_state:
        st.session_state.show_sidebar = True
    if "deep_thinking" not in st.session_state:
        st.session_state.deep_thinking = False
    if "response_length" not in st.session_state:
        st.session_state.response_length = "Médio"

def create_new_chat():
    chat_id = str(uuid.uuid4())
    st.session_state.chats[chat_id] = {
        "title": "Nova Conversa",
        "messages": [],
        "created_at": datetime.now(),
        "total_tokens": 0
    }
    st.session_state.active_chat_id = chat_id
    st.rerun()

def delete_chat(chat_id):
    if len(st.session_state.chats) > 1:
        del st.session_state.chats[chat_id]
        if st.session_state.active_chat_id == chat_id:
            st.session_state.active_chat_id = list(st.session_state.chats.keys())[0]
        st.rerun()

def switch_chat(chat_id):
    if st.session_state.active_chat_id != chat_id:
        st.session_state.active_chat_id = chat_id
        st.rerun()

def rename_chat(chat_id, new_title):
    if new_title.strip():
        st.session_state.chats[chat_id]["title"] = new_title.strip()
        st.rerun()

def estimate_tokens(text):
    if not text: return 0
    return len(str(text)) // 4

def update_token_count(prompt, response):
    prompt_tokens = estimate_tokens(prompt)
    response_tokens = estimate_tokens(response)
    active_chat_id = st.session_state.active_chat_id
    if 'total_tokens' not in st.session_state.chats[active_chat_id]:
        st.session_state.chats[active_chat_id]['total_tokens'] = 0
    st.session_state.chats[active_chat_id]['total_tokens'] += prompt_tokens + response_tokens

def format_token_count(count):
    if count >= 1000000:
        return f"{count/1000000:.1f}M"
    elif count >= 1000:
        return f"{count/1000:.1f}K"
    else:
        return str(count)

def get_response_length_instruction(length):
    instructions = {
        "Curto": "Seja conciso e direto ao ponto. Responda em no máximo 2-3 parágrafos.",
        "Médio": "Forneça uma resposta equilibrada com detalhes adequados.",
        "Longo": "Forneça uma resposta detalhada e abrangente com explicações completas.",
        "Muito Longo": "Seja extremamente detalhado, incluindo exemplos, contexto e explicações profundas."
    }
    return instructions.get(length, "")

def truncate_text(text, max_length=30):
    return text[:max_length] + "..." if len(text) > max_length else text

def render_chat_interface(client, MODEL_ID):
    init_chat_session_state()
    
    show_chat_sidebar = st.session_state.show_sidebar
    
    if show_chat_sidebar:
        chat_col, main_col = st.columns([1, 3])
    else:
        main_col = st.container()
        chat_col = None

    if show_chat_sidebar and chat_col:
        with chat_col:
            st.markdown("### 💬 Histórico")
            if st.button("➕ Nova Conversa", use_container_width=True, type="primary"):
                create_new_chat()
            
            st.markdown("---")
            
            for chat_id, chat_data in st.session_state.chats.items():
                is_active = chat_id == st.session_state.active_chat_id
                
                chat_container = st.container()
                with chat_container:
                    col1, col2, col3 = st.columns([3, 0.5, 0.5])
                    with col1:
                        button_type = "primary" if is_active else "secondary"
                        if st.button(truncate_text(chat_data["title"]), key=f"chat_{chat_id}", use_container_width=True, type=button_type):
                            switch_chat(chat_id)
                    with col2:
                        if st.button("✏️", key=f"rename_{chat_id}", help="Renomear"):
                            st.session_state[f"renaming_{chat_id}"] = True
                            st.rerun()
                    with col3:
                        if len(st.session_state.chats) > 1:
                            if st.button("🗑️", key=f"del_{chat_id}", help="Deletar"):
                                delete_chat(chat_id)
                    
                    if st.session_state.get(f"renaming_{chat_id}", False):
                        new_title = st.text_input("Novo nome:", value=chat_data["title"], key=f"rename_input_{chat_id}")
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.button("✅", key=f"save_{chat_id}"):
                                rename_chat(chat_id, new_title)
                                st.session_state[f"renaming_{chat_id}"] = False
                                st.rerun()
                        with col_cancel:
                            if st.button("❌", key=f"cancel_{chat_id}"):
                                st.session_state[f"renaming_{chat_id}"] = False
                                st.rerun()
            
            st.markdown("---")
            
            st.markdown("### ⚙️ Ajustes")
            
            active_chat = st.session_state.chats[st.session_state.active_chat_id]
            chat_tokens = active_chat.get("total_tokens", 0)
            token_color = "🔴" if chat_tokens > 800000 else "🟡" if chat_tokens > 500000 else "🟢"
            st.markdown(f"**{token_color} Tokens: {format_token_count(chat_tokens)} / 1M**")
            if st.button("🔄 Reset Tokens", key="reset_tokens"):
                st.session_state.chats[st.session_state.active_chat_id]["total_tokens"] = 0
                st.rerun()

            st.session_state.temperature = st.slider("Criatividade", 0.0, 2.0, st.session_state.temperature, 0.1)
            st.session_state.response_length = st.selectbox("Tamanho", ["Curto", "Médio", "Longo", "Muito Longo"], index=["Curto", "Médio", "Longo", "Muito Longo"].index(st.session_state.response_length))
            st.session_state.deep_thinking = st.checkbox("Pensamento Profundo", value=st.session_state.deep_thinking)
            
            with st.expander("Avançado"):
                st.session_state.personality = st.selectbox("Personalidade", ["Profissional", "Casual", "Acadêmico", "Criativo", "Técnico"], index=0)
                st.session_state.use_emojis = st.checkbox("Emojis", value=False)
                st.session_state.include_sources = st.checkbox("Citar Fontes", value=False)
            
            if st.button("👁️ Ocultar Lateral", use_container_width=True):
                st.session_state.show_sidebar = False
                st.rerun()

    with main_col:
        current_chat = st.session_state.chats[st.session_state.active_chat_id]
        
        header_col1, header_col2 = st.columns([4, 1])
        with header_col1:
            st.title("🤖 " + current_chat["title"])
        with header_col2:
            if not show_chat_sidebar:
                if st.button("💬 Menu", type="secondary"):
                    st.session_state.show_sidebar = True
                    st.rerun()
        
        messages = current_chat["messages"]
        if not messages:
            st.info("👋 Olá! Como posso ajudar você hoje?")
        else:
            for message in messages:
                with st.chat_message(message["role"]):
                    if "files" in message and message["files"]:
                        with st.expander(f"📎 {len(message['files'])} arquivo(s)"):
                            for file_name in message["files"]: st.caption(f"• {file_name}")
                    st.markdown(message["content"])
        
        uploaded_files = st.file_uploader("Anexar arquivos", type=['txt','pdf','docx','xlsx','png','jpg'], accept_multiple_files=True, key=f"uploader_{st.session_state.active_chat_id}", label_visibility="collapsed")
        
        if prompt := st.chat_input("Digite sua mensagem..."):
            processed_files = process_uploaded_files(uploaded_files) if uploaded_files else []
            attached_file_names = [f["name"] for f in processed_files]
            
            contents = []
            
            if processed_files:
                for p_file in processed_files:
                    if p_file["type"] in ["image", "audio", "video"]:
                         if isinstance(p_file["content"], str):
                            contents.append(types.Part.from_text(text=f"\n\n--- CONTEÚDO DO ARQUIVO: {p_file['name']} ---\n\n{p_file['content']}"))
                         else:
                             contents.append(p_file["content"])
                    else:
                        contents.append(types.Part.from_text(text=f"\n\n--- CONTEÚDO DO ARQUIVO: {p_file['name']} ---\n\n{p_file['content']}"))

            
            messages.append({"role": "user", "content": prompt, "files": attached_file_names})
            
            with st.chat_message("user"):
                if attached_file_names:
                    with st.expander(f"📎 {len(attached_file_names)} arquivo(s)"):
                        for file_name in attached_file_names: st.caption(f"• {file_name}")
                st.markdown(prompt)
            
            with st.chat_message("assistant"):
                with st.spinner("Pensando..."):
                    try:
                        active_chat = st.session_state.chats[st.session_state.active_chat_id]
                        if active_chat.get("total_tokens", 0) >= 1000000:
                            st.error("🚫 Limite de tokens atingido!")
                            st.stop()
                        
                        instructions = []
                        if st.session_state.deep_thinking: instructions.append("Analise profundamente.")
                        instructions.append(get_response_length_instruction(st.session_state.response_length))
                        
                        personality = st.session_state.get('personality', 'Profissional')
                        instructions.append(f"Tom: {personality}.")
                        if st.session_state.get('use_emojis'): instructions.append("Use emojis.")
                        if st.session_state.get('include_sources'): instructions.append("Cite fontes tipo de conhecimento.")

                        enhanced_prompt_text = prompt
                        if instructions:
                            enhanced_prompt_text = f"INSTRUÇÕES: {' '.join(instructions)}\n\nPERGUNTA: {prompt}"
                        
                        contents.append(types.Part.from_text(text=enhanced_prompt_text))
                        
                        config = types.GenerateContentConfig(
                            temperature=st.session_state.temperature,
                            top_p=st.session_state.top_p
                        )
                        
                        response = client.models.generate_content(
                            model=MODEL_ID,
                            contents=contents,
                            config=config
                        )
                        
                        response_text = response.text
                        st.markdown(response_text)
                        
                        update_token_count(enhanced_prompt_text, response_text)
                        messages.append({"role": "assistant", "content": response_text, "files": []})
                        
                        if len(messages) == 2:
                            try:
                                title_resp = client.models.generate_content(
                                    model=MODEL_ID,
                                    contents=f"Crie um título curto (max 4 palavras) para: '{prompt}'",
                                    config=types.GenerateContentConfig(temperature=0.3)
                                )
                                current_chat["title"] = title_resp.text.strip().replace('"', '')[:40]
                                st.rerun()
                            except Exception as e:
                                print(f"Erro AI Chat: {e}")
                    except Exception as e:
                        st.error(f"Erro: {e}")
                        if messages and messages[-1]["role"] == "user": messages.pop()
