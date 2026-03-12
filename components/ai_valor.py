import streamlit as st
from file_utils import process_uploaded_files

def render_valor_fiscalizado(client, MODEL_ID):
    st.markdown('<h1 class="main-title">🤖 AI para Cálculo de Valor Fiscalizado</h1>', unsafe_allow_html=True)

    st.markdown("""
    <div class="beta-alert fade-in">
        <h2>⚠️ PÁGINA EM FASE BETA E EXPERIMENTAL</h2>
        <p>Todos os valores calculados por esta página devem ser cuidadosamente confirmados por um servidor. A ferramenta utiliza um modelo de linguagem para auxiliar no cálculo, mas não substitui a análise humana detalhada. Utilize os resultados como uma primeira estimativa.</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

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
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🔍 Analisar e Calcular Valor", type="primary", use_container_width=True, key="btn_calcular_valor"):
                with st.spinner("🤖 Analisando os documentos e consultando a IA... Por favor, aguarde."):
                    processed_files = process_uploaded_files(uploaded_files)
                    if not processed_files:
                        st.error("❌ Não foi possível processar os arquivos. Tente novamente.")
                        return

                    full_content = ""
                    for file_info in processed_files:
                        full_content += f"--- INÍCIO DO DOCUMENTO: {file_info['name']} ---\n\n"
                        full_content += file_info['content']
                        full_content += f"\n\n--- FIM DO DOCUMENTO: {file_info['name']} ---\n\n"

                    instrucoes_adicionais_formatadas = ""
                    if additional_instructions:
                        instrucoes_adicionais_formatadas = f"""
**Instruções Adicionais do Usuário (devem ser seguidas com prioridade):**
---
{additional_instructions}
---
"""

                    prompt_text = f"""
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

                    try:
                        response = client.models.generate_content(
                            model=MODEL_ID,
                            contents=prompt_text
                        )
                        st.session_state.valor_ai_response = response.text
                        st.success("✅ Análise concluída com sucesso!")
                    except Exception as e:
                        error_message = str(e)
                        
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

    if st.session_state.get('valor_ai_response'):
        st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)
        st.markdown("""
        <div class="ai-result fade-in">
            <h3>🤖 Resultado da Análise da IA</h3>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(st.session_state.valor_ai_response)
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("🗑️ Limpar Resultado", key="clear_valor_result", use_container_width=True, help="Remove o resultado atual da análise"):
                st.session_state.valor_ai_response = None
                st.rerun()

    st.markdown('<hr class="custom-divider">', unsafe_allow_html=True)

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
