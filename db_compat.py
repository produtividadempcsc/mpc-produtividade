import streamlit as st
from datetime import date
from supabase_client import supabase, QueryBuilder, select_all, select_by_id, select_where, select_first, insert, update_by_id, delete_by_id
from utils.timezone import now_brazil, today_brazil

from repositories.afastamento_repository import (
    get_leave_days_for_period
)

# Re-export for external usage
get_leave_days_for_period = get_leave_days_for_period

# ============================================================================
# Funções de Usuário
# ============================================================================

def get_user_by_id(user_id: int):
    """Busca usuário por ID."""
    return select_by_id("usuarios", user_id)


def get_user_by_login(login: str):
    """Busca usuário por login."""
    return select_first("usuarios", "login", login)


def get_all_users():
    """Retorna todos os usuários."""
    return select_all("usuarios")


@st.cache_data(ttl=300)  # Cache por 5 minutos
def get_all_users_cached():
    """Retorna todos os usuários (com cache)."""
    return select_all("usuarios")


@st.cache_data(ttl=600)  # Cache por 10 minutos
def get_all_product_types_cached():
    """Retorna todos os tipos de produto (com cache)."""
    return select_all("tipos_produto")


def get_active_users():
    """Retorna apenas usuários ativos."""
    return QueryBuilder("usuarios").eq("ativo", True).order("nome_completo").execute()


def toggle_user_active_status(user_id: int, active: bool):
    """Ativa ou desativa um usuário."""
    return update_by_id("usuarios", user_id, {"ativo": active})


def update_user(user_id: int, data: dict):
    """Atualiza dados de um usuário."""
    return update_by_id("usuarios", user_id, data)


# ============================================================================
# Funções de Processo
# ============================================================================

def get_process_by_id(process_id: int):
    """Busca processo por ID."""
    return select_by_id("processos", process_id)


def get_processes_by_user(user_id: int, role_column: str = "id_servidor_responsavel"):
    """Busca processos de um usuário por papel."""
    return select_where("processos", role_column, user_id)


def update_process(process_id: int, data: dict):
    """Atualiza dados de um processo."""
    return update_by_id("processos", process_id, data)


# ============================================================================
# Funções de Tipo de Produto
# ============================================================================

def get_product_type_by_id(product_id: int):
    """Busca tipo de produto por ID."""
    return select_by_id("tipos_produto", product_id)


def get_product_type_by_name(name: str):
    """Busca tipo de produto por nome."""
    return select_first("tipos_produto", "nome_produto", name)


def get_correct_product_type_version(original_product_id: int, reference_date: date):
    """
    Busca a versão correta do TipoProduto com base em uma data de referência.
    """
    if not original_product_id or not reference_date:
        return None
    
    # Buscar produto original
    produto_original = get_product_type_by_id(original_product_id)
    if not produto_original:
        return None
    
    nome_produto = produto_original.get('nome_produto')
    ref_date_str = reference_date.isoformat() if isinstance(reference_date, date) else reference_date
    
    # Buscar versão correta
    produtos = QueryBuilder("tipos_produto") \
        .eq("nome_produto", nome_produto) \
        .gte("data_validade", ref_date_str) \
        .order("data_validade") \
        .execute()
    
    if produtos:
        return produtos[0]
    
    # Fallback: retornar a versão mais recente
    produtos = QueryBuilder("tipos_produto") \
        .eq("nome_produto", nome_produto) \
        .order("data_validade", desc=True) \
        .limit(1) \
        .execute()
    
    return produtos[0] if produtos else None


# ============================================================================
# Funções de Notificação
# ============================================================================

