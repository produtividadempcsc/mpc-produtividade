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
    if start_date is None or prazo_dias is None:
        return None, 0

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

def calculate_net_duration_calendar(start_date: date, end_date: date, id_usuario: int, manual_suspension_days: int = 0):
    """
    Calcula a duração líquida em dias corridos:
    (Data Fim - Data Início + 1) - Dias de Afastamento - Dias Suspensão Manual.
    """
    if not start_date or not end_date or start_date > end_date:
        return 0
    
    # 1. Base Calendar Days
    total_calendar = (end_date - start_date).days + 1
    
    # 2. Subtract Recorded Leaves (Afastamentos DB)
    leave_days = get_leave_days_for_period(start_date, end_date, id_usuario)
    
    # 3. Subtract Manual Suspension (from Process record)
    # Ensure we don't double count if manual suspension overlaps with leave?
    # Usually manual suspension is separate. We assume additive reduction logic as per user request.
    
    net_duration = total_calendar - leave_days - manual_suspension_days
    
    return max(0, net_duration)


# ============================================================================
# BATCH-FRIENDLY VARIANTS
# These accept pre-loaded holidays/leaves to avoid per-row DB calls.
# Use these in report generation where many rows are processed at once.
# ============================================================================

def calculate_due_date_batch(start_date: date, prazo_dias: int, tipo_contagem: str,
                             afastamentos_datas: set, feriados: set,
                             dias_suspensos: int = 0,
                             nao_se_aplica_prazo: bool = False) -> date:
    """
    Batch-friendly version of calculate_due_date.
    Accepts pre-loaded holidays and leave dates instead of fetching from DB.
    """
    if start_date is None or prazo_dias is None:
        return None

    if nao_se_aplica_prazo:
        return date.max

    # Step 1: Calculate base due date
    dias_contados_base = 0
    data_base = start_date

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

    # Step 2: Apply suspension days
    dias_contados_susp = 0
    data_final = data_base

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

    return data_final


def calculate_net_work_days_batch(start_date: date, end_date: date,
                                  afastamentos_datas: set, feriados: set) -> int:
    """
    Batch-friendly version of calculate_net_work_days.
    Accepts pre-loaded holidays and leave dates instead of fetching from DB.
    """
    if not start_date or not end_date or start_date > end_date:
        return 0

    dias_uteis_liquidos = 0
    data_atual = start_date

    while data_atual <= end_date:
        if (data_atual.weekday() < 5
                and data_atual not in feriados
                and data_atual not in afastamentos_datas):
            dias_uteis_liquidos += 1
        data_atual += timedelta(days=1)

    return dias_uteis_liquidos


def calculate_net_duration_calendar_batch(start_date: date, end_date: date,
                                           afastamentos_datas: set,
                                           manual_suspension_days: int = 0) -> int:
    """
    Batch-friendly version of calculate_net_duration_calendar.
    Accepts pre-loaded leave dates instead of fetching from DB.
    """
    if not start_date or not end_date or start_date > end_date:
        return 0

    total_calendar = (end_date - start_date).days + 1

    # Count leave days that overlap with the period
    leave_days = 0
    d = start_date
    while d <= end_date:
        if d in afastamentos_datas:
            leave_days += 1
        d += timedelta(days=1)

    net_duration = total_calendar - leave_days - manual_suspension_days
    return max(0, net_duration)
