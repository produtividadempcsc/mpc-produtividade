
import logging
import streamlit as st
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from datetime import datetime
from utils.jobs import update_process_statuses, send_deadline_notifications
import backup

# Configuração de Logs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Usando st.cache_resource para garantir que o scheduler seja um singleton
# e não seja recriado a cada rerun do Streamlit.
@st.cache_resource
def start_background_worker():
    """
    Inicia o scheduler em background para rodar jobs do worker.py
    dentro do processo do Streamlit.
    """
    logger.info("Iniciando Background Worker Manager...")

    # Instancia o scheduler (BackgroundScheduler roda em threads separadas)
    scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")

    # --- ADICIONANDO JOBS ---
    # Replica a mesma lógica do worker.py original
    
    # 1. Análise de Prazos e Status (Processos) - A cada 1 hora
    scheduler.add_job(
        update_process_statuses, 
        trigger='interval', 
        hours=1, 
        id='analise_prazos_job', 
        replace_existing=True
    )
    logger.info("Job 'analise_prazos_job' agendado (interval=1h).")

    # 2. Notificações (Emails) - A cada dia às 08:00
    scheduler.add_job(
        send_deadline_notifications, 
        trigger='cron', 
        hour=8, 
        id='notification_job', 
        replace_existing=True
    )
    logger.info("Job 'notification_job' agendado (cron=08:00).")

    # 3. Backup Automático - A cada 24 horas
    scheduler.add_job(
        backup.executar_backup_automatico_e_enviar_email, 
        trigger='interval', 
        hours=24, 
        id='auto_backup_job', 
        replace_existing=True
    )
    logger.info("Job 'auto_backup_job' agendado (interval=6h).")

    # --- INICIANDO ---
    try:
        scheduler.start()
        logger.info("Background Worker iniciado com sucesso!")
        return scheduler
    except Exception as e:
        logger.error(f"Erro ao iniciar Background Worker: {e}")
        return None
