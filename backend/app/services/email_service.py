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

    subject = "Reset your Quiza password"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: system-ui, 'Segoe UI', Roboto, sans-serif;
                background-color: #f4f3ec;
                color: #6b6375;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 40px auto;
                background-color: #ffffff;
                border-radius: 8px;
                overflow: hidden;
                box-shadow: rgba(0, 0, 0, 0.1) 0 10px 15px -3px, rgba(0, 0, 0, 0.05) 0 4px 6px -2px;
                border: 1px solid #e5e4e7;
            }}
            .header {{
                background-color: #aa3bff;
                padding: 24px;
                text-align: center;
            }}
            .header h1 {{
                color: #ffffff;
                margin: 0;
                font-size: 28px;
                letter-spacing: -0.5px;
            }}
            .content {{
                padding: 32px;
                text-align: center;
            }}
            .content h2 {{
                color: #08060d;
                font-size: 24px;
                margin-top: 0;
                margin-bottom: 16px;
            }}
            .content p {{
                font-size: 16px;
                line-height: 1.5;
                margin-bottom: 24px;
            }}
            .btn {{
                display: inline-block;
                background-color: #aa3bff;
                color: #ffffff !important;
                text-decoration: none;
                padding: 12px 24px;
                border-radius: 4px;
                font-weight: 500;
                font-size: 16px;
                margin-bottom: 24px;
            }}
            .footer {{
                background-color: #f9f9f9;
                padding: 20px;
                text-align: center;
                font-size: 14px;
                color: #9ca3af;
                border-top: 1px solid #e5e4e7;
            }}
            .footer a {{
                color: #aa3bff;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Quiza</h1>
            </div>
            <div class="content">
                <h2>Password Reset Request</h2>
                <p>Hello,</p>
                <p>We received a request to reset your password for your Quiza account. Click the button below to choose a new password.</p>
                <a href="{reset_link}" class="btn">Reset Password</a>
                <p>If you did not request a password reset, you can safely ignore this email. Your password will not change.</p>
                <p>This link will expire in {settings.password_reset_token_expire_minutes} minutes.</p>
            </div>
            <div class="footer">
                <p>Quiza &copy; {settings.app_name}</p>
            </div>
        </div>
    </body>
    </html>
    """
