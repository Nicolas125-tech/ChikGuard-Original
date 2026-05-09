import pytest
import logging
from src.alerts.providers import AlertProvider, build_alert_provider

def test_alert_provider_send(caplog):
    caplog.set_level(logging.INFO)

    settings = {"dummy": "setting"}
    provider = AlertProvider(settings)

    test_message = "Test alert message"
    result = provider.send(test_message)

    assert result is True

    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.INFO
    assert caplog.records[0].message == f"[ALERT] {test_message}"

def test_build_alert_provider():
    settings = {"dummy": "setting"}
    provider = build_alert_provider(settings)
    assert isinstance(provider, AlertProvider)
    assert provider.settings == settings
