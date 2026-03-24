import streamlit as st
from datetime import datetime, timedelta, date
from supabase_client import select_where, QueryBuilder, insert, delete_by_id 
from utils.timezone import today_brazil

@st.cache_data(ttl=600)
def get_user_leaves(user_id: int):
    """Retorna todos os afastamentos de um usuário."""
    result = select_where("afastamentos", "id_usuario", user_id)
    return result or []

@st.cache_data(ttl=600)
def get_leave_dates_set(user_id: int):
    """Retorna um set com todas as datas de afastamento de um usuário."""
    leaves = get_user_leaves(user_id)
    leave_dates = set()
    
    for af in leaves:
        data_inicio = datetime.fromisoformat(af['data_inicio']).date() if isinstance(af.get('data_inicio'), str) else af.get('data_inicio')
        data_fim = datetime.fromisoformat(af['data_fim']).date() if isinstance(af.get('data_fim'), str) else af.get('data_fim')
        
        if data_inicio and data_fim:
            d = data_inicio
            while d <= data_fim:
                leave_dates.add(d)
                d += timedelta(days=1)
    
    return leave_dates


def get_leaves_overlapping(user_id: int, start_date: date, end_date: date):
    """Retorna afastamentos que colidem com um período específico."""
    s_iso = start_date.isoformat()
    e_iso = end_date.isoformat()
    return QueryBuilder("afastamentos") \
        .eq("id_usuario", user_id) \
        .lte("data_inicio", e_iso) \
        .gte("data_fim", s_iso) \
        .execute()

def get_leave_days_for_period(start_date: date, end_date: date, id_usuario: int):
    """
    Calcula a quantidade de dias de afastamento de um usuário dentro de um período.
    """
    if not start_date or not end_date or start_date > end_date:
        return 0
    
    # Otimização: buscar apenas overlap
    leaves = get_leaves_overlapping(id_usuario, start_date, end_date)
    total_leave_days = 0
    
    for af in leaves:
        # Converter datas
        af_inicio = af.get('data_inicio')
        af_fim = af.get('data_fim')
        
        if isinstance(af_inicio, str):
            af_inicio = datetime.fromisoformat(af_inicio).date()
        if isinstance(af_fim, str):
            af_fim = datetime.fromisoformat(af_fim).date()
        
        if af_inicio and af_fim:
            # Calcula a sobreposição do afastamento com o período
            overlap_start = max(start_date, af_inicio)
            overlap_end = min(end_date, af_fim)
            
            if overlap_start <= overlap_end:
                total_leave_days += (overlap_end - overlap_start).days + 1
    
    return total_leave_days

def get_leaves_count(user_ids: list):
    """Retorna contagem de afastamentos para lista de usuários."""
    if not user_ids: return 0
    result = QueryBuilder("afastamentos") \
        .in_list("id_usuario", user_ids) \
        .select("id") \
        .execute()
    return len(result)

def get_all_leaves_count():
    """Retorna contagem total de afastamentos do sistema."""
    # Otimização: Selecionar apenas ID para reduzir tráfego
    res = QueryBuilder("afastamentos").select("id").execute()
    return len(res)

def get_active_leaves_count(user_ids: list):
    """Retorna contagem de afastamentos ativos."""
    if not user_ids: return 0
    today = today_brazil().isoformat()
    result = QueryBuilder("afastamentos") \
        .in_list("id_usuario", user_ids) \
        .lte("data_inicio", today) \
        .gte("data_fim", today) \
        .select("id") \
        .execute()
    return len(result)

@st.cache_data(ttl=600)
def get_all_leave_dates_by_user():
    """
    Carrega afastamentos de TODOS os usuários de uma só vez.
    Retorna um dict {user_id: set(date)} para uso em batch.
    """
    all_leaves = QueryBuilder("afastamentos").fetch_all()
    result = {}
    for af in all_leaves:
        uid = af.get('id_usuario')
        if uid is None:
            continue
        if uid not in result:
            result[uid] = set()
        
        af_inicio = af.get('data_inicio')
        af_fim = af.get('data_fim')
        
        if isinstance(af_inicio, str):
            af_inicio = datetime.fromisoformat(af_inicio).date()
        if isinstance(af_fim, str):
            af_fim = datetime.fromisoformat(af_fim).date()
        
        if af_inicio and af_fim:
            d = af_inicio
            while d <= af_fim:
                result[uid].add(d)
                d += timedelta(days=1)
    
    return result


def get_leaves_filtered(user_ids: list):
    """Retorna afastamentos de uma lista de usuários."""
    if not user_ids: return []
    return QueryBuilder("afastamentos") \
        .in_list("id_usuario", user_ids) \
        .order("data_inicio", desc=True) \
        .execute()

def create_leave(user_id: int, start_date: date, end_date: date, description: str):
    """Cria um novo afastamento."""
    return insert("afastamentos", {
        "id_usuario": user_id,
        "data_inicio": start_date.isoformat(),
        "data_fim": end_date.isoformat(),
        "descricao": description
    })

def delete_leave(leave_id: int):
    """Remove um afastamento."""
    return delete_by_id("afastamentos", leave_id)
