from datetime import date, timedelta
from repositories.calendar_repository import get_all_holidays
from repositories.afastamento_repository import get_leave_dates_set, get_leave_days_for_period

def calculate_due_date(start_date: date, prazo_dias: int, tipo_contagem: str, 
                       id_usuario: int, dias_suspensos: int = 0, 
                       nao_se_aplica_prazo: bool = False) -> date:
    """
    Calcula a data de vencimento de um prazo.
    """
    data_final, _ = calculate_due_date_with_details(
        start_date, prazo_dias, tipo_contagem, id_usuario, dias_suspensos, nao_se_aplica_prazo
    )
    return data_final


def calculate_due_date_with_details(start_date: date, prazo_dias: int, tipo_contagem: str,
                                     id_usuario: int, dias_suspensos: int = 0,
                                     nao_se_aplica_prazo: bool = False) -> tuple:
    """
    Calcula a data de vencimento de um prazo e retorna a data final e os dias de ajuste.
    """
    if nao_se_aplica_prazo:
        return date.max, 0
    
    # Obter datas de afastamento do usuário
    afastamentos_datas = get_leave_dates_set(id_usuario)
    
    # Obter feriados se for dias úteis
    feriados = set()
    if tipo_contagem == "dias uteis":
        feriados = get_all_holidays()
    
    # Etapa 1: Calcular data final baseada no prazo original
    dias_contados_base = 0
    data_base = start_date
    ajuste_calendario = 0
    
    while dias_contados_base < prazo_dias:
        data_base += timedelta(days=1)
        is_dia_valido = False
        
        if data_base in afastamentos_datas:
            pass
        elif tipo_contagem == "dias uteis":
            if data_base.weekday() < 5 and data_base not in feriados:
                is_dia_valido = True
        else:  # dias corridos
            is_dia_valido = True
        
        if is_dia_valido:
            dias_contados_base += 1
        else:
            ajuste_calendario += 1
    
    # Etapa 2: Aplicar dias de suspensão
    dias_contados_susp = 0
    data_final = data_base
    ajuste_suspensao = 0
    
    while dias_contados_susp < dias_suspensos:
        data_final += timedelta(days=1)
        is_dia_valido = False
        
        if data_final in afastamentos_datas:
            pass
        elif tipo_contagem == "dias uteis":
            if data_final.weekday() < 5 and data_final not in feriados:
                is_dia_valido = True
        else:
            is_dia_valido = True
        
        if is_dia_valido:
            dias_contados_susp += 1
        else:
            ajuste_suspensao += 1
    
    ajuste_total = ajuste_calendario + dias_suspensos + ajuste_suspensao
    
    return data_final, ajuste_total

def calculate_calendar_days_minus_leave(start_date: date, end_date: date, id_usuario: int):
    """
    Calcula a quantidade de dias corridos entre duas datas,
    subtraindo apenas os dias de afastamento do usuário no período.
    """
    if not start_date or not end_date or start_date > end_date:
        return 0
    
    total_calendar_days = (end_date - start_date).days + 1
    leave_days = get_leave_days_for_period(start_date, end_date, id_usuario)
    effective_duration = total_calendar_days - leave_days
    
    return max(0, effective_duration)

def calculate_net_work_days(start_date: date, end_date: date, id_usuario: int):
    """
    Calcula o número de dias úteis LÍQUIDOS entre duas datas,
    desconsiderando fins de semana, feriados e afastamentos do usuário.
    """
    if not start_date or not end_date or start_date > end_date:
        return 0
    
    feriados = get_all_holidays()
    afastamentos_datas = get_leave_dates_set(id_usuario)
    
    dias_uteis_liquidos = 0
    data_atual = start_date
    
    while data_atual <= end_date:
        is_weekday = data_atual.weekday() < 5
        is_not_holiday = data_atual not in feriados
        is_not_on_leave = data_atual not in afastamentos_datas
        
        if is_weekday and is_not_holiday and is_not_on_leave:
            dias_uteis_liquidos += 1
        
        data_atual += timedelta(days=1)
    
    return dias_uteis_liquidos

def count_business_days(start_date: date, end_date: date):
    """Calcula o número de dias úteis entre duas datas (inclusivo)."""
    if start_date > end_date:
        return 0
    
    feriados = get_all_holidays()
    
    dias_uteis_contados = 0
    data_atual = start_date
    
    while data_atual <= end_date:
        if data_atual.weekday() < 5 and data_atual not in feriados:
            dias_uteis_contados += 1
        data_atual += timedelta(days=1)
    
    return dias_uteis_contados
