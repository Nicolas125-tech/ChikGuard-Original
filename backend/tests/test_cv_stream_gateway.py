import sys
from unittest.mock import MagicMock, patch

# Mock heavy ML/CV modules that might not be available
sys.modules['cv2'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['ultralytics'] = MagicMock()
sys.modules['supervision'] = MagicMock()

import pytest
from src.application.cv_master.stream_gateway import HLSStreamGateway

def test_push_frame_ffmpeg_error():
    gateway = HLSStreamGateway()
    gateway.is_running = True
    gateway.ffmpeg_proc = MagicMock()

    # Mock the stdin.write to raise an exception
    gateway.ffmpeg_proc.stdin.write.side_effect = Exception("Simulated FFMPEG failure")

    # Mock a dummy frame with a tobytes method
    dummy_frame = MagicMock()
    dummy_frame.tobytes.return_value = b"fake_frame_bytes"

    # Verify that an exception writing to stdin calls stop_pipeline
    with patch.object(gateway, 'stop_pipeline') as mock_stop_pipeline:
        gateway.push_frame(dummy_frame)
        mock_stop_pipeline.assert_called_once()

def test_push_frame_happy_path():
    gateway = HLSStreamGateway()
    gateway.is_running = True
    gateway.ffmpeg_proc = MagicMock()

    # Mock a dummy frame with a tobytes method
    dummy_frame = MagicMock()
    dummy_frame.tobytes.return_value = b"fake_frame_bytes"

    # Verify that writing to stdin works and doesn't call stop_pipeline
    with patch.object(gateway, 'stop_pipeline') as mock_stop_pipeline:
        gateway.push_frame(dummy_frame)
        mock_stop_pipeline.assert_not_called()
        gateway.ffmpeg_proc.stdin.write.assert_called_once_with(b"fake_frame_bytes")

def test_push_frame_not_running():
    gateway = HLSStreamGateway()
    gateway.is_running = False
    gateway.ffmpeg_proc = MagicMock()

    # Mock a dummy frame
    dummy_frame = MagicMock()

    gateway.push_frame(dummy_frame)
    gateway.ffmpeg_proc.stdin.write.assert_not_called()

def test_push_frame_no_ffmpeg_proc():
    gateway = HLSStreamGateway()
    gateway.is_running = True
    gateway.ffmpeg_proc = None

    # Mock a dummy frame
    dummy_frame = MagicMock()

    # Should just return early and not raise an exception
    gateway.push_frame(dummy_frame)

# Clean up sys.modules after tests in this module
def teardown_module(module):
    for mod in ['cv2', 'torch', 'ultralytics', 'supervision']:
        if mod in sys.modules:
            del sys.modules[mod]
