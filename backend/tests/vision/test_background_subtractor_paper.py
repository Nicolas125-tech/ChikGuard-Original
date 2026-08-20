import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import cv2
import numpy as np
import pytest
from src.vision.background_subtractor_paper import PaperBackgroundSubtractor

def test_initialization():
    subtractor = PaperBackgroundSubtractor(threshold_val=100, morph_kernel_size=3)
    assert subtractor.threshold_val == 100
    assert subtractor.kernel.shape == (3, 3)
    assert subtractor.background_frame is None

def test_set_background():
    subtractor = PaperBackgroundSubtractor()
    # Create a dummy RGB background
    bg_frame = np.full((100, 100, 3), 50, dtype=np.uint8)
    subtractor.set_background(bg_frame)

    assert subtractor.background_frame is not None
    assert subtractor.background_frame.shape == (100, 100)
    # The image is converted to grayscale, so all channels are 50. Then negative = 255 - 50 = 205
    assert subtractor.background_frame[0, 0] == 205

def test_process_frame_empty():
    subtractor = PaperBackgroundSubtractor()
    res_none = subtractor.process_frame(None)
    assert res_none["blobs_count"] == 0

    res_empty = subtractor.process_frame(np.array([]))
    assert res_empty["blobs_count"] == 0

def test_process_frame_with_blob():
    subtractor = PaperBackgroundSubtractor(threshold_val=50, morph_kernel_size=3)

    # Background: dark gray (50)
    bg_frame = np.full((100, 100, 3), 50, dtype=np.uint8)
    subtractor.set_background(bg_frame)

    # Foreground: same dark gray, but with a bright white square in the middle representing a bird
    fg_frame = np.full((100, 100, 3), 50, dtype=np.uint8)
    cv2.rectangle(fg_frame, (40, 40), (60, 60), (255, 255, 255), -1)

    res = subtractor.process_frame(fg_frame)

    assert res["blobs_count"] == 1
    assert res["total_mask_area"] > 0
    assert res["mask"] is not None
    assert res["mask"].shape == (100, 100)

    # The center of the 40x40 to 60x60 square should be around (50, 50)
    cx, cy = res["blobs_centers"][0]
    assert 45 <= cx <= 55
    assert 45 <= cy <= 55

def test_process_frame_noise_filtered():
    subtractor = PaperBackgroundSubtractor(threshold_val=50, morph_kernel_size=3)

    bg_frame = np.full((100, 100, 3), 50, dtype=np.uint8)
    subtractor.set_background(bg_frame)

    # Foreground with small noise (area < 25)
    fg_frame = np.full((100, 100, 3), 50, dtype=np.uint8)
    cv2.rectangle(fg_frame, (10, 10), (12, 12), (255, 255, 255), -1) # Area ~ 9

    res = subtractor.process_frame(fg_frame)

    # Small noise should be filtered out because of area >= 25 condition in connectedComponentsWithStats
    assert res["blobs_count"] == 0
