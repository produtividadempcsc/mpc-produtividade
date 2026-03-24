import auth
import streamlit as st
from datetime import date
from sidebar import build_sidebar
from utils.timezone import today_brazil

# Módulos do projeto
import ui_utils
import utils.common as common_utils
from supabase_client import select_all, QueryBuilder
from services.prazo_service import calculate_due_date_with_details
from forms import display_analise_form # Importa o formulário de análise
from components.process_list_revisao import render_revisao_process_list
from repositories.devolucao_procurador_chefe_repository import get_devolucoes_procurador_chefe_batch

auth.auth_guard()

# ==============================================================================
# CLÁUSULA DE GUARDA DE PERFIL - ESSENCIAL PARA SEGURANÇA
# ==============================================================================
allowed_profiles = ["Chefe de Gabinete"]
if st.session_state.get("active_perfil") not in allowed_profiles:
    st.error("🚫 Apenas usuários com perfil 'Chefe de Gabinete' podem acessar esta página.")
    st.stop()
# ==============================================================================

# CSS Personalizado com as cores do sistema
ui_utils.load_css("style.css")

st.session_state.active_page = "Processos para Revisão"
build_sidebar()

# ROTEADOR DE MODAL: Se um processo foi selecionado para análise, exibe o formulário.
if 'processo_em_analise_id' in st.session_state:
    display_analise_form(st.session_state['processo_em_analise_id'])
