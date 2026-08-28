import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import numpy as np
import pytest
from src.domain.vision.radial_light_corrector import RadialBrooderLightCorrector

def test_correct_intensity_empty_frame():
    corrector = RadialBrooderLightCorrector()
    assert corrector.correct_intensity(None) is None
    empty_frame = np.array([])
    np.testing.assert_array_equal(corrector.correct_intensity(empty_frame), empty_frame)

def test_correct_intensity_basic():
    corrector = RadialBrooderLightCorrector(r_min=10, r_max=20, max_attenuation=0.4)
    # Create a simple synthetic image, all white
    frame = np.full((50, 50, 3), 255, dtype=np.uint8)

    corrected = corrector.correct_intensity(frame)

    assert corrected.shape == frame.shape
    assert corrected.dtype == np.uint8

    # Center (25, 25) should be attenuated by 40% (since r_min=10, max_attenuation=0.4)
    # The actual algorithm applies attenuation_mask directly to BGR channels
    # 255 * (1 - 0.4) = 153
    assert corrected[25, 25, 0] == 153
    assert corrected[25, 25, 1] == 153
    assert corrected[25, 25, 2] == 153

    # Outside radius (0, 0) should not be attenuated
    assert corrected[0, 0, 0] == 255

def test_correct_intensity_custom_center():
    corrector = RadialBrooderLightCorrector(center_xy=(10, 10), r_min=5, r_max=15, max_attenuation=0.5)
    frame = np.full((30, 30, 3), 200, dtype=np.uint8)

    corrected = corrector.correct_intensity(frame)

    # center is at (10, 10), it should be fully attenuated 200 * (1 - 0.5) = 100
    assert corrected[10, 10, 0] == 100
    # outside radius (25, 25) should not be attenuated
    assert corrected[25, 25, 0] == 200

def test_bgr_to_hsi():
    corrector = RadialBrooderLightCorrector()
    frame = np.full((10, 10, 3), 100, dtype=np.uint8)

    h, s, i = corrector.bgr_to_hsi(frame)
    assert h.shape == (10, 10)
    assert s.shape == (10, 10)
    assert i.shape == (10, 10)

    np.testing.assert_allclose(i, 100/255.0, atol=1e-3)
