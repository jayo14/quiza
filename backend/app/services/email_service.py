import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

def send_password_reset_email(to_email: str, reset_link: str) -> None:
    if not settings.smtp_server or not settings.smtp_username or not settings.smtp_password:
        logger.warning("SMTP settings not configured. Cannot send password reset email.")
        return
