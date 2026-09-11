import pytest
import sys
from unittest.mock import MagicMock

sys.modules['onnxruntime'] = MagicMock()
sys.modules['cryptography'] = MagicMock()
sys.modules['cryptography.hazmat'] = MagicMock()
sys.modules['cryptography.hazmat.primitives'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.ciphers'] = MagicMock()
sys.modules['cryptography.hazmat.primitives.ciphers.aead'] = MagicMock()

from src.security.tpm_model_loader import TPMModelLoader

def test_valid_tpm_handle_address():
    # Should not raise ValueError
    loader = TPMModelLoader("0x81000000")
    assert loader.tpm_handle_address == "0x81000000"

    loader2 = TPMModelLoader("0x1234abcd")
    assert loader2.tpm_handle_address == "0x1234abcd"

def test_invalid_tpm_handle_address():
    with pytest.raises(ValueError, match="Invalid TPM handle address format."):
        TPMModelLoader("0x81000000; rm -rf /")

    with pytest.raises(ValueError, match="Invalid TPM handle address format."):
        TPMModelLoader("81000000")

    with pytest.raises(ValueError, match="Invalid TPM handle address format."):
        TPMModelLoader("0xg")
