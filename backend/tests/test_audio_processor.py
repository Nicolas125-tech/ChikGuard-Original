import sys
import unittest.mock as mock
import numpy as np
import pytest

from src.audio.audio_processor import compute_mel_spectrogram

def test_compute_mel_spectrogram_no_librosa():
    """Test fallback when librosa is not available."""
    import src.audio.audio_processor as audio_processor

    # Store the original librosa reference
    original_librosa = audio_processor.librosa

    try:
        # Mock it to None as if it wasn't installed
        audio_processor.librosa = None

        audio_buffer = np.zeros(16000)
        result = audio_processor.compute_mel_spectrogram(
            audio_buffer,
            sr=16000,
            n_mels=64,
            n_fft=1024,
            hop_length=512
        )

        # Check shape
        assert result.shape == (64, int(16000 / 512))
        assert np.all(result == 0)
    finally:
        # Restore the original
        audio_processor.librosa = original_librosa

def test_compute_mel_spectrogram_with_librosa():
    """Test standard behavior when librosa is available."""
    import src.audio.audio_processor as audio_processor

    if audio_processor.librosa is None:
        pytest.skip("librosa is not installed, skipping test.")

    audio_buffer = np.zeros(16000)
    # Put a small signal so it's not completely zero
    audio_buffer[0:1000] = 0.5

    result = audio_processor.compute_mel_spectrogram(
        audio_buffer,
        sr=16000,
        n_mels=64,
        n_fft=1024,
        hop_length=512
    )

    # Check shape
    assert result.shape == (64, int(16000 / 512) + 1)

    # It should not be all zeros since we added a signal and librosa computes log_mel_spec
    assert not np.all(result == 0)

def test_compute_mel_spectrogram_empty_buffer():
    """Test with an empty buffer or all zeros buffer."""
    import src.audio.audio_processor as audio_processor

    if audio_processor.librosa is None:
        pytest.skip("librosa is not installed, skipping test.")

    audio_buffer = np.zeros(16000)

    result = audio_processor.compute_mel_spectrogram(
        audio_buffer,
        sr=16000,
        n_mels=64,
        n_fft=1024,
        hop_length=512
    )

    assert result.shape == (64, int(16000 / 512) + 1)
