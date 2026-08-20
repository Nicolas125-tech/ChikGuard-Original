import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import pytest
from src.vision.weight_estimator import BiometricWeightEstimator

def test_weight_estimator_clamping():
    estimator = BiometricWeightEstimator()
    frame_shape = (1080, 1920, 3)

    # Test lower bound (should clamp to 35.0g)
    # Using tiny area to force weight down
    result_tiny = estimator.estimate_bird_weight(
        box=[0, 0, 1, 1],
        frame_shape=frame_shape,
        species="chick",
        batch_age_days=1,
        mask_area_px=1.0
    )
    assert result_tiny["weight_g"] == 35.0

    # Test upper bound (should clamp to 4500.0g)
    # Using huge age and area to force weight up
    result_huge = estimator.estimate_bird_weight(
        box=[0, 0, 1080, 1920],
        frame_shape=frame_shape,
        species="hen",
        batch_age_days=100,
        mask_area_px=1080*1920
    )
    assert result_huge["weight_g"] == 4500.0

    # Test normal range (should not clamp)
    # Age 14 days, normal area
    result_normal = estimator.estimate_bird_weight(
        box=[100, 100, 200, 200], # 100x100 = 10000 px area
        frame_shape=frame_shape,
        species="chick",
        batch_age_days=14,
        mask_area_px=10000.0
    )
    assert 35.0 < result_normal["weight_g"] < 4500.0

def test_estimate_flock_weight_empty_detections():
    estimator = BiometricWeightEstimator()
    frame_shape = (1080, 1920, 3)

    # Test fallback to baseline when no detections
    result_empty = estimator.estimate_flock_weight(
        detections=[],
        frame_shape=frame_shape,
        batch_age_days=14
    )
    assert result_empty["count"] == 0
    assert result_empty["confidence"] == 0.50
    assert "avg_weight_g" in result_empty
    assert result_empty["weights_sample"] == []

def test_estimate_flock_weight_empty_detections_old_hen():
    estimator = BiometricWeightEstimator()
    frame_shape = (1080, 1920, 3)

    # Test fallback to baseline when no detections for older birds
    result_empty = estimator.estimate_flock_weight(
        detections=[],
        frame_shape=frame_shape,
        batch_age_days=25
    )
    assert result_empty["count"] == 0
    # Baseline for hen at 25 days: 1500.0 + 25 * 35.0 = 2375.0
    assert result_empty["avg_weight_g"] == 2375.0

def test_estimate_flock_weight_with_valid_detections():
    estimator = BiometricWeightEstimator()
    frame_shape = (1080, 1920, 3)

    # Simulate some detections
    detections = [
        {"class_id": 14, "species": "chick", "box": [100, 100, 200, 200], "mask_area_px": 10000.0},
        {"class_id": 14, "species": "chick", "box": [300, 300, 400, 400], "mask_area_px": 12000.0}
    ]

    result = estimator.estimate_flock_weight(
        detections=detections,
        frame_shape=frame_shape,
        batch_age_days=14
    )

    assert result["count"] == 2
    assert result["confidence"] == 0.93
    assert result["avg_weight_g"] > 0
    assert len(result["weights_sample"]) == 2

def test_zero_and_negative_age():
    estimator = BiometricWeightEstimator()
    frame_shape = (1080, 1920, 3)

    result_zero = estimator.estimate_bird_weight(
        box=[100, 100, 200, 200],
        frame_shape=frame_shape,
        species="chick",
        batch_age_days=0,
        mask_area_px=10000.0
    )
    assert result_zero["weight_g"] >= 35.0

    result_negative = estimator.estimate_bird_weight(
        box=[100, 100, 200, 200],
        frame_shape=frame_shape,
        species="chick",
        batch_age_days=-5,
        mask_area_px=10000.0
    )
    assert result_negative["weight_g"] >= 35.0

def test_invalid_box_coordinates():
    estimator = BiometricWeightEstimator()
    frame_shape = (1080, 1920, 3)

    result_inverted_box = estimator.estimate_bird_weight(
        box=[200, 200, 100, 100],  # Inverted x1>x2, y1>y2
        frame_shape=frame_shape,
        species="chick",
        batch_age_days=14,
        mask_area_px=0.0 # Force calculation from box
    )
    assert result_inverted_box["weight_g"] > 0
    assert result_inverted_box["confidence"] == 0.84 # No mask

def test_zero_frame_area():
    estimator = BiometricWeightEstimator()
    frame_shape = (0, 0, 3) # Should handle gracefully

    result = estimator.estimate_bird_weight(
        box=[10, 10, 20, 20],
        frame_shape=frame_shape,
        species="chick",
        batch_age_days=14,
        mask_area_px=100.0
    )
    assert result["weight_g"] > 0

def test_estimate_bird_weight_extreme_box():
    estimator = BiometricWeightEstimator()
    frame_shape = (1080, 1920, 3)

    # Test an extremely large box (exceeding frame)
    result_extreme = estimator.estimate_bird_weight(
        box=[-100, -100, 3000, 3000],
        frame_shape=frame_shape,
        species="hen",
        batch_age_days=50,
        mask_area_px=0.0
    )
    assert result_extreme["weight_g"] > 0
    assert result_extreme["weight_g"] <= 4500.0

def test_estimate_bird_weight_hen_growth():
    estimator = BiometricWeightEstimator()
    frame_shape = (1080, 1920, 3)

    result_hen = estimator.estimate_bird_weight(
        box=[100, 100, 200, 200],
        frame_shape=frame_shape,
        species="hen",
        batch_age_days=25,
        mask_area_px=10000.0
    )
    # Baseline for hen at 25 days: 1500.0 + 25 * 35.0 = 2375.0
    assert result_hen["age_baseline_g"] == 2375.0

def test_estimate_bird_weight_old_chick():
    estimator = BiometricWeightEstimator()
    frame_shape = (1080, 1920, 3)

    result_old_chick = estimator.estimate_bird_weight(
        box=[100, 100, 200, 200],
        frame_shape=frame_shape,
        species="chick",
        batch_age_days=30,  # > 21, but species is chick
        mask_area_px=10000.0
    )
    # Baseline for chick at 30 days: 42.0 * (30 ^ 1.15) ≈ 2098.6
    assert round(result_old_chick["age_baseline_g"], 1) == 2098.6

def test_estimate_flock_weight_mixed_species_and_classes():
    estimator = BiometricWeightEstimator()
    frame_shape = (1080, 1920, 3)

    detections = [
        {"class_id": 14, "species": "chick", "box": [10, 10, 20, 20]}, # valid
        {"class_id": 14, "species": "hen", "box": [30, 30, 40, 40]},   # valid
        {"class_id": 0, "species": "person", "box": [50, 50, 60, 60]}, # invalid
        {"class_id": 1, "species": "bird", "box": [70, 70, 80, 80]},   # valid
        {"class_id": 14, "box": [90, 90, 100, 100]} # valid, default species chick
    ]

    result = estimator.estimate_flock_weight(
        detections=detections,
        frame_shape=frame_shape,
        batch_age_days=14
    )

    assert result["count"] == 4
    assert len(result["weights_sample"]) == 4

def test_estimate_flock_weight_large_sample():
    estimator = BiometricWeightEstimator()
    frame_shape = (1080, 1920, 3)

    detections = [
        {"class_id": 14, "species": "chick", "box": [10, 10, 20, 20]} for _ in range(15)
    ]

    result = estimator.estimate_flock_weight(
        detections=detections,
        frame_shape=frame_shape,
        batch_age_days=14
    )

    assert result["count"] == 15
    assert len(result["weights_sample"]) == 10 # Sample is capped at 10
