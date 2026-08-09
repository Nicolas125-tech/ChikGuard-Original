import sys
import importlib
from unittest import mock
import pytest
import random
from src.ai.anomaly import detect_multivariate_anomaly
import src.ai.anomaly

def test_detect_multivariate_anomaly_insufficient_data():
    """
    Test that detect_multivariate_anomaly returns an error when sensor_history has fewer than 20 points.
    """
    # Provide exactly 19 historical points to test the boundary condition
    sensor_history = [{"temp": 28, "hum": 60, "amm": 15, "cough": 10}] * 19
    current_state = {"temp": 28, "hum": 60, "amm": 15, "cough": 10}

    result = detect_multivariate_anomaly(sensor_history, current_state)

    # If scikit-learn is not installed, it returns a different error first.
    if result.get("error") == "scikit-learn is not installed in the environment.":
        pytest.skip("scikit-learn is not available in the environment")

    assert "error" in result
    assert result["error"] == "Insufficient historical data for Isolation Forest. Need at least 20 points."

def test_detect_multivariate_anomaly_sklearn_missing():
    """
    Test that detect_multivariate_anomaly handles missing sklearn properly.
    """
    # Save the original module to ensure it's still in sys.modules
    try:
        with mock.patch.dict(sys.modules, {'sklearn': None, 'sklearn.ensemble': None}):
            importlib.reload(src.ai.anomaly)

            sensor_history = [{"temp": 28, "hum": 60, "amm": 15, "cough": 10}] * 20
            current_state = {"temp": 28, "hum": 60, "amm": 15, "cough": 10}

            result = src.ai.anomaly.detect_multivariate_anomaly(sensor_history, current_state)

            assert "error" in result
            assert result["error"] == "scikit-learn is not installed in the environment."
    finally:
        # restore outside the mock context
        importlib.reload(src.ai.anomaly)

def test_detect_multivariate_anomaly_normal():
    """
    Test that detect_multivariate_anomaly correctly identifies a normal state.
    """
    random.seed(42)
    # Generate enough points with slight variation so variance is non-zero
    sensor_history = [
        {
            "temp": random.uniform(27.5, 28.5),
            "hum": random.uniform(59.5, 60.5),
            "amm": random.uniform(14.5, 15.5),
            "cough": random.uniform(9.5, 10.5)
        }
        for _ in range(500)
    ]
    current_state = {"temp": 28.0, "hum": 60.0, "amm": 15.0, "cough": 10.0}

    result = detect_multivariate_anomaly(sensor_history, current_state)

    if result.get("error") == "scikit-learn is not installed in the environment.":
        pytest.skip("scikit-learn is not available in the environment")

    assert "is_anomaly" in result
    assert result["is_anomaly"] is False
    assert result["contributions"] == {}
    assert "score" in result
    assert "confidence" in result

def test_detect_multivariate_anomaly_abnormal():
    """
    Test that detect_multivariate_anomaly correctly identifies an anomalous state.
    """
    random.seed(42)
    sensor_history = [
        {
            "temp": random.uniform(27.5, 28.5),
            "hum": random.uniform(59.5, 60.5),
            "amm": random.uniform(14.5, 15.5),
            "cough": random.uniform(9.5, 10.5)
        }
        for _ in range(500)
    ]
    # Completely anomalous state
    current_state = {"temp": 100.0, "hum": 10.0, "amm": 50.0, "cough": 50.0}

    result = detect_multivariate_anomaly(sensor_history, current_state)

    if result.get("error") == "scikit-learn is not installed in the environment.":
        pytest.skip("scikit-learn is not available in the environment")

    assert "is_anomaly" in result
    assert result["is_anomaly"] is True
    # The anomaly is obvious, features should appear in contributions
    assert "temp" in result["contributions"]
    assert "amm" in result["contributions"]
    assert "hum" in result["contributions"]
    assert "cough" in result["contributions"]
