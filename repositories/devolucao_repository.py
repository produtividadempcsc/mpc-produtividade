"""
Repositório para operações de devolução de processos.
Gerencia a tabela processo_devolucoes que rastreia cada vez que
um chefe de gabinete devolve um processo para o servidor.
"""

from supabase_client import QueryBuilder, insert, update_by_id


def registrar_devolucao(id_processo: int, data_devolucao, prazo_dias: int,
                        observacao: str = None, id_usuario_devolucao: int = None):
    """
    Registra uma nova devolução de processo na tabela auxiliar.
    
    Args:
        id_processo: ID do processo devolvido
        data_devolucao: Data em que o processo foi devolvido (date ou str ISO)
        prazo_dias: Novo prazo definido pelo chefe (em dias)
        observacao: Observação da devolução
        id_usuario_devolucao: ID do chefe que devolveu
    
    Returns:
        Dict do registro inserido ou None
    """
    data = {
        "id_processo": id_processo,
        "data_devolucao": data_devolucao.isoformat() if hasattr(data_devolucao, 'isoformat') else data_devolucao,
        "prazo_dias": prazo_dias,
        "observacao": observacao,
        "id_usuario_devolucao": id_usuario_devolucao
    }
    return insert("processo_devolucoes", data)


def get_ultima_devolucao(id_processo: int):
    """
    Retorna a devolução mais recente de um processo (a ativa).
    
    Args:
        id_processo: ID do processo
    
    Returns:
        Dict com os dados da devolução ou None
    """
    result = QueryBuilder("processo_devolucoes") \
        .eq("id_processo", id_processo) \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()
    return result[0] if result else None


def get_devolucao_ativa(id_processo: int):
    """
    Retorna a devolução ativa (sem data_conclusao_servidor) de um processo.
    
    Args:
        id_processo: ID do processo
    
    Returns:
        Dict com os dados da devolução ativa ou None
    """
    result = QueryBuilder("processo_devolucoes") \
        .eq("id_processo", id_processo) \
        .is_null("data_conclusao_servidor") \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()
    return result[0] if result else None


def concluir_devolucao(id_processo: int, data_conclusao):
    """
    Marca a devolução ativa de um processo como concluída.
    Chamado quando o servidor conclui o processo após devolução.
    
    Args:
        id_processo: ID do processo
        data_conclusao: Data de conclusão pelo servidor
    """
    devolucao = get_devolucao_ativa(id_processo)
    if devolucao:
        update_by_id("processo_devolucoes", devolucao['id'], {
            "data_conclusao_servidor": data_conclusao.isoformat() if hasattr(data_conclusao, 'isoformat') else data_conclusao
        })


def get_todas_devolucoes(id_processo: int):
    """
    Retorna todas as devoluções de um processo, ordenadas da mais recente.
    
    Args:
        id_processo: ID do processo
    
    Returns:
        Lista de dicts com os dados das devoluções
    """
    return QueryBuilder("processo_devolucoes") \
        .eq("id_processo", id_processo) \
        .order("created_at", desc=True) \
        .execute()


def get_devolucoes_batch(processo_ids: list):
    """
    Busca as devoluções ativas de vários processos em batch (otimizado).
    Retorna um dict {id_processo: devolucao_mais_recente_ativa}.
    
    Args:
        processo_ids: Lista de IDs de processos
    
    Returns:
        Dict {id_processo: devolucao_dict ou None}
    """
    if not processo_ids:
        return {}
    
    result = QueryBuilder("processo_devolucoes") \
        .in_list("id_processo", processo_ids) \
        .is_null("data_conclusao_servidor") \
        .order("created_at", desc=True) \
        .execute()
    
    # Agrupar por processo (pegar a mais recente de cada)
    devolucoes = {}
    for d in result:
        pid = d['id_processo']
        if pid not in devolucoes:
            devolucoes[pid] = d
    
    return devolucoes