def create_notification(user_id: int, message: str, tipo: str = "sistema", id_processo: int = None):
    """Cria uma notificação no sistema para um usuário específico.
    
    Args:
        user_id: ID do usuário destinatário
        message: Mensagem da notificação
        tipo: Tipo da notificação ('sistema', 'prazo', 'devolucao', 'conclusao', 'comentario', 'atribuicao')
        id_processo: ID do processo relacionado (para link direto)
    """
    try:
        data = {
            "id_usuario_destino": user_id,
            "mensagem": message,
            "lida": False,
            "timestamp": now_brazil().isoformat(),
            "tipo": tipo,
        }
        if id_processo is not None:
            data["id_processo"] = id_processo
        result = insert("notificacoes", data)
        print(f"Notificação criada para o usuário {user_id}: {message}")
        return result
    except Exception as e:
        print(f"ERRO ao criar notificação para o usuário {user_id}: {e}")
        return None


def get_user_notifications(user_id: int, limit: int = 10):
    """Retorna as notificações de um usuário."""
    return QueryBuilder("notificacoes") \
        .eq("id_usuario_destino", user_id) \
        .order("timestamp", desc=True) \
        .limit(limit) \
        .execute()


def mark_notifications_as_read(user_id: int):
    """Marca todas as notificações não lidas de um usuário como lidas."""
    unread = QueryBuilder("notificacoes") \
        .eq("id_usuario_destino", user_id) \
        .eq("lida", False) \
        .execute()
    
    for notif in unread:
        update_by_id("notificacoes", notif['id'], {"lida": True})


# ============================================================================
# Funções de Histórico de Processo
# ============================================================================

def get_process_history(process_id: int):
    """Retorna o histórico de um processo."""
    return QueryBuilder("processo_historico") \
        .eq("id_processo", process_id) \
        .order("timestamp", desc=True) \
        .execute()


def add_process_history(process_id: int, user_id: int, action: str, details: str = None):
    """Adiciona uma entrada no histórico de um processo."""
    data = {
        "id_processo": process_id,
        "id_usuario_acao": user_id,
        "evento": action,
        "observacao": details,
        "timestamp": now_brazil().isoformat()
    }
    return insert("processo_historico", data)


# ============================================================================
# Funções de Substituição
# ============================================================================

def get_active_substitution(user_id: int):
    """Verifica se o usuário tem uma substituição ativa."""
    hoje = today_brazil().isoformat()
    
    result = QueryBuilder("substituicoes") \
        .eq("id_servidor_substituto", user_id) \
        .lte("data_inicio", hoje) \
        .gte("data_fim", hoje) \
        .execute()
    
    return result[0] if result else None


# ============================================================================
# Funções de Comentário
# ============================================================================

def get_process_comments(process_id: int):
    """Retorna os comentários de um processo."""
    return QueryBuilder("comentarios") \
        .eq("id_processo", process_id) \
        .order("timestamp", desc=True) \
        .execute()


def add_comment(process_id: int, user_id: int, text: str):
    """Adiciona um comentário a um processo."""
    data = {
        "id_processo": process_id,
        "id_usuario": user_id,
        "texto": text,
        "timestamp": now_brazil().isoformat()
    }
    return insert("comentarios", data)


# ============================================================================
# Funções de Cálculo de Prazo
# ============================================================================




# ============================================================================
# Funções de Hierarquia e Relacionamentos
# ============================================================================

def get_user_bosses(servidor_id: int):
    """Retorna a lista de usuários que são chefes do servidor fornecido."""
    # Passo 1: Buscar IDs dos chefes na tabela de associação
    relations = QueryBuilder("gabinete_servidores") \
        .eq("servidor_id", servidor_id) \
        .select("chefe_id") \
        .execute()
    
    if not relations:
        return []
    
    chefe_ids = [r['chefe_id'] for r in relations]
    
    # Passo 2: Buscar os usuários chefes
    if not chefe_ids:
        return []
        
    chefes = QueryBuilder("usuarios") \
        .in_list("id", chefe_ids) \
        .execute()
        
    return chefes


