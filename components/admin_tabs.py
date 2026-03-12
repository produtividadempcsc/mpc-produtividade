import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from db_compat import (
    get_all_product_types, get_product_type_by_id, get_product_type_by_name,
    create_product_type, update_product_type, delete_product_type, get_latest_product_versions,
    get_config, set_config, get_all_users
)
from utils.common import generate_nome_id
from repositories.calendar_repository import get_holidays_only, upsert_calendar_entry
import utils
import backup
from utils.jobs import initialize_restored_data
import os
import relatorios
import reports_corregedoria
from supabase_client import supabase

def render_tab_produtos():
    """Renderiza a aba de Gestão de Tipos de Produto."""
    st.subheader("🎯 Gestão de Tipos de Produto e Prazos")
    
    try:
        with st.spinner("Carregando tipos de produto..."):
            all_products = get_all_product_types()
        if all_products:
            df_prods = pd.DataFrame([{
                "ID": p.get('id'), 
                "Nome": p.get('nome_produto'), 
                "Prazo Servidor": p.get('prazo_servidor'), 
                "Prazo Chefe": p.get('prazo_chefe'), 
                "Contagem": p.get('tipo_contagem_prazo'), 
                "Data de Validade": datetime.fromisoformat(p.get('data_validade')).strftime('%d/%m/%Y') if p.get('data_validade') else 'N/A', 
                "Versão": p.get('versao')
            } for p in all_products])
            st.dataframe(df_prods, use_container_width=True)
        else: 
            st.info("📝 Nenhum produto cadastrado.")
    except Exception as e: 
        st.error(f"❌ Erro ao carregar produtos: {e}")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.expander("➕ Adicionar Produto", expanded=True):
            with st.form("add_prod", clear_on_submit=True):
                nome = st.text_input("📝 Nome do Produto", key="prod_nome_add")
                p_serv = st.number_input("⏱️ Prazo Servidor (dias)", min_value=1, step=1)
                p_chefe = st.number_input("👔 Prazo Chefe (dias)", min_value=1, step=1)
                t_cont = st.selectbox("📊 Tipo de Contagem", ["dias uteis", "dias corridos"])
                descricao = st.text_area("📋 Descrição / Instruções (Markdown)")
                data_criacao = st.date_input("📅 Data de Criação", value=date.today(), min_value=date(2000, 1, 1), max_value=date(2099, 12, 31), format="DD/MM/YYYY")
                data_validade = st.date_input("⏰ Data de Validade", value=date.today(), min_value=date(2000, 1, 1), max_value=date(2099, 12, 31), format="DD/MM/YYYY")
                
                submitted = st.form_submit_button("✅ Cadastrar Produto")
                
                if submitted and nome:
                    existing = get_product_type_by_name(nome)
                    if existing: 
                        st.error(f"❌ Produto '{nome}' já existe.")
                    else:
                        nome_id = generate_nome_id(nome)
                        novo_produto_data = {
                            "nome_id": nome_id, 
                            "nome_produto": nome,
                            "prazo_servidor": p_serv,
                            "prazo_chefe": p_chefe,
                            "tipo_contagem_prazo": t_cont, 
                            "data_criacao": data_criacao.isoformat(), 
                            "data_validade": data_validade.isoformat(),
                            "descricao": descricao,
                            "versao": 1
                        }
                        
                        result = create_product_type(novo_produto_data)
                        
                        st.success("✅ Produto cadastrado com sucesso!")
                        st.rerun()

    with col2:
        with st.expander("✏️ Editar/Deletar", expanded=True):
            all_prods = get_all_product_types()
            prod_dict = {f"{p.get('nome_produto')} (v{p.get('versao')})": p.get('id') for p in all_prods}
            
            if not prod_dict:
                st.info("📝 Nenhum produto para gerenciar.")
            else:
                sel_prod_name = st.selectbox("🔍 Selecione o Produto", options=list(prod_dict.keys()), key="prod_edit_select")
                
                if sel_prod_name:
                    prod_to_edit = get_product_type_by_id(prod_dict[sel_prod_name])
                    
                    if prod_to_edit:
                        with st.form("edit_prod_form"):
                            n_nome = st.text_input("📝 Nome", value=prod_to_edit.get('nome_produto'))
                            n_p_serv = st.number_input("⏱️ Prazo Servidor", min_value=1, step=1, value=prod_to_edit.get('prazo_servidor', 1))
                            n_p_chefe = st.number_input("👔 Prazo Chefe", min_value=1, step=1, value=prod_to_edit.get('prazo_chefe', 1))
                            n_t_cont = st.selectbox("📊 Contagem", ["dias uteis", "dias corridos"], 
                                                  index=["dias uteis", "dias corridos"].index(prod_to_edit.get('tipo_contagem_prazo', 'dias uteis')))
                            n_descricao = st.text_area("📋 Descrição", value=prod_to_edit.get('descricao') or "")
                            
                            current_validade = prod_to_edit.get('data_validade')
                            if isinstance(current_validade, str):
                                current_validade = datetime.fromisoformat(current_validade).date()
                            n_data_validade = st.date_input("⏰ Data de Validade", value=current_validade or date.today(), min_value=date(2000, 1, 1), max_value=date(2099, 12, 31), format="DD/MM/YYYY")
                            
                            st.markdown("---")
                                            
                            upd = st.form_submit_button("💾 Salvar Alterações")
                            
                            if upd:
                                update_data = {
                                    "nome_produto": n_nome,
                                    "prazo_servidor": n_p_serv,
                                    "prazo_chefe": n_p_chefe,
                                    "tipo_contagem_prazo": n_t_cont,
                                    "descricao": n_descricao,
                                    "data_validade": n_data_validade.isoformat()
                                }
                                
                                update_product_type(prod_to_edit.get('id'), update_data)
                                st.success("✅ Produto atualizado!")
                                st.rerun()

                        st.markdown("---")
                        
                        st.warning("⚠️ Zona de Perigo")
                        confirm_delete_prod = st.checkbox("🗑️ Confirmo que desejo deletar este produto", 
                                                        key=f"del_prod_{prod_to_edit.get('id')}")
                        
                        if st.button("🗑️ Deletar Produto", disabled=(not confirm_delete_prod)):
                            delete_product_type(prod_to_edit.get('id'))
                            st.success("✅ Produto deletado!")
                            st.rerun()

    with col3:
        with st.expander("📝 Alterar Prazo", expanded=True):
            produtos_mais_recentes = get_latest_product_versions()
            produto_nomes = [p.get('nome_produto') for p in produtos_mais_recentes]
            
            if not produto_nomes:
                st.warning("⚠️ Nenhum tipo de produto cadastrado para alterar.")
            else:
                produto_selecionado_nome = st.selectbox(
                    "🔍 Selecione o Tipo de Produto", 
                    options=sorted(produto_nomes)
                )
                
                # Buscar versão mais recente do produto selecionado
                produto_selecionado = None
                for p in produtos_mais_recentes:
                    if p.get('nome_produto') == produto_selecionado_nome:
                        produto_selecionado = p
                        break

                with st.form("alterar_prazo_form", clear_on_submit=True):
                    if produto_selecionado:
                        st.text_input("⏱️ Prazo Servidor Atual", 
                                    value=f"{produto_selecionado.get('prazo_servidor')} dias", disabled=True)
                        st.text_input("👔 Prazo Chefe Atual", 
                                    value=f"{produto_selecionado.get('prazo_chefe')} dias", disabled=True)
                        st.text_input("📊 Forma de Contagem Atual", 
                                    value=produto_selecionado.get('tipo_contagem_prazo', '').title(), disabled=True)
                        
                        st.markdown("---")
                        
                        novo_prazo = st.number_input("🆕 Novo Prazo Servidor (dias)", 
                                                   min_value=1, step=1, value=produto_selecionado.get('prazo_servidor', 1))
                        novo_prazo_chefe = st.number_input("🆕 Novo Prazo Chefe (dias)", 
                                                         min_value=1, step=1, value=produto_selecionado.get('prazo_chefe', 1))
                        nova_contagem = st.selectbox("🆕 Nova Forma de Contagem", 
                                                   ["dias uteis", "dias corridos"], 
                                                   index=["dias uteis", "dias corridos"].index(produto_selecionado.get('tipo_contagem_prazo', 'dias uteis')))
                        nova_vigencia = st.date_input("📅 Vigência do Novo Prazo", value=date.today(), min_value=date(2000, 1, 1), max_value=date(2099, 12, 31), format="DD/MM/YYYY")
                    
                    submitted = st.form_submit_button("💾 Salvar Alteração")
                    
                    if submitted and produto_selecionado:
                        # Atualizar data_validade do produto original para um dia antes da nova vigência
                        validade_final_original = produto_selecionado.get('data_validade')
                        update_product_type(produto_selecionado.get('id'), {
                            "data_validade": (nova_vigencia - timedelta(days=1)).isoformat()
                        })
                        
                        # Criar nova versão
                        nova_versao_data = {
                            "nome_id": produto_selecionado.get('nome_id'),
                            "nome_produto": produto_selecionado.get('nome_produto'),
                            "prazo_servidor": novo_prazo,
                            "prazo_chefe": novo_prazo_chefe,
                            "tipo_contagem_prazo": nova_contagem,
                            "data_criacao": datetime.now().isoformat(),
                            "data_validade": validade_final_original,
                            "versao": produto_selecionado.get('versao', 1) + 1
                        }
                        create_product_type(nova_versao_data)
                        
                        st.success("✅ Alteração de prazo salva! Nova versão criada.")
                        st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_tab_feriados():
    """Renderiza a aba de Gestão do Calendário (Feriados)."""
    st.subheader("📅 Gestão do Calendário (Feriados e Pontos Facultativos)")

    try:
        with st.spinner("Carregando calendário..."):
            feriados = get_holidays_only()

        if feriados:
            df_feriados = pd.DataFrame([{
                "📅 Data": datetime.fromisoformat(f.get('data')).strftime('%d/%m/%Y') if f.get('data') else 'N/A', 
                "🎉 Descrição": f.get('dia_semana'),
                "_data_iso": f.get('data')  # Para usar na remoção
            } for f in feriados])
            st.dataframe(df_feriados[["📅 Data", "🎉 Descrição"]], use_container_width=True, hide_index=True)
        else:
            st.info("📝 Nenhum feriado ou ponto facultativo cadastrado.")
    
    except Exception as e:
        st.error(f"❌ Erro ao carregar feriados: {e}")
        feriados = []

    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.expander("➕ Adicionar Feriado", expanded=True):
            with st.form("add_holiday", clear_on_submit=True):
                data_feriado = st.date_input("📅 Selecione a Data do Feriado", min_value=date(2000, 1, 1), max_value=date(2099, 12, 31), format="DD/MM/YYYY")
                descricao = st.text_input("🎉 Descrição (Ex: Corpus Christi)")
                
                submitted = st.form_submit_button("✅ Adicionar Feriado")
                
                if submitted and descricao:
                    upsert_calendar_entry(data_feriado, descricao, False)
                    st.success(f"✅ Feriado '{descricao}' adicionado em {data_feriado.strftime('%d/%m/%Y')}.")
                    st.rerun()

    with col2:
        with st.expander("🗑️ Remover Feriado", expanded=True):
            if feriados:
                feriados_list = {
                    f"{datetime.fromisoformat(f.get('data')).strftime('%d/%m/%Y')} - {f.get('dia_semana')}": f.get('data') 
                    for f in feriados
                }
                sel_feriado = st.selectbox("🔍 Selecione um feriado para remover", 
                                         options=list(feriados_list.keys()), key="holiday_remove_select")
            
                if st.button("🔄 Reverter para Dia Útil"):
                    data_para_reverter = feriados_list[sel_feriado]
                    data_obj = datetime.fromisoformat(data_para_reverter).date()
                    
                    # Atualizar para dia útil com nome do dia da semana
                    dia_semana = data_obj.strftime('%A')
                    upsert_calendar_entry(data_obj, dia_semana, True)
                
                    st.success(f"✅ O dia {data_obj.strftime('%d/%m/%Y')} foi restaurado como dia útil.")
                    st.rerun()
            else:
                st.info("📝 Nenhum feriado para remover.")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_tab_afastamentos():
    """Renderiza a aba de Lançamento de Afastamento Global."""
    st.subheader("🌴 Lançar Afastamento Coletivo para Todos os Usuários")

    with st.form("global_recess_form", clear_on_submit=True):
        st.error("🚨 **Atenção:** Esta ação adicionará um período de afastamento para **TODOS** os usuários do sistema. Use com cuidado.")
        
        descricao = st.text_input("📋 Descrição do Afastamento", 
                                placeholder="Ex: Recesso de Final de Ano")
        
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("📅 Data de Início", key="global_recess_start_date", min_value=date(2000, 1, 1), max_value=date(2099, 12, 31), format="DD/MM/YYYY")
        with col2:
            data_fim = st.date_input("📅 Data de Fim", key="global_recess_end_date", min_value=date(2000, 1, 1), max_value=date(2099, 12, 31), format="DD/MM/YYYY")

        submitted = st.form_submit_button("🌴 Lançar Afastamento para Todos")

        if submitted:
            if not descricao:
                st.error("❌ O campo 'Descrição' é obrigatório.")
            elif data_inicio > data_fim:
                st.error("❌ A data de início não pode ser posterior à data de fim.")
            else:
                with st.spinner("Processando solicitação global..."):
                    resultado = utils.adicionar_recesso_para_todos_usuarios(
                        descricao=descricao,
                        data_inicio=data_inicio,
                        data_fim=data_fim
                    )
                
                if resultado["sucesso"]:
                    st.success(resultado["mensagem"])
                    if "detalhes" in resultado and resultado["detalhes"]["avisos"] > 0:
                        with st.expander(f"👀 Ver detalhes dos {resultado['detalhes']['avisos']} usuários que já possuíam este recesso"):
                            st.json(resultado['detalhes']['usuarios_com_aviso'])
                else:
                    st.error(f"❌ Falha ao adicionar recesso: {resultado['mensagem']}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_tab_backup():
    """Renderiza a aba de Gerenciamento de Backup."""
    st.subheader("💾 Gerenciamento de Backup")

    st.info("✅ O sistema de backup automático está ativo e integrado ao banco de dados em nuvem.")
    
    # Seção para Configuração do Backup Automático
    with st.container(border=True):
        st.markdown("**⚙️ Configuração do Backup Automático**")
        try:
            current_freq = get_config('backup_frequencia') or "Diário"
        except Exception as e:
            print(f"⚠️ Erro silencioso em Administracao.py (Configurar Backup): {e}")
            set_config('backup_frequencia', 'Diário')
            current_freq = "Diário"
    
        options = ["Desativado", "Diário", "Semanal"]
        new_freq = st.selectbox(
            "🔄 Frequência do Backup Automático:",
            options=options,
            index=options.index(current_freq) if current_freq in options else 0
        )

        if new_freq != current_freq:
            set_config('backup_frequencia', new_freq)
            st.success(f"✅ Frequência de backup atualizada para: {new_freq}")
            st.rerun()

    # Seção de Backup Manual (Adicionada)
    with st.container(border=True):
        st.markdown("**⬇️ Backup Manual e Download**")
        st.info("ℹ️ Gere um backup completo do sistema agora e faça o download imediato.")
        
        if st.button("📦 Gerar Novo Backup", type="primary", use_container_width=True, key="btn_gerar_backup_manual"):
            with st.spinner("⏳ Gerando backup completo..."):
                try:
                    generated_path = backup.backup_local_excel()
                    if generated_path and os.path.exists(generated_path):
                        st.session_state['backup_manual_path'] = generated_path
                        st.session_state['backup_manual_timestamp'] = datetime.now()
                        st.rerun()
                    else:
                        st.error("❌ Falha ao gerar o arquivo de backup.")
                except Exception as e:
                     st.error(f"❌ Erro ao executar backup: {e}")

        # Exibir botão de download se houver um backup válido no estado
        if 'backup_manual_path' in st.session_state and os.path.exists(st.session_state['backup_manual_path']):
            bkp_path = st.session_state['backup_manual_path']
            bkp_time = st.session_state.get('backup_manual_timestamp', datetime.now())
            
            st.success(f"✅ Backup gerado em {bkp_time.strftime('%H:%M:%S')}")
            
            with open(bkp_path, "rb") as f:
                st.download_button(
                    label="⬇️ Baixar Arquivo de Backup (.xlsx)",
                    data=f.read(),
                    file_name=os.path.basename(bkp_path),
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key="download_manual_backup_btn_persistent",
                    type="secondary",
                    use_container_width=True
                )

    # Seção de Restauração (Adicionada)
    with st.container(border=True):
        st.markdown("**♻️ Restaurar Backup**")
        st.info("ℹ️ Utilize esta função para recuperar dados a partir de um arquivo Excel de backup gerado anteriormente. A restauração usará 'Upsert', ou seja, atualizará registros existentes e criará novos.")
        
        uploaded_backup = st.file_uploader("Selecione o arquivo de backup (.xlsx)", type=["xlsx"], key="restore_uploader")
        
        if uploaded_backup:
            st.warning("⚠️ **ATENÇÃO:** Esta operação modificará o banco de dados atual. Recomenda-se gerar um novo backup antes de prosseguir.")
            
            if st.button("🚨 INICIAR RESTAURAÇÃO", type="primary", use_container_width=True):
                with st.spinner("⏳ Restaurando banco de dados... Isso pode levar alguns minutos."):
                    sucesso, mensagem = backup.restore_database(uploaded_backup)
                
                if sucesso:
                    st.success(f"✅ {mensagem}")
                    
                    # Pós-processamento para garantir integridade
                    with st.spinner("🔄 Recalculando prazos e status dos processos restaurados..."):
                        try:
                            initialize_restored_data()
                            st.success("✅ Prazos e status recalculados com sucesso!")
                        except Exception as e:
                            st.error(f"⚠️ Dados restaurados, mas houve erro no recálculo de status: {e}")
                            
                    st.balloons()
                else:
                    st.error(f"❌ {mensagem}")

    # Seção para Configuração do Email de Backup
    with st.container(border=True):
        st.markdown("**📧 Configuração do E-mail para Backup Automático**")
        try:
            current_email = get_config('email_backup_automatico') or ""

            with st.form("config_email_backup"):
                new_email = st.text_input("📧 E-mail para receber os backups automáticos:", value=current_email)
                
                if st.form_submit_button("💾 Salvar E-mail de Backup"):
                    if not new_email:
                        st.error("❌ O campo de e-mail não pode estar vazio.")
                    else:
                        set_config('email_backup_automatico', new_email)
                        st.success(f"✅ E-mail para backups salvo como: {new_email}")
                        st.rerun()
        except Exception as e:
            st.error(f"Erro ao carregar configuração de email: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_tab_relatorios_mensais():
    """Renderiza a aba de Relatórios Mensais (Gerenciais)."""
    st.subheader("📊 Relatórios Gerenciais")
    
    try:
        # ---- Seção 1: Relatório Mensal Individual ----
        with st.container(border=True):
            st.markdown('<h4>📑 Relatório Mensal Individual</h4>', unsafe_allow_html=True)
            st.caption("Gera o relatório de produtividade para um mês específico.")
            
            col_rep1, col_rep2, col_rep3 = st.columns([1, 1, 2])
            
            with col_rep1:
                anos_disponiveis = relatorios.get_available_years()
                if not anos_disponiveis:
                    anos_disponiveis = [datetime.now().year]
                sel_ano = st.selectbox("Ano de Referência", anos_disponiveis, key="rel_mensal_ano")
                
            with col_rep2:
                meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
                hoje = date.today()
                mes_anterior = hoje.month - 1 if hoje.month > 1 else 12
                sel_mes = st.selectbox("Mês de Referência", list(meses.keys()), format_func=lambda x: meses[x], index=mes_anterior-1, key="rel_mensal_mes")
            
            with col_rep3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("📄 Gerar Relatório PDF", type="primary", use_container_width=True, key="btn_rel_mensal"):
                    with st.spinner(f"Processando dados de {meses[sel_mes]}/{sel_ano}..."):
                        try:
                            metricas = relatorios.calcular_metricas_mensais(sel_mes, sel_ano)
                            
                            if not metricas:
                                st.warning("Nenhum dado encontrado para o período selecionado.")
                            else:
                                pdf_bytes = relatorios.gerar_relatorio_pdf(metricas, sel_mes, sel_ano)
                                nome_arquivo = f"Relatorio_Produtividade_{meses[sel_mes]}_{sel_ano}.pdf"
                                st.download_button(
                                    label="⬇️ Baixar Relatório (.pdf)",
                                    data=pdf_bytes,
                                    file_name=nome_arquivo,
                                    mime="application/pdf",
                                    key="download_report_btn_admin",
                                    type="secondary",
                                    use_container_width=True
                                )
                                st.success("✅ Relatório gerado com sucesso!")
                                    
                        except Exception as e:
                            st.error(f"Erro durante a geração do relatório: {e}")

        # ---- Seção 2: Relatório Consolidado por Período ----
        with st.container(border=True):
            st.markdown('<h4>📈 Relatório Consolidado por Período</h4>', unsafe_allow_html=True)
            st.caption("Gera um relatório consolidado agregando dados de múltiplos meses.")
            
            col_p1, col_p2, col_p3, col_p4 = st.columns([1, 1, 1, 1])
            
            with col_p1:
                anos_periodo = relatorios.get_available_years()
                if not anos_periodo:
                    anos_periodo = [datetime.now().year]
                sel_ano_periodo = st.selectbox("Ano", anos_periodo, key="rel_periodo_ano")
            
            with col_p2:
                tipo_periodo = st.selectbox("Tipo de Período", ["Trimestral", "Semestral", "Anual"], key="rel_tipo_periodo")
            
            with col_p3:
                config_periodo = relatorios.PERIODOS_CONFIG.get(tipo_periodo, {})
                opcoes_periodo = {v["nome"]: k for k, v in config_periodo.items()}
                sel_periodo_nome = st.selectbox("Período", list(opcoes_periodo.keys()), key="rel_sel_periodo")
            
            with col_p4:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("📊 Gerar Relatório do Período", type="primary", use_container_width=True, key="btn_rel_periodo"):
                    sel_periodo_key = opcoes_periodo[sel_periodo_nome]
                    meses_periodo = config_periodo[sel_periodo_key]["meses"]
                    nome_completo = config_periodo[sel_periodo_key]["nome"]
                    
                    with st.spinner(f"Processando dados de {nome_completo}/{sel_ano_periodo}..."):
                        try:
                            metricas_per = relatorios.calcular_metricas_periodo(sel_ano_periodo, meses_periodo)
                            
                            if not metricas_per:
                                st.warning("Nenhum dado encontrado para o período selecionado.")
                            else:
                                pdf_bytes_per = relatorios.gerar_relatorio_periodo_pdf(metricas_per, sel_ano_periodo, nome_completo)
                                nome_arq_per = f"Relatorio_Produtividade_{nome_completo.replace(' ', '_').replace('º', '')}_{sel_ano_periodo}.pdf"
                                st.download_button(
                                    label="⬇️ Baixar Relatório Consolidado (.pdf)",
                                    data=pdf_bytes_per,
                                    file_name=nome_arq_per,
                                    mime="application/pdf",
                                    key="download_report_periodo_btn",
                                    type="secondary",
                                    use_container_width=True
                                )
                                st.success("✅ Relatório consolidado gerado com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao gerar relatório do período: {e}")

        # ---- Seção 3: Relatórios em Lote (ZIP) ----
        with st.container(border=True):
            st.markdown('<h4>📦 Relatórios Mensais em Lote (ZIP)</h4>', unsafe_allow_html=True)
            st.caption("Gera todos os relatórios mensais do ano em PDFs individuais e os agrupa em um arquivo ZIP para download.")
            
            col_z1, col_z2 = st.columns([1, 3])
            
            with col_z1:
                anos_lote = relatorios.get_available_years()
                if not anos_lote:
                    anos_lote = [datetime.now().year]
                sel_ano_lote = st.selectbox("Ano para Lote", anos_lote, key="rel_lote_ano")
            
            with col_z2:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("📦 Gerar Todos os Relatórios do Ano (.zip)", type="primary", use_container_width=True, key="btn_rel_lote"):
                    with st.spinner(f"Gerando relatórios para todos os meses de {sel_ano_lote}... Isso pode demorar um pouco."):
                        try:
                            zip_bytes = relatorios.gerar_relatorio_lote_zip(sel_ano_lote)
                            st.download_button(
                                label=f"⬇️ Baixar Relatórios de {sel_ano_lote} (.zip)",
                                data=zip_bytes,
                                file_name=f"Relatorios_Produtividade_{sel_ano_lote}.zip",
                                mime="application/zip",
                                key="download_lote_zip_btn",
                                type="secondary",
                                use_container_width=True
                            )
                            st.success("✅ Pacote de relatórios gerado com sucesso!")
                        except Exception as e:
                            st.error(f"Erro ao gerar relatórios em lote: {e}")
                
    except Exception as e:
        st.error(f"❌ Ocorreu um erro inesperado: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)

def render_tab_corregedoria():
    """Renderiza a aba de Relatório para Corregedoria."""
    st.subheader("⚖️ Relatório para Corregedoria")
    
    st.info("Este relatório gera um extrato detalhado de produtividade de um Procurador e sua equipe (Chefes e Servidores) para fins de correição.")

    try:
        # 1. Seleção de Procurador
        all_users_adm = get_all_users()
        procuradores = [u for u in all_users_adm if u.get('perfil') == 'Procurador']
        
        proc_options = {p.get('nome_completo'): p.get('id') for p in procuradores}
        
        if not proc_options:
            st.warning("Nenhum usuário com perfil 'Procurador' encontrado.")
        else:
            col_sel_proc, col_dates = st.columns([1, 2])
            
            with col_sel_proc:
                selected_proc_name = st.selectbox("Selecione o Procurador:", options=sorted(proc_options.keys()))
                procurador_id = proc_options[selected_proc_name]
            
            with col_dates:
                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    dt_inicio_corr = st.date_input("Data de Início:", value=date.today().replace(day=1), min_value=date(2000, 1, 1), max_value=date(2099, 12, 31), format="DD/MM/YYYY")
                with c_d2:
                    dt_fim_corr = st.date_input("Data de Fim:", value=date.today(), min_value=date(2000, 1, 1), max_value=date(2099, 12, 31), format="DD/MM/YYYY")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("📊 Gerar Relatório de Corregedoria", type="primary", use_container_width=True):
                if dt_inicio_corr > dt_fim_corr:
                    st.error("A data de início não pode ser posterior à data de fim.")
                else:
                    with st.spinner(f"Gerando relatório para {selected_proc_name}..."):
                        try:
                            excel_path = reports_corregedoria.generate_corregedoria_excel(procurador_id, dt_inicio_corr, dt_fim_corr)
                            
                            if excel_path and os.path.exists(excel_path):
                                with open(excel_path, "rb") as f:
                                    st.success("✅ Relatório gerado com sucesso!")
                                    st.download_button(
                                        label="⬇️ Baixar Relatório Corregedoria (.xlsx)",
                                        data=f.read(),
                                        file_name=os.path.basename(excel_path),
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key="download_btn_corregedoria"
                                    )
                            else:
                                st.warning("Nenhum dado encontrado para o período/procurador selecionado (ou erro na geração).")
                                
                        except Exception as e:
                            st.error(f"Erro ao gerar relatório: {e}")
                            import traceback
                            st.code(traceback.format_exc())

    except Exception as e:
        st.error(f"Erro ao carregar lista de procuradores: {e}")

    st.markdown('</div>', unsafe_allow_html=True)

def render_tab_configuracoes():
    """Renderiza a aba de Configurações Gerais do Sistema."""
    st.subheader("⚙️ Configurações Gerais do Sistema")
    
    with st.container(border=True):
        st.markdown("### 📧 Controle Global de E-mails")
        st.markdown(
            """
            Aqui você pode controlar o envio de e-mails por todo o sistema.
            
            **Nota:** O envio de e-mails de **Backup Diário** NÃO é afetado por esta configuração e continuará sendo enviado normalmente para segurança dos dados.
            """
        )
        
        try:
            # Busca configuração atual, default é 'true'
            email_ativo_str = get_config('sistema_email_ativo')
            if email_ativo_str is None:
                email_ativo_str = "true"
            
            email_ativo = email_ativo_str.lower() == 'true'
            
            # Toggle switch
            novo_estado = st.toggle("Ativar envio de e-mails do sistema", value=email_ativo)
            
            # Se estado mudou, salva no banco
            if novo_estado != email_ativo:
                novo_valor_str = "true" if novo_estado else "false"
                set_config('sistema_email_ativo', novo_valor_str)
                
                if novo_estado:
                    st.success("✅ O envio de e-mails foi ATIVADO globalmente.")
                else:
                    st.warning("⛔ O envio de e-mails foi DESATIVADO globalmente. Apenas backups serão enviados.")
                
                # Rerun para atualizar estado visual imediatamente
                st.rerun()
                
            if email_ativo:
                st.caption("🟢 Status: O sistema está enviando notificações normalmente.")
            else:
                st.caption("🔴 Status: O envio de notificações está suspenso.")
                
        except Exception as e:
            st.error(f"Erro ao carregar configurações: {e}")
            
    st.markdown('</div>', unsafe_allow_html=True)

