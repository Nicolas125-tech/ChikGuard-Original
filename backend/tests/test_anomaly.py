import pytest
from unittest.mock import patch
from src.ai.anomaly import detect_multivariate_anomaly

def test_detect_anomaly_no_sklearn():
    with patch('src.ai.anomaly._SKLEARN_AVAILABLE', False):
        result = detect_multivariate_anomaly([{}], {})
        assert result == {"error": "scikit-learn is not installed in the environment."}

def test_detect_anomaly_insufficient_data():
    history = [{"temp": 28, "hum": 60, "amm": 15, "cough": 10}] * 19
    result = detect_multivariate_anomaly(history, {})
    assert "error" in result
    assert "Need at least 20 points" in result["error"]

def test_detect_anomaly_normal():
    # 50 points of normal data with slight variation so variance isn't exactly 0
    history = []
    import random
    random.seed(42)
    for i in range(50):
        history.append({
            "temp": 28 + random.uniform(-0.5, 0.5),
            "hum": 60 + random.uniform(-2, 2),
            "amm": 15 + random.uniform(-1, 1),
            "cough": 10 + random.uniform(-2, 2)
        })
    current_state = {"temp": 28, "hum": 60, "amm": 15, "cough": 10}

    result = detect_multivariate_anomaly(history, current_state)

    assert "error" not in result
    assert result["is_anomaly"] is False
    assert result["score"] > 0
    assert "confidence" in result

def test_detect_anomaly_is_anomaly():
    # 50 points of normal data
    history = []
    import random
    random.seed(42)
    for i in range(50):
        history.append({
            "temp": 28 + random.uniform(-0.5, 0.5),
            "hum": 60 + random.uniform(-2, 2),
            "amm": 15 + random.uniform(-1, 1),
            "cough": 10 + random.uniform(-2, 2)
        })
    # Current state has a huge spike
    current_state = {"temp": 40, "hum": 90, "amm": 150, "cough": 50}

    result = detect_multivariate_anomaly(history, current_state)
    assert "error" not in result
    assert result["is_anomaly"] is True
    assert result["score"] < 0
    assert "contributions" in result
    assert "amm" in result["contributions"]
    assert "temp" in result["contributions"]
    assert "cough" in result["contributions"]