def get_prosecutors_linked_to_users(user_ids: list):
    """Retorna lista de procuradores vinculados a uma lista de usuários (geralmente chefes)."""
    if not user_ids:
        return []
        
    # Passo 1: Buscar IDs dos procuradores na tabela de associação
    relations = QueryBuilder("procurador_chefes") \
        .in_list("chefe_id", user_ids) \
        .select("procurador_id") \
        .execute()
        
    if not relations:
        return []
        
    proc_ids = list(set([r['procurador_id'] for r in relations]))
    
    # Passo 2: Buscar os usuários procuradores
    procuradores = QueryBuilder("usuarios") \
        .in_list("id", proc_ids) \
        .execute()
        
    return procuradores


def get_prosecutors_of_boss(chefe_id: int):
    """Retorna procuradores de um chefe específico."""
    return get_prosecutors_linked_to_users([chefe_id])


def toggle_process_favorite(user_id: int, process_id: int):
    """Alterna o estado de favorito de um processo para um usuário."""
    # Verificar se já existe
    exists = QueryBuilder("processo_favoritos") \
        .eq("id_usuario", user_id) \
        .eq("id_processo", process_id) \
        .execute()
        
    if exists:
        # Remove
        QueryBuilder("processo_favoritos") \
            .eq("id_usuario", user_id) \
            .eq("id_processo", process_id) \
            .delete()
        return False # Não é mais favorito
    else:
        # Adiciona
        insert("processo_favoritos", {"id_usuario": user_id, "id_processo": process_id})
        return True # Agora é favorito


def is_process_favorite(user_id: int, process_id: int):
    """Verifica se um processo é favorito do usuário."""
    exists = QueryBuilder("processo_favoritos") \
        .eq("id_usuario", user_id) \
        .eq("id_processo", process_id) \
        .execute()
    return len(exists) > 0


def get_user_favorites(user_id: int):
    """Retorna lista de processos favoritos do usuário."""
    return QueryBuilder("processo_favoritos") \
        .eq("id_usuario", user_id) \
        .execute()


def get_product_types():
    """Retorna todos os tipos de produto."""
    return select_all("tipos_produto")


def get_user_subordinates(user_id: int):
    """Retorna chefes subordinados ao usuário."""
    relations = QueryBuilder("chefe_subordinado_chefe") \
        .eq("chefe_superior_id", user_id) \
        .select("chefe_subordinado_id") \
        .execute()
    if not relations: return []
    ids = [r['chefe_subordinado_id'] for r in relations]
    if not ids: return []
    return QueryBuilder("usuarios").in_list("id", ids).execute()


def get_direct_servants(user_id: int):
    """Retorna servidores diretos do usuário."""
    relations = QueryBuilder("gabinete_servidores") \
        .eq("chefe_id", user_id) \
        .select("servidor_id") \
        .execute()
    if not relations: return []
    ids = [r['servidor_id'] for r in relations]
    if not ids: return []
    return QueryBuilder("usuarios").in_list("id", ids).execute()



def mark_comments_as_read(user_id: int, comment_ids: list):
    """Marca lista de comentários como lidos pelo usuário."""
    if not comment_ids: return
    
    # Check which are already read to avoid duplicates
    existing = QueryBuilder("comentario_lido") \
        .eq("id_usuario", user_id) \
        .in_list("id_comentario", comment_ids) \
        .execute()
    
    existing_ids = {r['id_comentario'] for r in existing}
    to_insert = [cid for cid in comment_ids if cid not in existing_ids]
    
    if to_insert:
        data = [{"id_usuario": user_id, "id_comentario": cid} for cid in to_insert]
        insert("comentario_lido", data)






# ============================================================================
# Funções de Gerenciamento de Usuários (Admin)
# ============================================================================

def create_user(data: dict):
    """Cria um novo usuário."""
    return insert("usuarios", data)

