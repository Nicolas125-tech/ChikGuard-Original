import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import os
import sys
import unittest.mock as mock

# Adjust sys.path to see src/ and backend
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from src.ai.spatial import detect_huddling


def test_detect_huddling_not_enough_birds():
    # Less than min_birds_per_cluster (8)
    points = [{"x": 10, "y": 10} for _ in range(5)]
    result = detect_huddling(points, min_birds_per_cluster=8)

    assert result.get("huddling_detected") is False
    assert result.get("clusters_found") == 0
    assert "Nao ha aves suficientes rastreadas" in result.get("msg", "")


def test_detect_huddling_no_clusters():
    # 10 widely spread points, eps=80, so they won't form a cluster
    points = [{"x": i * 100, "y": i * 100} for i in range(1, 11)]
    result = detect_huddling(points, eps_pixels=80, min_birds_per_cluster=8)

    assert result.get("huddling_detected") is False
    assert result.get("clusters_found") == 0
    assert result.get("density_score") == 0.0
    assert "Excelente Conforto Termico" in result.get("msg", "")


def test_detect_huddling_with_clusters():
    # 32 points total, 8 in a cluster, 24 widely spread.
    # 8/32 = 0.25 (25%), which is <= 0.25, so huddling_detected should be False
    points = [{"x": 10, "y": 10} for _ in range(8)]
    spread_points = [{"x": i * 1000, "y": i * 1000} for i in range(1, 25)]
    points.extend(spread_points)

    result = detect_huddling(points, eps_pixels=80, min_birds_per_cluster=8)

    assert result.get("huddling_detected") is False
    assert result.get("clusters_found") == 1
    assert result.get("density_score") == 25.0
    assert result.get("cluster_centers")[0]["bird_count"] == 8
    assert "Pequenos grupos isolados" in result.get("msg", "")


def test_detect_huddling_critical():
    # 10 points total, 8 in a cluster, 2 widely spread.
    # 8/10 = 0.80 (80%), which is > 0.25, so huddling_detected should be True
    points = [{"x": 10, "y": 10} for _ in range(8)]
    spread_points = [{"x": i * 1000, "y": i * 1000} for i in range(1, 3)]
    points.extend(spread_points)

    result = detect_huddling(points, eps_pixels=80, min_birds_per_cluster=8)

    assert result.get("huddling_detected") is True
    assert result.get("clusters_found") == 1
    assert result.get("density_score") == 80.0
    assert result.get("cluster_centers")[0]["bird_count"] == 8
    assert "ALERTA VERMELHO" in result.get("msg", "")


def test_sklearn_not_available():
    with mock.patch("src.ai.spatial._SKLEARN_AVAILABLE", False):
        result = detect_huddling([])
        assert "error" in result
        assert "scikit-learn is not installed" in result["error"]
