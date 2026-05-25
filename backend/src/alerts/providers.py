import logging
import os
import smtplib
from email.mime.text import MIMEText
import requests

logger = logging.getLogger(__name__)

class AlertProvider:
    def __init__(self, settings):
        self.settings = settings
        # We can extract values from Settings class instance or direct dict/environment fallback
        self.telegram_bot_token = getattr(settings, 'telegram_bot_token', None) or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = getattr(settings, 'telegram_chat_id', None) or os.getenv("TELEGRAM_CHAT_ID")
        
        self.twilio_account_sid = getattr(settings, 'twilio_account_sid', None) or os.getenv("TWILIO_ACCOUNT_SID")
        self.twilio_auth_token = getattr(settings, 'twilio_auth_token', None) or os.getenv("TWILIO_AUTH_TOKEN")
        self.twilio_from_number = getattr(settings, 'twilio_from_number', None) or os.getenv("TWILIO_FROM_NUMBER")
        self.twilio_to_number = getattr(settings, 'twilio_to_number', None) or os.getenv("TWILIO_TO_NUMBER")

        self.smtp_server = getattr(settings, 'smtp_server', None) or os.getenv("SMTP_SERVER")
        self.smtp_port = getattr(settings, 'smtp_port', 587)
        self.smtp_user = getattr(settings, 'smtp_user', None) or os.getenv("SMTP_PASSWORD")
        self.smtp_password = getattr(settings, 'smtp_password', None) or os.getenv("SMTP_PASSWORD")
        self.smtp_to = getattr(settings, 'smtp_to', None) or os.getenv("SMTP_TO")

    def send(self, message):
        """
        Sends an alert message using all configured channels: Telegram, Twilio, or SMTP.
        Falls back to logging to standard output.
        """
        logger.info(f"[ALERT-TRIGGER] Initiating active alert: {message}")
        sent_any = False

        # 1. Send via Telegram Bot API
        if self.telegram_bot_token and self.telegram_chat_id:
            try:
                url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
                payload = {
                    "chat_id": self.telegram_chat_id,
                    "text": f"🚨 [ChikGuard Alert]\n{message}"
                }
                r = requests.post(url, json=payload, timeout=5)
                if r.status_code == 200:
                    logger.info("[ALERT] Message sent successfully via Telegram.")
                    sent_any = True
                else:
                    logger.error(f"[ALERT] Telegram sending failed with status {r.status_code}: {r.text}")
            except Exception as e:
                logger.error(f"[ALERT] Error sending Telegram alert: {e}")

        # 2. Send via Twilio (SMS or WhatsApp)
        if self.twilio_account_sid and self.twilio_auth_token and self.twilio_from_number and self.twilio_to_number:
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"
                
                # Check if this is a WhatsApp or SMS number
                from_num = self.twilio_from_number
                to_num = self.twilio_to_number
                if not from_num.startswith("whatsapp:") and "whatsapp" in from_num.lower():
                    from_num = f"whatsapp:{from_num.replace('whatsapp:', '')}"
                if not to_num.startswith("whatsapp:") and "whatsapp" in to_num.lower():
                    to_num = f"whatsapp:{to_num.replace('whatsapp:', '')}"

                data = {
                    "From": from_num,
                    "To": to_num,
                    "Body": f"🚨 [ChikGuard] {message}"
                }
                
                r = requests.post(
                    url, 
                    data=data, 
                    auth=(self.twilio_account_sid, self.twilio_auth_token), 
                    timeout=5
                )
                if r.status_code in {200, 201}:
                    logger.info(f"[ALERT] Message sent successfully via Twilio to {to_num}.")
                    sent_any = True
                else:
                    logger.error(f"[ALERT] Twilio sending failed with status {r.status_code}: {r.text}")
            except Exception as e:
                logger.error(f"[ALERT] Error sending Twilio alert: {e}")

        # 3. Send via SMTP Email
        if self.smtp_server and self.smtp_user and self.smtp_password and self.smtp_to:
            try:
                msg = MIMEText(f"ChikGuard detectou um alerta relevante:\n\n{message}")
                msg["Subject"] = "🚨 Alerta do Sistema ChikGuard"
                msg["From"] = self.smtp_user
                msg["To"] = self.smtp_to

                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=5) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.sendmail(self.smtp_user, [self.smtp_to], msg.as_string())
                logger.info(f"[ALERT] Email alert sent successfully to {self.smtp_to}.")
                sent_any = True
            except Exception as e:
                logger.error(f"[ALERT] Error sending SMTP email alert: {e}")

        # Standard logging fallback
        logger.info(f"[ALERT] {message}")
        return True

def build_alert_provider(settings):
    """
    Factory function to build the alert provider.
    """
    return AlertProvider(settings)
