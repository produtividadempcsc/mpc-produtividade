"""
Repositório para operações de devolução de processos do Procurador para o Chefe de Gabinete.
Gerencia a tabela devolucoes_procurador_chefe.
"""

from supabase_client import QueryBuilder, insert, update_by_id

def registrar_devolucao_procurador_chefe(id_processo: int, data_devolucao, prazo_dias: int,
                        observacao: str = None, id_usuario_devolucao: int = None):
    """
    Registra uma nova devolução de processo na tabela devolucoes_procurador_chefe.
    """
    data = {
        "id_processo": id_processo,
        "data_devolucao": data_devolucao.isoformat() if hasattr(data_devolucao, 'isoformat') else data_devolucao,
        "prazo_dias": prazo_dias,
        "observacao": observacao,
        "id_usuario_devolucao": id_usuario_devolucao
    }
    return insert("devolucoes_procurador_chefe", data)

def get_devolucao_procurador_chefe_ativa(id_processo: int):
    """
    Retorna a devolução ativa (sem data_conclusao_chefe) de um processo.
    """
    result = QueryBuilder("devolucoes_procurador_chefe") \
        .eq("id_processo", id_processo) \
        .is_null("data_conclusao_chefe") \
        .order("created_at", desc=True) \
        .limit(1) \
        .execute()
    return result[0] if result else None

def concluir_devolucao_procurador_chefe(id_processo: int, data_conclusao):
    """
    Marca a devolução ativa de um processo como concluída pelo chefe.
    """
    devolucao = get_devolucao_procurador_chefe_ativa(id_processo)
    if devolucao:
        update_by_id("devolucoes_procurador_chefe", devolucao['id'], {
            "data_conclusao_chefe": data_conclusao.isoformat() if hasattr(data_conclusao, 'isoformat') else data_conclusao
        })

def get_devolucoes_procurador_chefe_batch(processo_ids: list):
    """
    Busca as devoluções ativas de vários processos em batch.
    Retorna um dict {id_processo: devolucao_mais_recente_ativa}.
    """
    if not processo_ids:
        return {}
    
    result = QueryBuilder("devolucoes_procurador_chefe") \
        .in_list("id_processo", processo_ids) \
        .is_null("data_conclusao_chefe") \
        .order("created_at", desc=True) \
        .execute()
    
    devolucoes = {}
    for d in result:
        pid = d['id_processo']
        if pid not in devolucoes:
            devolucoes[pid] = d
    
    return devolucoes
