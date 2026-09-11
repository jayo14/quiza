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

    from_email = settings.smtp_from_email or settings.smtp_username
    from_name = settings.smtp_from_name
    expire_minutes = settings.password_reset_token_expire_minutes

    subject = "Reset your Quiza password"

    plain_text = (
        f"Hello,\n\n"
        f"We received a request to reset your Quiza account password.\n\n"
        f"Click the link below to choose a new password:\n\n"
        f"{reset_link}\n\n"
        f"If you did not request a password reset, you can safely ignore this email. "
        f"Your password will not change.\n\n"
        f"This link will expire in {expire_minutes} minutes.\n\n"
        f"Quiza Support\n"
        f"{from_email}\n"
    )

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reset your Quiza password</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f3ec;font-family:system-ui,'Segoe UI',Roboto,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f3ec;">
        <tr>
            <td align="center" style="padding:40px 20px;">
                <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background-color:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 10px 15px -3px rgba(0,0,0,0.1);border:1px solid #e5e4e7;">
                    <tr>
                        <td style="background-color:#aa3bff;padding:24px;text-align:center;">
                            <h1 style="color:#ffffff;margin:0;font-size:28px;letter-spacing:-0.5px;">Quiza</h1>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding:32px;text-align:center;">
                            <h2 style="color:#08060d;font-size:24px;margin-top:0;margin-bottom:16px;">Password Reset Request</h2>
                            <p style="font-size:16px;line-height:1.5;margin-bottom:24px;color:#374151;">Hello,</p>
                            <p style="font-size:16px;line-height:1.5;margin-bottom:24px;color:#374151;">We received a request to reset the password for your Quiza account. Click the button below to choose a new password.</p>
                            <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto 24px;">
                                <tr>
                                    <td style="background-color:#aa3bff;border-radius:4px;">
                                        <a href="{reset_link}" style="display:inline-block;padding:12px 24px;color:#ffffff;text-decoration:none;font-weight:500;font-size:16px;">Reset Password</a>
                                    </td>
                                </tr>
                            </table>
                            <p style="font-size:16px;line-height:1.5;margin-bottom:24px;color:#374151;">If you did not request a password reset, you can safely ignore this email. Your password will not change.</p>
                            <p style="font-size:14px;line-height:1.5;margin-bottom:0;color:#6b7280;">This link will expire in {expire_minutes} minutes.</p>
                        </td>
                    </tr>
                    <tr>
                        <td style="background-color:#f9f9f9;padding:20px;text-align:center;font-size:14px;color:#9ca3af;border-top:1px solid #e5e4e7;">
                            <p style="margin:0;">Quiza &copy; {settings.app_name}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_email}>"
    msg["To"] = to_email
    msg["Reply-To"] = from_email
    msg["List-Unsubscribe"] = f"<mailto:{from_email}?subject=unsubscribe>"
    msg["Precedence"] = "bulk"
    msg["X-Mailer"] = "Quiza Mailer"

    msg.attach(MIMEText(plain_text, "plain"))
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(from_email, [to_email], msg.as_string())
        logger.info(f"Password reset email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
