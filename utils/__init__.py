# Re-export commonly used functions for backward compatibility
# Lazy imports para evitar importação circular com supabase_client

def adicionar_recesso_para_todos_usuarios(*args, **kwargs):
    from utils.common import adicionar_recesso_para_todos_usuarios as _fn
    return _fn(*args, **kwargs)

def send_email_notification(*args, **kwargs):
    from utils.notifications import send_email_notification as _fn
    return _fn(*args, **kwargs)

__all__ = ['adicionar_recesso_para_todos_usuarios', 'send_email_notification']
