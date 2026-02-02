
import re
import unicodedata
from datetime import date, datetime
from typing import List, Dict, Any, Callable
from thefuzz import fuzz
from supabase_client import QueryBuilder, insert, select_all
from db_compat import (
    get_product_type_by_id, calculate_due_date, select_all
)

# Importar funções de timezone do módulo separado (sem dependências circulares)
from utils.timezone import now_brazil, today_brazil, BRAZIL_TZ

# --- FUNÇÕES DE TEXTO E NORMALIZAÇÃO ---

def normalize_process_number(s: str) -> str:
    """Normaliza o número do processo para comparação, removendo espaços e caracteres especiais."""
    if not s:
        return ""
    return re.sub(r'[\s/.-]', '', s).lower()

def generate_nome_id(nome_produto):
    """Gera um nome_id a partir do nome_produto."""
    if not isinstance(nome_produto, str):
        return None
    s = nome_produto.lower()
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[^a-z0-9]+', '_', s).strip('_')
    return s

def filter_by_similarity(search_term: str, items: list, key_func, threshold=85):
    """
    Filtra uma lista de itens com base na similaridade do número do processo.
    """
    if not search_term:
        return items

    normalized_search_term = normalize_process_number(search_term)

    # 1. Verificação de correspondência exata
    exact_matches = []
    for item in items:
        item_str = key_func(item)
        if item_str and normalize_process_number(item_str) == normalized_search_term:
            exact_matches.append(item)
    
    if exact_matches:
        return exact_matches

    # 2. Busca por sequência de 5 ou mais caracteres
    sequential_matches = []
    for item in items:
        item_str = key_func(item)
        if not item_str:
            continue
        
        normalized_item_str = normalize_process_number(item_str)
        
        if (len(normalized_search_term) >= 5 and normalized_search_term in normalized_item_str) or \
           (len(normalized_item_str) >= 5 and normalized_item_str in normalized_search_term):
            sequential_matches.append(item)

    if sequential_matches:
        return list(dict.fromkeys(sequential_matches))

    # 3. Busca por similaridade (fuzzy)
    filtered_items = []
    for item in items:
        item_str = key_func(item)
        if item_str:
            if fuzz.ratio(normalized_search_term, normalize_process_number(item_str)) >= threshold:
                filtered_items.append(item)
    return filtered_items


# --- FUNÇÕES DE LÓGICA DE NEGÓCIO ---

def get_servidor_status(processo: dict, db_session=None) -> str:
    """
    Calcula e retorna o status correto para a etapa do servidor de um processo.
    (Versão Supabase)
    """
    status_serv = processo.get('status_servidor')
    if status_serv == "Devolvido":
        return "Devolvido"

    if processo.get('nao_se_aplica_prazo_servidor'):
        return "No Prazo"

    produto_obj = get_product_type_by_id(processo.get('id_tipo_produto'))
    if not produto_obj:
        return "Erro de Vinculação"

    dt_atrib = processo.get('data_atribuicao_servidor')
    if isinstance(dt_atrib, str):
        dt_atrib = date.fromisoformat(dt_atrib)

    data_final_servidor = calculate_due_date(
        start_date=dt_atrib,
        prazo_dias=processo.get('prazo_servidor_aplicado'),
        tipo_contagem=produto_obj.get('tipo_contagem_prazo'),
        id_usuario=processo.get('id_servidor_responsavel'),
        dias_suspensos=processo.get('prazo_total_dias_suspenso')
    )

    if today_brazil() > data_final_servidor:
        return "Atrasado"
    else:
        return "No Prazo"


