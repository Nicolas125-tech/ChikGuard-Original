import pytest
import logging
from unittest.mock import patch, MagicMock
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
        timeout=5
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
        timeout=5
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
