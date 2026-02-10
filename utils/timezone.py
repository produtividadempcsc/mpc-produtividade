"""
Funções de fuso horário para o Brasil.
O sistema roda no Streamlit Cloud (UTC), mas os usuários estão no Brasil (GMT-3).

Este módulo NÃO deve ter dependências de outros módulos do projeto para evitar
importações circulares.
"""

from datetime import date, datetime
import pytz

BRAZIL_TZ = pytz.timezone('America/Sao_Paulo')

def now_brazil() -> datetime:
    """
    Retorna o datetime atual no fuso horário do Brasil (America/Sao_Paulo).
    Use esta função em vez de datetime.now() para garantir horário correto.
    """
    return datetime.now(BRAZIL_TZ)

def today_brazil() -> date:
    """
    Retorna a data atual no fuso horário do Brasil (America/Sao_Paulo).
    Use esta função em vez de date.today() para garantir data correta.
    """
    return datetime.now(BRAZIL_TZ).date()