def has_unread_comments(processo_id: int, user_id: int) -> bool:
    """
    Verifica se um processo tem comentários não lidos para um usuário.
    """
    try:
        comments = QueryBuilder("comentarios").eq("id_processo", processo_id).select("id").execute()
        comment_ids = [c['id'] for c in comments]
        
        if not comment_ids:
            return False
            
        read_marks = QueryBuilder("comentario_lido") \
            .eq("id_usuario", user_id) \
            .in_list("id_comentario", comment_ids) \
            .select("id_comentario") \
            .execute()
            
        read_ids = {r['id_comentario'] for r in read_marks}
        
        return len(set(comment_ids)) > len(read_ids)
    except Exception as e:
        print(f"[COMMENTS] Error checking unread status: {e}")
        return False


def batch_has_unread_comments(processo_ids: list, user_id: int) -> dict:
    """
    Verifica quais processos têm comentários não lidos em batch (otimizado).
    Usa apenas 2 queries HTTP em vez de 2*N queries.
    
    Args:
        processo_ids: Lista de IDs de processos para verificar
        user_id: ID do usuário que está verificando
        
    Returns:
        Dict {processo_id: bool} indicando se cada processo tem comentários não lidos
    """
    if not processo_ids:
        return {}
    
    try:
        # Query única para todos os comentários dos processos
        comments = QueryBuilder("comentarios") \
            .in_list("id_processo", processo_ids) \
            .select("id, id_processo") \
            .execute()
        
        if not comments:
            return {pid: False for pid in processo_ids}
        
        # Agrupar comentários por processo
        comments_by_processo = {}
        all_comment_ids = []
        for c in comments:
            pid = c['id_processo']
            if pid not in comments_by_processo:
                comments_by_processo[pid] = []
            comments_by_processo[pid].append(c['id'])
            all_comment_ids.append(c['id'])
        
        # Query única para todos os comentários lidos pelo usuário
        read_marks = QueryBuilder("comentario_lido") \
            .eq("id_usuario", user_id) \
            .in_list("id_comentario", all_comment_ids) \
            .select("id_comentario") \
            .execute()
        
        read_ids = {r['id_comentario'] for r in read_marks}
        
        # Calcular quais processos têm não lidos
        result = {}
        for pid in processo_ids:
            proc_comments = set(comments_by_processo.get(pid, []))
            proc_read = proc_comments & read_ids
            result[pid] = len(proc_comments) > len(proc_read)
        
        return result
        
    except Exception as e:
        print(f"[COMMENTS] Error checking batch unread: {e}")
        return {pid: False for pid in processo_ids}


def adicionar_recesso_para_todos_usuarios(descricao: str, data_inicio: date, data_fim: date):
    """
    Adiciona um período de recesso coletivo para TODOS os usuários do sistema.
    """
    resultados = {
        "adicionados": 0,
        "avisos": 0,
        "usuarios_com_aviso": []
    }

    try:
        todos_usuarios = select_all("usuarios", "id, nome_completo")
        if not todos_usuarios:
            return {"sucesso": False, "mensagem": "Nenhum usuário encontrado no sistema."}

        di_str = data_inicio.isoformat()
        df_str = data_fim.isoformat()

        for usuario in todos_usuarios:
            uid = usuario['id']
            
            count_existente = QueryBuilder("afastamentos") \
                .eq("id_usuario", uid) \
                .eq("descricao", descricao) \
                .eq("data_inicio", di_str) \
                .eq("data_fim", df_str) \
                .count()

            if count_existente > 0:
                resultados["avisos"] += 1
                resultados["usuarios_com_aviso"].append(usuario.get('nome_completo'))
                continue

            novo_afastamento = {
                "id_usuario": uid,
                "descricao": descricao,
                "data_inicio": di_str,
                "data_fim": df_str
            }
            insert("afastamentos", novo_afastamento)
            resultados["adicionados"] += 1

        mensagem = f"Recesso adicionado para {resultados['adicionados']} usuário(s)."
        if resultados["avisos"] > 0:
            mensagem += f" O recesso já existia para {resultados['avisos']} usuário(s)."
        return {"sucesso": True, "mensagem": mensagem, "detalhes": resultados}

    except Exception as e:
        return {"sucesso": False, "mensagem": f"Ocorreu um erro: {e}"}
