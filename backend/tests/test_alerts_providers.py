import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import logging
import os
from unittest.mock import MagicMock, patch

from src.alerts.providers import AlertProvider, build_alert_provider


def test_alert_provider_send_default(caplog):
    caplog.set_level(logging.INFO)

    # Empty settings should just fallback to stdout logging
    settings = MagicMock()
    # Mocking standard settings attributes as None
    settings.telegram_bot_token = None
    settings.telegram_chat_id = None
    settings.twilio_account_sid = None
    settings.twilio_auth_token = None
    settings.twilio_from_number = None
    settings.twilio_to_number = None
    settings.smtp_server = None
    settings.smtp_user = None
    settings.smtp_password = None
    settings.smtp_to = None

    provider = AlertProvider(settings)
    test_message = "Test alert message"
    result = provider.send(test_message)

    assert result is True

    # Should log trigger initiation and final fallback
    log_messages = [record.message for record in caplog.records]
    assert any("[ALERT-TRIGGER] Iniciando disparo de alerta ativo" in msg for msg in log_messages)
    assert any(f"[ALERT] {test_message}" in msg for msg in log_messages)


@patch("requests.post")
def test_alert_provider_send_telegram(mock_post, caplog):
    caplog.set_level(logging.INFO)

    settings = MagicMock()
    settings.telegram_bot_token = "fake_token"
    settings.telegram_chat_id = "fake_chat_id"
    settings.twilio_account_sid = None
    settings.smtp_server = None

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    provider = AlertProvider(settings)
    result = provider.send("Telegram Test Alert")

    assert result is True
    mock_post.assert_called_once_with(
        "https://api.telegram.org/botfake_token/sendMessage",
        json={"chat_id": "fake_chat_id", "text": "🚨 [ChikGuard Alert]\nTelegram Test Alert"},
        timeout=5,
    )

    log_messages = [record.message for record in caplog.records]
    assert any("Notificação via Telegram enviada com sucesso." in msg for msg in log_messages)


@patch("requests.post")
def test_alert_provider_send_twilio_sms(mock_post, caplog):
    caplog.set_level(logging.INFO)

    settings = MagicMock()
    settings.telegram_bot_token = None
    settings.twilio_account_sid = "AC_sid"
    settings.twilio_auth_token = "auth_token"
    settings.twilio_from_number = "+123456"
    settings.twilio_to_number = "+654321"
    settings.smtp_server = None

    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_post.return_value = mock_response

    provider = AlertProvider(settings)
    result = provider.send("Twilio Test Alert")

    assert result is True
    mock_post.assert_called_once_with(
        "https://api.twilio.com/2010-04-01/Accounts/AC_sid/Messages.json",
        data={"From": "+123456", "To": "+654321", "Body": "🚨 [ChikGuard] Twilio Test Alert"},
        auth=("AC_sid", "auth_token"),
        timeout=5,
    )

    log_messages = [record.message for record in caplog.records]
    assert any("Notificação via Twilio enviada" in msg for msg in log_messages)


@patch("smtplib.SMTP")
def test_alert_provider_send_email(mock_smtp_class, caplog):
    caplog.set_level(logging.INFO)

    settings = MagicMock()
    settings.telegram_bot_token = None
    settings.twilio_account_sid = None
    settings.smtp_server = "smtp.example.com"
    settings.smtp_port = 587
    settings.smtp_user = "user@example.com"
    settings.smtp_password = "password123"
    settings.smtp_to = "dest@example.com"

    mock_smtp_instance = MagicMock()
    mock_smtp_class.return_value.__enter__.return_value = mock_smtp_instance

    provider = AlertProvider(settings)
    result = provider.send("Email Test Alert")

    assert result is True
    mock_smtp_instance.starttls.assert_called_once()
    mock_smtp_instance.login.assert_called_once_with("user@example.com", "password123")
    mock_smtp_instance.sendmail.assert_called_once()

    log_messages = [record.message for record in caplog.records]
    assert any("E-mail de contingência enviado" in msg for msg in log_messages)


def test_build_alert_provider():
    settings = MagicMock()
    provider = build_alert_provider(settings)
    assert isinstance(provider, AlertProvider)

