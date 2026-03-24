# Re-export commonly used functions for backward compatibility
from utils.common import adicionar_recesso_para_todos_usuarios
from utils.notifications import send_email_notification

__all__ = ['adicionar_recesso_para_todos_usuarios', 'send_email_notification']
