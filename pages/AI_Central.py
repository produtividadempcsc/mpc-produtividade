
import streamlit as st
import google.generativeai as genai
import auth
from sidebar import build_sidebar
from db_compat import get_user_by_id
import uuid
from file_utils import process_uploaded_files
from datetime import datetime
import ui_utils
from db_compat import get_all_prompts, get_prompt_by_id, create_prompt, update_prompt, delete_prompt, get_all_users
from supabase_client import QueryBuilder
from forms import display_edit_prompt_form

# --- Autenticação e Guard Clause ---
auth.auth_guard()

# =====================================================================
# GUARD CLAUSE DE PERFIL
# =====================================================================
allowed_profiles = ["Servidor", "Chefe de Gabinete", "Procurador", "Administrador"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Você não tem permissão para acessar esta página.")
    st.stop()
# =====================================================================

st.session_state.active_page = "AI Central"
build_sidebar()

# Carregar CSS global e específicos
ui_utils.load_css()
ui_utils.load_css("styles/chat.css")
ui_utils.load_css("styles/ai_valor.css")
ui_utils.load_css("styles/prompt_bank.css")

# --- Configuração do Gemini (Compartilhada) ---
try:
    genai.configure(api_key=auth.GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-3-flash-preview')
except Exception as e:
    st.error(f"Erro ao configurar a API do Gemini. Verifique a chave da API em auth.py. Erro: {e}")
    st.stop()

# --- Funções Auxiliares do Chat ---
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
    return len(text) // 4

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

# --- Renderização das Subs-páginas ---

def render_chat_interface():
    init_chat_session_state()
    
    show_chat_sidebar = st.session_state.show_sidebar
    
    if show_chat_sidebar:
        chat_col, main_col = st.columns([1, 3])
    else:
        main_col = st.container()
        chat_col = None

    # --- SIDEBAR DE CHATS ---
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
            
            # Configurações na sidebar do chat
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

    # --- ÁREA PRINCIPAL DO CHAT ---
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
            
            prompt_parts = [prompt]
            if processed_files:
                for p_file in processed_files:
                    if p_file["type"] in ["image", "audio", "video"]:
                        prompt_parts.append(p_file["content"])
                    else:
                        prompt_parts.append(f"\n\n--- CONTEÚDO DO ARQUIVO: {p_file['name']} ---\n\n{p_file['content']}")
            
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

                        enhanced_prompt = prompt
                        if instructions:
                            enhanced_prompt = f"INSTRUÇÕES: {' '.join(instructions)}\n\nPERGUNTA: {prompt}"
                        prompt_parts[0] = enhanced_prompt
                        
                        response = model.generate_content(prompt_parts, generation_config=genai.types.GenerationConfig(temperature=st.session_state.temperature, top_p=st.session_state.top_p))
                        response_text = response.text
                        st.markdown(response_text)
                        
                        update_token_count(enhanced_prompt, response_text)
                        messages.append({"role": "assistant", "content": response_text, "files": []})
                        
                        if len(messages) == 2:
                            try:
                                title_resp = model.generate_content(f"Crie um título curto (max 4 palavras) para: '{prompt}'", generation_config=genai.types.GenerationConfig(temperature=0.3))
                                current_chat["title"] = title_resp.text.strip().replace('"', '')[:40]
                                st.rerun()
                            except: pass
                    except Exception as e:
                        st.error(f"Erro: {e}")
                        if messages and messages[-1]["role"] == "user": messages.pop()

def render_valor_fiscalizado():
    # Título principal estilizado
    st.markdown('<h1 class="main-title">🤖 AI para Cálculo de Valor Fiscalizado</h1>', unsafe_allow_html=True)

    # Alerta Beta
    st.markdown("""
    <div class="beta-alert fade-in">
        <h2>⚠️ PÁGINA EM FASE BETA E EXPERIMENTAL</h2>
        <p>Todos os valores calculados por esta página devem ser cuidadosamente confirmados por um servidor. A ferramenta utiliza um modelo de linguagem para auxiliar no cálculo, mas não substitui a análise humana detalhada. Utilize os resultados como uma primeira estimativa.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Seção 1: Upload de Documento
    st.markdown("""
    <div class="section-card fade-in">
        <h2 class="section-header">📄 Envie os Documentos do Processo</h2>
        <div class="info-box">
            <p>Selecione um ou mais documentos do processo para análise conjunta pela IA. Formatos aceitos: PDF, DOCX, TXT, XLSX.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Selecione o(s) arquivo(s) do processo",
        type=['pdf', 'docx', 'txt', 'xlsx'],
        accept_multiple_files=True,
        help="Envie um ou mais documentos do processo para que a IA possa analisá-los em conjunto.",
        key="valor_uploader"
    )

    # Seção 2: Instruções Adicionais (Opcional)
    st.markdown("""
    <div class="section-card fade-in">
        <h2 class="section-header">🧠 Instruções Adicionais para a IA (Opcional)</h2>
        <div class="info-box">
            <p>Se desejar, forneça instruções ou um contexto extra para a IA. Por exemplo: "Considere apenas o valor do contrato principal, ignorando os aditivos" ou "O valor do dano está descrito no relatório de auditoria anexo".</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    additional_instructions = st.text_area(
        "Instruções Adicionais:",
        placeholder="Forneça aqui um contexto ou instrução específica para a análise...",
        height=150,
        key="valor_additional_instructions"
    )

    if uploaded_files:
        file_names = [f.name for f in uploaded_files]
        st.success(f"✅ {len(uploaded_files)} arquivo(s) carregado(s) com sucesso: {', '.join(file_names)}")
        
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        
        # Botões de análise
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔍 Analisar e Calcular Valor", type="primary", use_container_width=True, key="btn_calcular_valor"):
                with st.spinner("🤖 Analisando os documentos e consultando a IA... Por favor, aguarde."):
                    # 1. Processar os arquivos
                    processed_files = process_uploaded_files(uploaded_files)
                    if not processed_files:
                        st.error("❌ Não foi possível processar os arquivos. Tente novamente.")
                        return

                    # 2. Consolidar o conteúdo de todos os arquivos
                    full_content = ""
                    for file_info in processed_files:
                        full_content += f"--- INÍCIO DO DOCUMENTO: {file_info['name']} ---\n\n"
                        full_content += file_info['content']
                        full_content += f"\n\n--- FIM DO DOCUMENTO: {file_info['name']} ---\n\n"

                    # 3. Construir o Prompt
                    instrucoes_adicionais_formatadas = ""
                    if additional_instructions:
                        instrucoes_adicionais_formatadas = f"""
**Instruções Adicionais do Usuário (devem ser seguidas com prioridade):**
---
{additional_instructions}
---
"""

                    prompt = f"""
                    **Tarefa:** Você é um assistente especializado em análise de processos do Ministério Público de Contas de Santa Catarina. Sua função é calcular o "Volume de Recursos Fiscalizados" com base no conteúdo de um ou mais documentos de processo, nas regras fornecidas e em quaisquer instruções adicionais do usuário.

{instrucoes_adicionais_formatadas}
                    **Documentos do Processo (Conteúdo Consolidado):**
                    ---
                    {full_content}
                    ---

                    **Regras para Cálculo (Guia de Preenchimento):**
                    ---
                    1.  **Tomada de Contas Especial:** Valor do prejuízo ou danos em apuração.
                    2.  **Auditoria, Inspeção, Acompanhamento:** Soma dos valores pertinentes ao objetivo da análise.
                    3.  **Programa de Governo:** Total dos gastos e bens alusivos ao programa fiscalizado.
                    4.  **Atos de Pessoal (Aposentadorias, Pensões):** Valor total dos proventos (passados e futuros). Calcular usando a data de início do benefício e a expectativa de vida do IBGE (76 anos em 2024). Se o beneficiário já for mais velho que a expectativa, usar 13 meses. Fórmula: `Valor Mensal * (13 * (76 - Idade Atual))`
                    5.  **Atos de Pessoal (Admissões):** Soma das remunerações desde a admissão até a data do parecer. Fórmula: `Valor do Vencimento * Quantidade de Meses Trabalhados`.
                    6.  **Edital de Licitação:** Valor estimado no processo licitatório.
                    7.  **Contrato, Convênio, Acordo:** Valor total contratado/ajustado.
                    8.  **Denúncias e Procedimentos Apuratórios:** Valor estimado e justificado no processo. Se o objeto se encaixar em outra categoria, usar a regra específica.
                    9.  **Outros Assuntos:** Valor estimado e justificado no processo.
                    ---

                    **Sua Resposta Deve Conter:**
                    1.  **Tipo de Processo Identificado:** Qual das categorias acima o processo parece ser.
                    2.  **Valores Extraídos do Texto:** Liste os valores numéricos e as informações chave que você usou para o cálculo (ex: "Valor do contrato: R$ 1.200.000,00", "Idade do aposentado: 65 anos", "Início do benefício: 01/01/2020").
                    3.  **Raciocínio para o Cálculo:** Explique passo a passo como você chegou ao valor final, mencionando a regra aplicada.
                    4.  **Valor Final Calculado:** Apresente o resultado final de forma clara e destacada, no formato "R$ XXX.XXX,XX".

                    **Exemplo de Resposta:**
                    > **Tipo de Processo Identificado:** Contrato
                    > **Valores Extraídos do Texto:** O valor total do contrato é de R$ 1.200.000,00.
                    > **Raciocínio para o Cálculo:** O documento é um contrato, e a regra para "Contrato" diz para usar o valor total contratado.
                    > **Valor Final Calculado:** R$ 1.200.000,00

                    Analise o documento fornecido e retorne a resposta no formato especificado. Se não for possível determinar o valor ou o tipo de processo, informe claramente.
                    """

                    # 4. Chamar a IA
                    try:
                        response = model.generate_content(prompt)
                        st.session_state.valor_ai_response = response.text
                        st.success("✅ Análise concluída com sucesso!")
                    except Exception as e:
                        error_message = str(e)
                        
                        # Verifica se é o erro específico de cota excedida (código 429)
                        if "429" in error_message and "quota" in error_message.lower():
                            st.warning(
                                """
                                #### ⚠️ Limite de Análise Atingido
                                O documento que você enviou é muito grande e atingiu nosso limite de processamento momentâneo.

                                **O que fazer agora?**

                                1.  **Aguarde cerca de 1 minuto** e tente analisar o documento novamente.
                                2.  Se o erro persistir, tente uma das seguintes opções:
                                    *   **Use um arquivo menor:** Se possível, tente com um documento que tenha menos páginas.
                                    *   **Divida o documento:** Se for um PDF de muitas páginas, tente enviar apenas as seções mais relevantes para o cálculo.

                                Isso nos ajuda a manter a ferramenta disponível gratuitamente para todos. Agradecemos a sua compreensão!
                                """,
                                icon="⏳"
                            )
                        else:
                            st.error(f"❌ Ocorreu um erro inesperado ao contatar a IA: {e}")
                        
                        st.session_state.valor_ai_response = None

    # Exibir a resposta da IA se existir
    if st.session_state.get('valor_ai_response'):
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        st.markdown("""
        <div class="ai-result fade-in">
            <h3>🤖 Resultado da Análise da IA</h3>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.valor_ai_response)
        
        # Botão para limpar resultado
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🗑️ Limpar Resultado", key="clear_valor_result", use_container_width=True, help="Remove o resultado atual da análise"):
                st.session_state.valor_ai_response = None
                st.rerun()

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

    # Seção: Instruções e Conceitos
    st.markdown("""
    <div class="section-card fade-in">
        <h2 class="section-header">📋 Instruções e Conceitos</h2>
        <div class="info-box">
            <p>Esta página utiliza um modelo de Inteligência Artificial para extrair e calcular o <strong>Volume de Recursos Fiscalizados</strong> a partir de um documento de processo. Abaixo estão as regras e conceitos que a IA utiliza, baseadas no "Guia de Preenchimento do Campo 'Valor'".</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📖 Ver Guia de Preenchimento do Campo 'Valor'"):
        st.markdown("""
        ### Guia de Preenchimento do Campo "Valor"
        **Base de dados – Número Unificado**

        #### INTRODUÇÃO 
        Em tempos de reforma administrativa e fiscal, a sociedade brasileira se questiona sobre a necessidade e importância de diversas entidades públicas. A atuação pública é, assim, alvo de indagações quanto ao papel do Estado e exige soluções para as demandas sociais.
        
        Para apresentar à sociedade a atuação dos órgãos públicos, considerando a evolução tecnológica, os mecanismos de transparência pública passaram a ser mais que uma regra: tornaram-se um dever.

        #### 1. Valoração do Volume de Recursos Fiscalizados
        O preenchimento do campo "Valor" refere-se à identificação da valoração do volume de Recursos Fiscalizados, que corresponde ao total dos valores envolvidos no processo ou procedimento tramitado no MPC/SC.

        | Objeto de Processo / Procedimento | Como calcular o Volume de Recursos Fiscalizados |
        | --- | --- |
        | Tomada de Contas Especial | Valor do prejuízo ou danos em apuração |
        | Auditoria, Inspeção, Acompanhamento | Soma dos valores pertinentes ao objetivo da análise |
        | Programa de Governo | Total dos gastos e bens alusivos ao programa fiscalizado |
        | Atos de Registro de Pessoal: Aposentadorias, Reservas e Pensões | Valor Mensal × (13 × (76 - Idade Atual)) |
        | Atos de Registro de Pessoal: Admissões | Valor do Vencimento × Quantidade de Meses Trabalhados |
        | Edital de Licitação | Valor estimado constante do processo licitatório |
        | Contrato, Convênio, Acordo e Instrumentos Congêneres | Total correspondente à importância contratada/acordada |
        | Denúncias e Procedimentos Apuratórios | Valor estimado, identificado e justificado no processo |
        | Outros Assuntos | Valor estimado, identificado e justificado no processo |

        #### 2. Valoração dos Benefícios Quantitativos Não Financeiros
        Podem ocorrer processos em que não seja possível mensurar um benefício financeiro de forma numérica. Nesse contexto, o campo "Valor" deverá ser deixado em branco.

        #### 3. Exemplos Práticos
        
        **3.1. Restituição de recursos a órgão ou entidade:** 
        O benefício é o valor total do convênio ou contrato fiscalizado.
        
        **3.2. Interrupção do pagamento de vantagem indevida:**
        Para benefício recorrente/mensal: total que deixará de ser pago em 13 meses.
        
        **3.3. Aposentadoria, reserva, reforma, pensão:**
        Fórmula: `Valor da Aposentadoria Mensal × (13 × (76 - Idade Atual))`
        
        *Exemplo:* Aposentado de 65 anos, recebendo R$ 5.000,00 mensais:
        - Volume = R$ 5.000,00 × (13 × 11) = R$ 5.000,00 × 143 = **R$ 715.000,00**
        
        **3.4. Impugnação de despesas:** 
        O Volume de Recursos Fiscalizados é o valor da despesa glosada ou impugnada.
        """)

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

# --- Main Page Layout ---
st.title("🧠 Central de Inteligência Artificial")

tabs = st.tabs(["🤖 Chat Inteligente", "💰 Cálculo de Valor", "📚 Banco de Prompts"])

with tabs[0]:
    render_chat_interface()

with tabs[1]:
    render_valor_fiscalizado()

with tabs[2]:
    render_prompt_bank()
