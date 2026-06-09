import logging
import os
import re
import smtplib
from email.mime.text import MIMEText
import requests

logger = logging.getLogger(__name__)


class AlertProvider:
    """
    Orquestrador central de alertas responsável por encaminhar notificações
    críticas para canais externos ativos (Telegram, Twilio, SMTP).
    """

    def __init__(self, settings):
        self.settings = settings

        # Inicializa configurações dos canais externos
        self._load_telegram_config(settings)
        self._load_twilio_config(settings)
        self._load_smtp_config(settings)

    def _load_telegram_config(self, settings):
        self.telegram_bot_token = getattr(settings, "telegram_bot_token", None) or os.getenv(
            "TELEGRAM_BOT_TOKEN"
        )
        self.telegram_chat_id = getattr(settings, "telegram_chat_id", None) or os.getenv(
            "TELEGRAM_CHAT_ID"
        )

    def _load_twilio_config(self, settings):
        self.twilio_account_sid = getattr(settings, "twilio_account_sid", None) or os.getenv(
            "TWILIO_ACCOUNT_SID"
        )
        self.twilio_auth_token = getattr(settings, "twilio_auth_token", None) or os.getenv(
            "TWILIO_AUTH_TOKEN"
        )
        self.twilio_from_number = getattr(settings, "twilio_from_number", None) or os.getenv(
            "TWILIO_FROM_NUMBER"
        )
        self.twilio_to_number = getattr(settings, "twilio_to_number", None) or os.getenv(
            "TWILIO_TO_NUMBER"
        )

    def _load_smtp_config(self, settings):
        self.smtp_server = getattr(settings, "smtp_server", None) or os.getenv("SMTP_SERVER")
        self.smtp_port = getattr(settings, "smtp_port", 587)
        self.smtp_user = getattr(settings, "smtp_user", None) or os.getenv("SMTP_USER")
        self.smtp_password = getattr(settings, "smtp_password", None) or os.getenv("SMTP_PASSWORD")
        self.smtp_to = getattr(settings, "smtp_to", None) or os.getenv("SMTP_TO")

    def send(self, message):
        """
        Dispara alertas para todos os canais ativamente configurados.
        Sempre loga a mensagem como fallback.
        """
        logger.info(f"[ALERT-TRIGGER] Iniciando disparo de alerta ativo: {message}")

        self._send_to_telegram(message)
        self._send_to_twilio(message)
        self._send_to_email(message)

        # Fallback de logs do sistema
        logger.info(f"[ALERT] {message}")
        return True

    def _send_to_telegram(self, message):
        """Envia o alerta para o grupo/canal configurado no Telegram."""
        if not (self.telegram_bot_token and self.telegram_chat_id):
            return

        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {"chat_id": self.telegram_chat_id, "text": f"🚨 [ChikGuard Alert]\n{message}"}
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200:
                logger.info("[ALERT] Notificação via Telegram enviada com sucesso.")
            else:
                logger.error(
                    f"[ALERT] Falha no Telegram (Status {response.status_code}): {response.text}"
                )
        except Exception as exc:
            logger.error(f"[ALERT] Erro de rede ao enviar alerta para o Telegram: {exc}")

    def _send_to_twilio(self, message):
        """Envia o alerta por SMS ou WhatsApp via serviço Twilio."""
        if not (
            self.twilio_account_sid
            and self.twilio_auth_token
            and self.twilio_from_number
            and self.twilio_to_number
        ):
            return

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}/Messages.json"

            # Formata os números de origem/destino garantindo o prefixo correto para WhatsApp
            from_number = self._normalize_twilio_number(self.twilio_from_number)
            to_number = self._normalize_twilio_number(self.twilio_to_number)

            payload = {"From": from_number, "To": to_number, "Body": f"🚨 [ChikGuard] {message}"}

            response = requests.post(
                url, data=payload, auth=(self.twilio_account_sid, self.twilio_auth_token), timeout=5
            )
            if response.status_code in {200, 201}:
                logger.info(f"[ALERT] Notificação via Twilio enviada para {to_number}.")
            else:
                logger.error(
                    f"[ALERT] Falha no Twilio (Status {response.status_code}): {response.text}"
                )
        except Exception as exc:
            logger.error(f"[ALERT] Erro ao enviar notificação via Twilio: {exc}")

    def _normalize_twilio_number(self, phone_number):
        """Padroniza strings de contato para envio via SMS ou WhatsApp do Twilio."""
        number = str(phone_number).strip()
        if "whatsapp" in number.lower() and not number.lower().startswith("whatsapp:"):
            # Corrige variações como whatsapp+55... -> whatsapp:+55...
            clean_digits = re.sub(r"[^\d+]", "", number)
            return f"whatsapp:{clean_digits}"
        return number

    def _send_to_email(self, message):
        """Dispara um e-mail de alerta clínico via SMTP."""
        if not (self.smtp_server and self.smtp_user and self.smtp_password and self.smtp_to):
            return

        try:
            email_msg = MIMEText(
                f"O sistema ChikGuard registrou uma ocorrência relevante:\n\n{message}"
            )
            email_msg["Subject"] = "🚨 Alerta Clínico - Sistema ChikGuard"
            email_msg["From"] = self.smtp_user
            email_msg["To"] = self.smtp_to

            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=5) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, [self.smtp_to], email_msg.as_string())

            logger.info(f"[ALERT] E-mail de contingência enviado para {self.smtp_to}.")
        except Exception as exc:
            logger.error(f"[ALERT] Erro ao disparar e-mail via SMTP: {exc}")


def build_alert_provider(settings):
    """Fábrica (Factory) para montagem e retorno do provedor de alertas."""
    return AlertProvider(settings)
