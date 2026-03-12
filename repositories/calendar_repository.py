import streamlit as st
from datetime import datetime, date
from supabase_client import QueryBuilder

@st.cache_data(ttl=86400) # Cache for 24 hours
def get_all_holidays():
    """Retorna todas as datas de feriados/dias não úteis."""
    result = QueryBuilder("calendario").eq("e_dia_util", False).execute()
    # Converter strings de data para objetos date
    return {datetime.fromisoformat(r['data']).date() for r in result if r.get('data')}

def get_holidays_only(): # For admin usage
    """Retorna apenas feriados (dias não úteis que não são fim de semana)."""
    entries = QueryBuilder("calendario").eq("e_dia_util", False).order("data").execute()
    # Filter out weekends (stored as dia_semana)
    weekends = ['Sábado', 'Domingo', 'Saturday', 'Sunday']
    return [e for e in entries if e.get('dia_semana') not in weekends]

def is_business_day(day: date):
    """Verifica se um dia é útil (não é fim de semana nem feriado)."""
    if day.weekday() >= 5:  # Sábado ou Domingo
        return False
    
    # Verificar se é feriado
    holidays = get_all_holidays()
    return day not in holidays

def upsert_calendar_entry(data_date, dia_semana, e_dia_util):
    """Insere ou atualiza uma entrada no calendário."""
    from supabase_client import supabase # imports locais para evitar circular se for o caso
    
    data_iso = data_date.isoformat()
    
    # 1. Remove existing
    supabase.table("calendario").delete().eq("data", data_iso).execute()
    
    # 2. Insert new
    supabase.table("calendario").insert({
        "data": data_iso,
        "dia_semana": dia_semana,
        "e_dia_util": e_dia_util
    }).execute()
