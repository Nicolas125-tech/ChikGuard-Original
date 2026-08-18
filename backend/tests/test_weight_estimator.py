import pytest
from src.vision.weight_estimator import BiometricWeightEstimator

@pytest.fixture
def estimator():
    return BiometricWeightEstimator()

def test_estimate_bird_weight_chick_young(estimator):
    """Test weight estimation for young chicks"""
    box = [10, 10, 110, 110]
    frame_shape = (1080, 1920, 3)

    result = estimator.estimate_bird_weight(
        box=box,
        frame_shape=frame_shape,
        species="chick",
        batch_age_days=14
    )

    assert "weight_g" in result
    assert "age_baseline_g" in result
    assert "area_factor" in result
    assert "confidence" in result
    assert result["confidence"] == 0.84

def test_estimate_bird_weight_hen_adult(estimator):
    """Test weight estimation for adult hens"""
    box = [100, 100, 300, 300]
    frame_shape = (1080, 1920, 3)

    result = estimator.estimate_bird_weight(
        box=box,
        frame_shape=frame_shape,
        species="hen",
        batch_age_days=30
    )

    assert result["age_baseline_g"] == 2550.0

def test_estimate_bird_weight_limits(estimator):
    """Test physical weight limits (min/max bounds)"""
    # Test minimum bound (very small box, young chick)
    box = [0, 0, 1, 1]
    result = estimator.estimate_bird_weight(
        box=box,
        frame_shape=(1080, 1920, 3),
        species="chick",
        batch_age_days=1
    )
    assert result["weight_g"] >= 35.0

    # Test maximum bound (very large box, older hen)
    box = [0, 0, 1080, 1920]
    result = estimator.estimate_bird_weight(
        box=box,
        frame_shape=(1080, 1920, 3),
        species="hen",
        batch_age_days=100
    )
    assert result["weight_g"] <= 4500.0

def test_estimate_bird_weight_with_mask(estimator):
    """Test weight estimation when mask area is provided"""
    box = [10, 10, 110, 110]
    frame_shape = (1080, 1920, 3)

    result = estimator.estimate_bird_weight(
        box=box,
        frame_shape=frame_shape,
        species="chick",
        batch_age_days=14,
        mask_area_px=5000.0
    )

    assert result["confidence"] == 0.91

def test_estimate_flock_weight_empty(estimator):
    """Test flock weight estimation with empty detections"""
    result = estimator.estimate_flock_weight(
        detections=[],
        frame_shape=(1080, 1920, 3),
        batch_age_days=14
    )

    assert result["count"] == 0
    assert result["confidence"] == 0.50
    assert result["weights_sample"] == []
    assert result["avg_weight_g"] > 0

def test_estimate_flock_weight_with_detections(estimator):
    """Test flock weight estimation with multiple valid detections"""
    detections = [
        {"class_id": 14, "box": [10, 10, 50, 50], "species": "chick"},
        {"class_id": 14, "box": [20, 20, 60, 60], "species": "chick", "mask_area_px": 1500.0},
        {"class_id": 99, "box": [0,0,10,10]} # Should be ignored
    ]

    result = estimator.estimate_flock_weight(
        detections=detections,
        frame_shape=(1080, 1920, 3),
        batch_age_days=14
    )

    assert result["count"] == 2
    assert result["confidence"] == 0.93
    assert len(result["weights_sample"]) == 2
    assert result["avg_weight_g"] > 0