def test_alert_provider_init_with_settings():
    settings = MagicMock()
    settings.telegram_bot_token = "tel_token"
    settings.telegram_chat_id = "tel_chat"
    settings.twilio_account_sid = "tw_sid"
    settings.twilio_auth_token = "tw_auth"
    settings.twilio_from_number = "tw_from"
    settings.twilio_to_number = "tw_to"
    settings.smtp_server = "smtp_serv"
    settings.smtp_port = 465
    settings.smtp_user = "smtp_usr"
    settings.smtp_password = "smtp_pwd"
    settings.smtp_to = "smtp_dest"

    provider = AlertProvider(settings)

    assert provider.telegram_bot_token == "tel_token"
    assert provider.telegram_chat_id == "tel_chat"
    assert provider.twilio_account_sid == "tw_sid"
    assert provider.twilio_auth_token == "tw_auth"
    assert provider.twilio_from_number == "tw_from"
    assert provider.twilio_to_number == "tw_to"
    assert provider.smtp_server == "smtp_serv"
    assert provider.smtp_port == 465
    assert provider.smtp_user == "smtp_usr"
    assert provider.smtp_password == "smtp_pwd"
    assert provider.smtp_to == "smtp_dest"

@patch.dict(os.environ, {
    "TELEGRAM_BOT_TOKEN": "env_tel_token",
    "TELEGRAM_CHAT_ID": "env_tel_chat",
    "TWILIO_ACCOUNT_SID": "env_tw_sid",
    "TWILIO_AUTH_TOKEN": "env_tw_auth",
    "TWILIO_FROM_NUMBER": "env_tw_from",
    "TWILIO_TO_NUMBER": "env_tw_to",
    "SMTP_SERVER": "env_smtp_serv",
    "SMTP_USER": "env_smtp_usr",
    "SMTP_PASSWORD": "env_smtp_pwd",
    "SMTP_TO": "env_smtp_dest"
})
def test_alert_provider_init_with_env_vars():
    class DummySettings:
        pass

    settings = DummySettings()

    provider = AlertProvider(settings)

    assert provider.telegram_bot_token == "env_tel_token"
    assert provider.telegram_chat_id == "env_tel_chat"
    assert provider.twilio_account_sid == "env_tw_sid"
    assert provider.twilio_auth_token == "env_tw_auth"
    assert provider.twilio_from_number == "env_tw_from"
    assert provider.twilio_to_number == "env_tw_to"
    assert provider.smtp_server == "env_smtp_serv"
    assert provider.smtp_port == 587
    assert provider.smtp_user == "env_smtp_usr"
    assert provider.smtp_password == "env_smtp_pwd"
    assert provider.smtp_to == "env_smtp_dest"

@patch("requests.post")
def test_alert_provider_send_telegram_error(mock_post, caplog):
    caplog.set_level(logging.ERROR)

    settings = MagicMock()
    settings.telegram_bot_token = "secret_bot_token_123"
    settings.telegram_chat_id = "fake_chat_id"
    settings.twilio_account_sid = None
    settings.smtp_server = None

    # Simulate an exception that contains the token to test sanitization
    mock_post.side_effect = Exception("Connection error with token secret_bot_token_123")

    provider = AlertProvider(settings)
    result = provider.send("Telegram Test Alert Error")

    assert result is True

    log_messages = [record.message for record in caplog.records]
    assert any("Erro de rede ao enviar alerta para o Telegram: Connection error with token ***" in msg for msg in log_messages)
    assert not any("secret_bot_token_123" in msg for msg in log_messages)

@patch("requests.post")
def test_alert_provider_send_twilio_error(mock_post, caplog):
    caplog.set_level(logging.ERROR)

    settings = MagicMock()
    settings.telegram_bot_token = None
    settings.twilio_account_sid = "AC_sid"
    settings.twilio_auth_token = "auth_token"
    settings.twilio_from_number = "+123456"
    settings.twilio_to_number = "+654321"
    settings.smtp_server = None

    mock_post.side_effect = Exception("Twilio connection error")

    provider = AlertProvider(settings)
    result = provider.send("Twilio Test Alert Error")

    assert result is True

    log_messages = [record.message for record in caplog.records]
    assert any("Erro ao enviar notificação via Twilio: Twilio connection error" in msg for msg in log_messages)
