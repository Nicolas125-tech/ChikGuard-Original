from datetime import datetime
from src.ai.forecast import predict_slaughter_date

def test_predict_slaughter_date_insufficient_data():
    start_date = datetime(2023, 1, 1)

    # 0 items
    assert predict_slaughter_date([], start_date) is None

    # 1 item
    assert predict_slaughter_date([{"day": 1, "avg_weight": 50.0}], start_date) is None

    # 2 items
    weight_data = [
        {"day": 1, "avg_weight": 50.0},
        {"day": 2, "avg_weight": 100.0}
    ]
    result = predict_slaughter_date(weight_data, start_date)
    assert result is None

def test_predict_slaughter_date_normal_growth():
    start_date = datetime(2023, 1, 1)
    weight_data = [
        {"day": 1, "avg_weight": 50.0},
        {"day": 10, "avg_weight": 500.0},
        {"day": 20, "avg_weight": 1200.0},
        {"day": 30, "avg_weight": 2100.0}
    ]
    result = predict_slaughter_date(weight_data, start_date, target_weight=2800.0)
    assert result is not None
    assert result["target_date"] is not None
    assert result["target_day"] > 30
    assert result["target_weight"] == 2800.0
    assert len(result["equation_coeffs"]) == 3
    assert len(result["projections"]) > 0

def test_predict_slaughter_date_not_reached():
    start_date = datetime(2023, 1, 1)
    # Slow growth that won't reach 2800 in 90 days
    weight_data = [
        {"day": 1, "avg_weight": 50.0},
        {"day": 10, "avg_weight": 51.0},
        {"day": 20, "avg_weight": 52.0}
    ]
    result = predict_slaughter_date(weight_data, start_date, target_weight=2800.0)
    assert result is not None
    assert result["target_date"] is None
    assert result["target_day"] is None
    assert result["target_weight"] == 2800.0
    assert len(result["equation_coeffs"]) == 3
    assert len(result["projections"]) == 70  # 90 - 20 = 70 projections

def test_failure_to_reach_target_weight_in_90_days():
    start_date = datetime(2023, 1, 1)
    weight_data = [
        {"day": 10, "avg_weight": 190.0},
        {"day": 20, "avg_weight": 310.0},
        {"day": 40, "avg_weight": 490.0},
        {"day": 60, "avg_weight": 590.0}
    ]
    result = predict_slaughter_date(weight_data, start_date, target_weight=2800.0)
    assert result is not None
    assert result["target_date"] is None
    assert result["target_day"] is None
    assert result["target_weight"] == 2800.0
    assert len(result["equation_coeffs"]) == 3
    assert len(result["projections"]) > 0
    # Make sure we actually didn't reach the target weight within the projected timeframe
    max_weight_in_projections = max(p["estimated_weight_g"] for p in result["projections"])
    assert max_weight_in_projections < 2800.0
