
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import streamlit as st
from db_compat import get_config

def send_email_notification(destinatario_email: str, assunto: str, corpo: str, attachment_path: str = None, force_send: bool = False):
    """
    Envia notificações por e-mail, com suporte opcional para anexos.
    O parâmetro `force_send` ignora o 'Kill Switch' global de e-mails.
    """
    try:
        # Verificar Kill Switch Global
        email_ativo = get_config('sistema_email_ativo')
        
        # Se for None, assume True (ativado por padrão)
        if email_ativo is None:
            email_ativo = "true"
            
        if email_ativo.lower() != 'true' and not force_send:
            print(f"AVISO: Envio de e-mails está DESATIVADO globalmente. E-mail para {destinatario_email} ignorado.")
            return False

        remetente_user = st.secrets["email_credentials"]["gmail_user"]
        remetente_pass = st.secrets["email_credentials"]["gmail_app_password"]
    except KeyError:
        print("ERRO: Credenciais de e-mail não configuradas.")
        try:
            st.error("Credenciais de e-mail não configuradas. Notificação não enviada.")
        except Exception:
            pass
        return False

    msg = MIMEMultipart()
    msg['Subject'] = assunto
    msg['From'] = remetente_user
    msg['To'] = destinatario_email
    msg.attach(MIMEText(corpo, 'html'))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {os.path.basename(attachment_path)}",
        )
        msg.attach(part)

    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(remetente_user, remetente_pass)
        server.sendmail(remetente_user, [destinatario_email], msg.as_string())
        server.quit()
        print(f"E-mail enviado com sucesso para {destinatario_email}")
        return True
    except Exception as e:
        print(f"Falha ao enviar e-mail: {e}")
        try:
            st.warning(f"Falha ao enviar notificação por e-mail: {e}")
        except Exception:
            pass
        return False