def delete_user(user_id: int):
    """
    Deleta um usuário e todos os seus dados relacionados.
    Remove primeiro os relacionamentos para evitar erros de foreign key.
    """
    try:
        # 1. Remover relacionamentos de gabinete (servidor-chefe)
        QueryBuilder("gabinete_servidores").eq("servidor_id", user_id).delete()
        QueryBuilder("gabinete_servidores").eq("chefe_id", user_id).delete()
        
        # 2. Remover relacionamentos de procurador-chefe
        QueryBuilder("procurador_chefes").eq("chefe_id", user_id).delete()
        QueryBuilder("procurador_chefes").eq("procurador_id", user_id).delete()
        
        # 3. Remover relacionamentos de subordinação entre chefes
        QueryBuilder("chefe_subordinado_chefe").eq("chefe_subordinado_id", user_id).delete()
        QueryBuilder("chefe_subordinado_chefe").eq("chefe_superior_id", user_id).delete()
        
        # 4. Remover substituições
        QueryBuilder("substituicoes").eq("id_chefe_titular", user_id).delete()
        QueryBuilder("substituicoes").eq("id_servidor_substituto", user_id).delete()
        
        # 5. Remover afastamentos
        QueryBuilder("afastamentos").eq("id_usuario", user_id).delete()
        
        # 6. Remover notificações
        QueryBuilder("notificacoes").eq("id_usuario_destino", user_id).delete()
        
        # 7. Remover favoritos de processos
        QueryBuilder("processo_favoritos").eq("id_usuario", user_id).delete()
        
        # 8. Remover marcações de comentários lidos
        QueryBuilder("comentario_lido").eq("id_usuario", user_id).delete()
        
        # 9. Remover histórico de processos (ações do usuário)
        QueryBuilder("processo_historico").eq("id_usuario_acao", user_id).delete()
        
        # 10. Finalmente, deletar o usuário
        return delete_by_id("usuarios", user_id)
    except Exception as e:
        print(f"[DB_COMPAT] Erro ao deletar usuário {user_id}: {e}")
        return False

def manage_user_relations(user_id: int, relation_table: str, id_col_main: str, id_col_rel: str, related_ids: list):
    """
    Gerencia relacionamentos many-to-many (limpa e insere novos).
    Ex: user_id=10, relation_table='gabinete_servidores', id_col_main='servidor_id', id_col_rel='chefe_id', related_ids=[1, 2]
    """
    # 1. Remove existing
    QueryBuilder(relation_table).eq(id_col_main, user_id).delete()
    
    # 2. Insert new
    if related_ids:
        data = [{id_col_main: user_id, id_col_rel: rid} for rid in related_ids]
        insert(relation_table, data)

# Wrappers for specific relations
def update_servidor_chefes(servidor_id: int, chefe_ids: list):
    manage_user_relations(servidor_id, "gabinete_servidores", "servidor_id", "chefe_id", chefe_ids)

def update_chefe_procuradores(chefe_id: int, procurador_ids: list):
    manage_user_relations(chefe_id, "procurador_chefes", "chefe_id", "procurador_id", procurador_ids)

def update_chefe_superiores(chefe_id: int, superior_ids: list):
    manage_user_relations(chefe_id, "chefe_subordinado_chefe", "chefe_subordinado_id", "chefe_superior_id", superior_ids)


# ============================================================================
# Funções de Substituição
# ============================================================================

def get_all_substituicoes():
    """Retorna todas as substituições."""
    return QueryBuilder("substituicoes").order("data_inicio", desc=True).execute()

def get_substituicoes_by_chefe(chefe_id: int):
    """Retorna substituições de um chefe específico."""
    return QueryBuilder("substituicoes").eq("id_chefe_titular", chefe_id).order("data_inicio", desc=True).execute()

def create_substituicao(data: dict):
    """Cria uma nova substituição."""
    return insert("substituicoes", data)

def delete_substituicao(sub_id: int):
    """Remove uma substituição."""
    return delete_by_id("substituicoes", sub_id)


# ============================================================================
# Funções de Configuração (configuracoes table)
# ============================================================================

def get_config(key: str) -> str:
    """Busca valor de configuração por chave."""
    result = select_first("configuracoes", "chave", key)
    return result.get('valor') if result else None

