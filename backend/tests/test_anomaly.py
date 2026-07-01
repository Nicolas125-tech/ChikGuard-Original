import pytest
from src.ai.anomaly import detect_multivariate_anomaly

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
