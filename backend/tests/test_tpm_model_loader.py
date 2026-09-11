import sys
from unittest.mock import MagicMock

# Mock libs that are not available in pytest env
sys.modules['cv2'] = MagicMock()
sys.modules['onnxruntime'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()
sys.modules['supervision'] = MagicMock()

from src.security.tpm_model_loader import TPMModelLoader


def test_tpm_model_loader_dev_mode(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("MOCK_TPM_KEY", "test_key_32_bytes_test_key_32_by")

    loader = TPMModelLoader()
    key = loader._unseal_key_from_tpm()

    assert key == b"test_key_32_bytes_test_key_32_by"
    assert len(key) == 32

def test_tpm_model_loader_dev_mode_no_env_key(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.delenv("MOCK_TPM_KEY", raising=False)

    loader = TPMModelLoader()
    key = loader._unseal_key_from_tpm()

    assert key == b"0123456789abcdef0123456789abcdef"
    assert len(key) == 32

def test_tpm_model_loader_dev_mode_short_key(monkeypatch):
    monkeypatch.setenv("DEV_MODE", "true")
    monkeypatch.setenv("MOCK_TPM_KEY", "short_key")

    loader = TPMModelLoader()
    key = loader._unseal_key_from_tpm()

    assert key == b"short_key00000000000000000000000"
    assert len(key) == 32