def set_config(key: str, value: str):
    """Define ou atualiza uma configuração."""
    existing = select_first("configuracoes", "chave", key)
    if existing:
        # Update existing - configuracoes uses 'chave' as primary key, not 'id'
        supabase.table("configuracoes").update({"valor": value}).eq("chave", key).execute()
    else:
        insert("configuracoes", {"chave": key, "valor": value})

def get_all_configs() -> list:
    """Retorna todas as configurações."""
    return select_all("configuracoes")


# ============================================================================
# Funções de Prompt IA (prompts_ia table)
# ============================================================================

def get_all_prompts(user_id: int = None, include_public: bool = True) -> list:
    """Retorna prompts IA, opcionalmente filtrados por usuário."""
    if user_id is None:
        # Return all public prompts
        return QueryBuilder("prompts_ia").eq("e_publico", True).order("data_criacao", desc=True).execute()
    
    if include_public:
        # Return user's prompts + public prompts
        # Supabase doesn't support OR directly in simple queries, so we fetch separately and merge
        user_prompts = QueryBuilder("prompts_ia").eq("id_criador", user_id).execute()
        public_prompts = QueryBuilder("prompts_ia").eq("e_publico", True).execute()
        
        # Merge and deduplicate (by id)
        all_prompts = {p['id']: p for p in user_prompts}
        for p in public_prompts:
            if p['id'] not in all_prompts:
                all_prompts[p['id']] = p
        return sorted(all_prompts.values(), key=lambda x: x.get('data_criacao', ''), reverse=True)
    else:
        # Return only user's prompts
        return QueryBuilder("prompts_ia").eq("id_criador", user_id).order("data_criacao", desc=True).execute()

def get_prompt_by_id(prompt_id: int) -> dict:
    """Busca prompt por ID."""
    return select_by_id("prompts_ia", prompt_id)

def create_prompt(data: dict) -> dict:
    """Cria um novo prompt IA."""
    if 'data_criacao' not in data:
        data['data_criacao'] = now_brazil().isoformat()
    return insert("prompts_ia", data)

def update_prompt(prompt_id: int, data: dict):
    """Atualiza um prompt IA."""
    return update_by_id("prompts_ia", prompt_id, data)

def delete_prompt(prompt_id: int):
    """Remove um prompt IA."""
    return delete_by_id("prompts_ia", prompt_id)


# ============================================================================
# Funções de Tipo de Produto - CRUD Completo (tipos_produto table)
# ============================================================================

def get_all_product_types() -> list:
    """Retorna todos os tipos de produto ordenados."""
    return QueryBuilder("tipos_produto").order("nome_produto").order("versao", desc=True).execute()

def create_product_type(data: dict) -> dict:
    """Cria um novo tipo de produto."""
    if 'data_criacao' not in data:
        data['data_criacao'] = now_brazil().isoformat()
    if 'versao' not in data:
        data['versao'] = 1
    return insert("tipos_produto", data)

def update_product_type(product_id: int, data: dict):
    """Atualiza um tipo de produto."""
    return update_by_id("tipos_produto", product_id, data)

def delete_product_type(product_id: int):
    """Remove um tipo de produto."""
    return delete_by_id("tipos_produto", product_id)

def get_latest_product_versions() -> list:
    """Retorna a versão mais recente de cada tipo de produto."""
    all_products = get_all_product_types()
    # Group by nome_id and get the latest version
    latest = {}
    for p in all_products:
        nome_id = p.get('nome_id')
        if nome_id not in latest or p.get('versao', 0) > latest[nome_id].get('versao', 0):
            latest[nome_id] = p
    return list(latest.values())



# ============================================================================
# Funções de Histórico de Processo (CRUD)
# ============================================================================

def delete_process_history_by_user(user_id: int):
    """Remove histórico de um usuário específico."""
    QueryBuilder("processo_historico").eq("id_usuario_acao", user_id).delete()


# ============================================================================
# Funções Auxiliares para hash de senha (compatibilidade)
# ============================================================================

def hash_password(password: str) -> str:
    """Gera hash bcrypt de uma senha."""
    import bcrypt
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
