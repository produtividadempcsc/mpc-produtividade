import auth
import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import os
import threading
from sidebar import build_sidebar

# Módulos do projeto
# (Backup removido pois agora é via Supabase Cloud)
import utils
from utils.common import generate_nome_id
import relatorios
import reports_corregedoria
from utils.jobs import initialize_restored_data # Importação para pós-processamento de restore
import ui_utils
import backup


from db_compat import (
    get_all_product_types, get_product_type_by_id, get_product_type_by_name,
    create_product_type, update_product_type, delete_product_type, get_latest_product_versions,
    get_holidays_only, upsert_calendar_entry,
    get_config, set_config, get_all_users, create_leave
)
from supabase_client import supabase, QueryBuilder, select_first

auth.auth_guard()

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
if st.session_state.get("active_perfil") != "Administrador":
    st.error("🚫 Você não tem permissão para acessar esta página.")
    st.stop()
# ==============================================================================

st.session_state.active_page = "Administração"
build_sidebar()

# CSS Profissional com as cores do sistema
ui_utils.load_css("styles/admin.css")

st.title("🏛️ Painel de Administração")

admin_tabs = st.tabs([
    "📦 Tipos de Produto", 
    "📅 Gerenciar Feriados", 
    "🌴 Afastamento Global", 
    "💾 Gerenciar Backup", 
    "📊 Relatório Mensal",
    "⚖️ Relatório Corregedoria",
    "⚙️ Configurações Gerais"
])

# --- ABA GERENCIAR TIPOS DE PRODUTO ---
with admin_tabs[0]:
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
            st.dataframe(df_prods, width="stretch")
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
                data_criacao = st.date_input("📅 Data de Criação", value=date.today())
                data_validade = st.date_input("⏰ Data de Validade", value=date.today())
                
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
                sel_prod_name = st.selectbox("🔍 Selecione o Produto", options=prod_dict.keys(), key="prod_edit_select")
                
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
                            n_data_validade = st.date_input("⏰ Data de Validade", value=current_validade or date.today())
                            
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
                        nova_vigencia = st.date_input("📅 Vigência do Novo Prazo", value=date.today())
                    
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

# --- ABA GERENCIAR FERIADOS ---
with admin_tabs[1]:
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
            st.dataframe(df_feriados[["📅 Data", "🎉 Descrição"]], width="stretch", hide_index=True)
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
                data_feriado = st.date_input("📅 Selecione a Data do Feriado")
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

# --- ABA AFASTAMENTO GLOBAL ---
with admin_tabs[2]:
    st.subheader("🌴 Lançar Afastamento Coletivo para Todos os Usuários")

    with st.form("global_recess_form", clear_on_submit=True):
        st.error("🚨 **Atenção:** Esta ação adicionará um período de afastamento para **TODOS** os usuários do sistema. Use com cuidado.")
        
        descricao = st.text_input("📋 Descrição do Afastamento", 
                                placeholder="Ex: Recesso de Final de Ano")
        
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("📅 Data de Início", key="global_recess_start_date")
        with col2:
            data_fim = st.date_input("📅 Data de Fim", key="global_recess_end_date")

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

# --- ABA GERENCIAR BACKUP ---
with admin_tabs[3]:
    st.subheader("💾 Gerenciamento de Backup")

    # st.warning("⚠️ O sistema de backup está temporariamente desativado...") # REMOVIDO
    st.info("✅ O sistema de backup automático está ativo e integrado ao banco de dados em nuvem.")
    
    # Seção para Configuração do Backup Automático
    with st.container(border=True):
        st.markdown("**⚙️ Configuração do Backup Automático**")
        try:
            current_freq = get_config('backup_frequencia') or "Diário"
        except:
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
        
        if st.button("📦 Gerar Novo Backup", type="primary", width='stretch', key="btn_gerar_backup_manual"):
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
                    width='stretch'
                )

    # Seção de Restauração (Adicionada)
    with st.container(border=True):
        st.markdown("**♻️ Restaurar Backup**")
        st.info("ℹ️ Utilize esta função para recuperar dados a partir de um arquivo Excel de backup gerado anteriormente. A restauração usará 'Upsert', ou seja, atualizará registros existentes e criará novos.")
        
        uploaded_backup = st.file_uploader("Selecione o arquivo de backup (.xlsx)", type=["xlsx"], key="restore_uploader")
        
        if uploaded_backup:
            st.warning("⚠️ **ATENÇÃO:** Esta operação modificará o banco de dados atual. Recomenda-se gerar um novo backup antes de prosseguir.")
            
            if st.button("🚨 INICIAR RESTAURAÇÃO", type="primary", width='stretch'):
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