else:
    # --- CONTEÚDO PRINCIPAL DA PÁGINA ---
    st.markdown("""
    <div class="main-header">
        <h1>👀 Processos para Revisão</h1>
        <p>Processos concluídos pelos servidores e que aguardam sua análise</p>
    </div>
    """, unsafe_allow_html=True)

    
    user_id = st.session_state.user_id

    
    try:
        id_chefe = st.session_state.active_user_id
        
        # --- INTERFACE DE FILTROS ---
        st.markdown('<div class="filters-header">Painel de Controle da Equipe</div>', unsafe_allow_html=True)

        # Popula a lista de servidores para o filtro
        all_servidores_raw = QueryBuilder("usuarios").eq("perfil", "Servidor").order("nome_completo").execute()
        servidores_equipe = all_servidores_raw
        
        servidores_nomes = [s['nome_completo'] for s in servidores_equipe]
        
        filtro_numero_processo_rev = st.text_input("🔍 Filtrar por Número do Processo:", key="rev_filtro_num", placeholder="Digite o número do processo...")

        f_col1, f_col2, f_col3 = st.columns(3)
        with f_col1:
            opcoes_status_revisao = ["Aguardando Análise", "Revisão Atrasada"]
            filtro_status_revisao = st.multiselect("📊 Status da Revisão", options=opcoes_status_revisao)
        with f_col2:
            filtro_servidor = st.multiselect("👤 Filtrar por Servidor", options=servidores_nomes, key="rev_servidor")
        with f_col3:
            ordenar_por_revisao = st.selectbox("📈 Ordenar por", ["Mais Recentes", "Mais Antigos", "Prazo de Revisão (Crescente)", "Prazo de Revisão (Decrescente)"], key="rev_ordem")

        # Legenda de ícones
        st.markdown("""
        <div class="icon-legend">
            <div class="legend-title">📖 Legenda de Ícones</div>
            <div class="legend-items">
                <div class="legend-item"><span>💬</span> Comentários não lidos</div>
                <div class="legend-item"><span>📎</span> Possui anexos</div>
                <div class="legend-item"><span>📖</span> Descrição disponível</div>
                <div class="legend-item"><span>📄</span> Modelo disponível</div>
                <div class="legend-item"><span>🔥</span> Urgente</div>
                <div class="legend-item"><span>⚠️</span> Prioritário</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- LÓGICA DE QUERY ---
        with st.spinner("Carregando revisões..."):
            qb = QueryBuilder("processos").eq("id_chefe_gabinete", id_chefe).eq("status_servidor", "Concluído")

            # Filtro server-side por número do processo (busca em TODO o banco)
            if filtro_numero_processo_rev:
                search_clean = filtro_numero_processo_rev.strip()
                qb.ilike_all_words("processo_numero", search_clean)
            
            if filtro_status_revisao:
                 qb.in_list("status_chefe", filtro_status_revisao)
            else:
                 qb.in_list("status_chefe", ["Aguardando Análise", "Revisão Atrasada"])

            if filtro_servidor:
                # Get IDs for names
                ids_servidores_filtrados = [s['id'] for s in servidores_equipe if s['nome_completo'] in filtro_servidor]
                if ids_servidores_filtrados:
                     qb.in_list("id_servidor_responsavel", ids_servidores_filtrados)
            
            processos_para_analise = qb.execute()

        # Refinamento local: reordena por similaridade (fuzzy matching)
        if filtro_numero_processo_rev and processos_para_analise:
            processos_para_analise = common_utils.filter_by_similarity(
                search_term=filtro_numero_processo_rev,
                items=processos_para_analise,
                key_func=lambda p: p.get('processo_numero', '')
            )
        
        # --- REESTRUTURAÇÃO: Pré-cálculo dos dados para evitar recálculos no loop ---
        hoje = today_brazil()
        processos_com_dados = []
        # Cache para objetos já buscados
        all_types = select_all("tipos_produto")
        produtos_cache = {p['id']: p for p in all_types}
        
        all_users_cache = select_all("usuarios", "id, nome_completo")
        usuarios_cache = {u['id']: u['nome_completo'] for u in all_users_cache}

        # Busca devoluções do procurador ativas em batch
        processo_ids_batch = [p['id'] for p in processos_para_analise]
        devolucoes_procurador_chefe_ativas = get_devolucoes_procurador_chefe_batch(processo_ids_batch)

        for p in processos_para_analise:
            produto_obj = produtos_cache.get(p.get('id_tipo_produto'))
            dt_conclusao_str = p.get('data_conclusao_servidor')
            dt_atrib_chefe_str = p.get('data_atribuicao_chefe')
            
            if not produto_obj: continue
            
            pid = p.get('id')
            dev_procurador = devolucoes_procurador_chefe_ativas.get(pid)
            
            # Se tiver devolução ATIVA do procurador, usar a data dela como base
            if dev_procurador:
                dt_base_revisao_str = dev_procurador.get('data_devolucao')
            else:
                # Se não houver conclusão do servidor mas o chefe estiver com o processo, usamos a data_atribuicao_chefe ou a data_criacao
                dt_base_revisao_str = dt_atrib_chefe_str or dt_conclusao_str or p.get('created_at', str(today_brazil()))
                
            dt_base_revisao = date.fromisoformat(dt_base_revisao_str[:10])
            
            if dt_conclusao_str:
                dt_conclusao_servidor = date.fromisoformat(dt_conclusao_str[:10])
            else:
                dt_conclusao_servidor = dt_base_revisao
            
            data_final_ajustada, ajuste = calculate_due_date_with_details(
                dt_base_revisao, 
                p.get('prazo_chefe_aplicado', 0), 
                produto_obj.get('tipo_contagem_prazo', 'dias uteis'), 
                p.get('id_chefe_gabinete'), 
                dias_suspensos=p.get('prazo_total_dias_suspenso', 0)
            )
            dias_restantes = (data_final_ajustada - hoje).days
            
            processos_com_dados.append({
                "processo": p,
                "dias_restantes": dias_restantes,
                "data_final_ajustada": data_final_ajustada,
                "ajuste": ajuste,
                "servidor_nome": usuarios_cache.get(p.get('id_servidor_responsavel'), "N/A"),
                "produto_nome": produto_obj.get('nome_produto'),
                "procurador_nome": usuarios_cache.get(p.get('id_procurador'), "N/A"),
                "dt_ref": dt_conclusao_servidor
            })

        # --- Lógica de Ordenação ---
        if ordenar_por_revisao == "Prazo de Revisão (Crescente)": 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["dias_restantes"])
        elif ordenar_por_revisao == "Prazo de Revisão (Decrescente)": 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["dias_restantes"], reverse=True)
        elif ordenar_por_revisao == "Mais Antigos": 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["dt_ref"])
        else: 
            processos_ordenados = sorted(processos_com_dados, key=lambda item: item["dt_ref"], reverse=True)
        
        st.markdown("---")
        
        # --- EXIBIÇÃO DOS RESULTADOS ---
        if not processos_ordenados:
            st.markdown("""
            <div style="text-align: center; padding: 50px; background: white; border-radius: 12px; box-shadow: 0 3px 15px rgba(0,0,0,0.1);">
                <h3 style="color: var(--primary-color);">🔍 Nenhum processo encontrado</h3>
                <p>Tente ajustar os filtros para encontrar os processos desejados.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info(f"Mostrando {len(processos_ordenados)} processos aguardando revisão.")

            # Otimização: Pré-busca de dados de favoritos e anexos
            # Fetch favs for current user


            # Batch check for unread comments (optimization: 2 queries instead of N*2)
            processo_ids_ordenados = [item["processo"].get("id") for item in processos_ordenados]
            unread_comments_cache = common_utils.batch_has_unread_comments(processo_ids_ordenados, st.session_state.user_id)

            if 'history_visible_rev' not in st.session_state:
                st.session_state.history_visible_rev = {}

            render_revisao_process_list(processos_ordenados, unread_comments_cache)


            
    except Exception as e:
        st.error(f"Ocorreu um erro ao carregar a página: {e}")