# --- ABA RELATÓRIO MENSAL ---
with admin_tabs[4]:
    st.subheader("📊 Relatórios Gerenciais")
    
    # st.warning("⚠️ O sistema de relatórios está temporariamente desativado enquanto finalizamos a migração para o Supabase.")
    
    try:
        # --- SEÇÃO DE GERAÇÃO MANUAL ---
        st.markdown('<h3 class="section-header">📑 Gerar Relatório Mensal</h3>', unsafe_allow_html=True)
        st.markdown("Selecione o período desejado para gerar o arquivo Excel com os indicadores de produtividade.")
        
        col_rep1, col_rep2, col_rep3 = st.columns([1, 1, 2])
        
        with col_rep1:
            anos_disponiveis = relatorios.get_available_years()
            if not anos_disponiveis:
                anos_disponiveis = [datetime.now().year]
            sel_ano = st.selectbox("Ano de Referência", anos_disponiveis)
            
        with col_rep2:
            meses = {1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril", 5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto", 9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"}
            # Default to previous month
            hoje = date.today()
            mes_anterior = hoje.month - 1 if hoje.month > 1 else 12
            # If jan, prev month is dec of prev year basically, but user selects year manually above.
            sel_mes = st.selectbox("Mês de Referência", list(meses.keys()), format_func=lambda x: meses[x], index=mes_anterior-1)
        
        with col_rep3:
            st.markdown("<br>", unsafe_allow_html=True) # Spacer
            if st.button("📊 Gerar Relatório Excel", type="primary", width='stretch'):
                with st.spinner(f"Processando dados de {meses[sel_mes]}/{sel_ano}..."):
                    try:
                        # 1. Calcular Métricas
                        metricas = relatorios.calcular_metricas_mensais(sel_mes, sel_ano)
                        
                        if not metricas:
                            st.warning("Nenhum dado encontrado para o período selecionado.")
                        else:
                            # 2. Gerar XLSX
                            xlsx_path = relatorios.gerar_relatorio_xlsx(metricas, sel_mes, sel_ano)
                            
                            if xlsx_path and os.path.exists(xlsx_path):
                                with open(xlsx_path, "rb") as f:
                                    st.download_button(
                                        label="⬇️ Baixar Relatório Gerado (.xlsx)",
                                        data=f.read(),
                                        file_name=os.path.basename(xlsx_path),
                                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key="download_report_btn_admin",
                                        type="secondary",
                                        width='stretch'
                                    )
                                st.success("✅ Relatório gerado com sucesso! Clique no botão acima para baixar.")
                            else:
                                st.error("Erro ao gerar o arquivo físico do relatório.")
                                
                    except Exception as e:
                        st.error(f"Erro durante a geração do relatório: {e}")
                                
    except Exception as e:
        st.error(f"❌ Ocorreu um erro inesperado: {e}")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- ABA RELATÓRIO CORREGEDORIA ---
with admin_tabs[5]:
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
                    dt_inicio_corr = st.date_input("Data de Início:", value=date.today().replace(day=1))
                with c_d2:
                    dt_fim_corr = st.date_input("Data de Fim:", value=date.today())
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("📊 Gerar Relatório de Corregedoria", type="primary", width='stretch'):
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

# --- ABA CONFIGURAÇÕES GERAIS ---
with admin_tabs[6]:
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