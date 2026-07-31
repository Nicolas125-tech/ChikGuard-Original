import os
import sys
import numpy as np
import pytest
from datetime import datetime, timedelta

# Adjust path to see src/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from src.vision.gait_analyzer import GaitAnalyzer
from src.vision.lameness_detector import LamenessDetector

def test_dynamic_skeleton_detection_and_hock_angles():
    analyzer = GaitAnalyzer(history_len=20)
    base_time = datetime.utcnow()

    # 1. Test ChikGuard-11 skeleton format
    # Generate 15 frames for ChikGuard-11
    # Hip (6), Knees (7, 8), Feet (9, 10)
    for i in range(15):
        kps_11 = [[0.0, 0.0, 1.0]] * 11
        # Hip center at [100, 100]
        kps_11[6] = [100.0, 100.0, 0.9]
        
        # Left leg: Knee [100, 110], Foot [100, 120] -> angle is 180 degrees (straight line)
        kps_11[7] = [100.0, 110.0, 0.9]
        kps_11[9] = [100.0, 120.0, 0.9]
        
        # Right leg: Knee [120, 100], Foot [120, 110] -> angle is 90 degrees (right-angle bend)
        kps_11[8] = [120.0, 100.0, 0.9]
        kps_11[10] = [120.0, 110.0, 0.9]
        
        res = analyzer.update_track(
            track_id=10, 
            keypoints=kps_11, 
            timestamp=base_time + timedelta(seconds=i * 0.1)
        )
    
    assert res["status"] == "ANALYZED"
    assert res["skeletal_format_detected"] == "ChikGuard-11"
    assert np.isclose(res["avg_hock_angle_left"], 180.0, atol=1.0)
    assert np.isclose(res["avg_hock_angle_right"], 90.0, atol=1.0)
    assert res["avg_hock_angle_combined"] == pytest.approx(135.0, abs=1.0)


def test_coco_17_skeleton_and_unilateral_asymmetry():
    analyzer = GaitAnalyzer(history_len=20)
    base_time = datetime.utcnow()

    # 2. Test COCO-17 skeleton format
    # Hip (11/12), Knees (13/14), Ankles (15/16)
    for i in range(15):
        kps_17 = [[0.0, 0.0, 1.0]] * 17
        # Hips
        kps_17[11] = [95.0, 100.0, 0.9]
        kps_17[12] = [105.0, 100.0, 0.9]
        
        # Left leg (straight line): Knee [95, 110], Ankle [95, 120] -> angle ~ 180
        kps_17[13] = [95.0, 110.0, 0.9]
        kps_17[15] = [95.0, 120.0, 0.9]
        
        # Right leg (severely bent/abnormal): Knee [120, 100], Ankle [120, 110] -> angle ~ 90 (using hip R 105,100)
        # Knee to Hip R: [105, 100] - [120, 100] = [-15, 0]. Knee to Ankle: [120, 110] - [120, 100] = [0, 10]. Angle = 90.
        kps_17[14] = [120.0, 100.0, 0.9]
        kps_17[16] = [120.0, 110.0, 0.9]
        
        res = analyzer.update_track(
            track_id=20, 
            keypoints=kps_17, 
            timestamp=base_time + timedelta(seconds=i * 0.1)
        )
        
    assert res["status"] == "ANALYZED"
    assert res["skeletal_format_detected"] == "COCO-17"
    assert np.isclose(res["avg_hock_angle_left"], 180.0, atol=1.0)
    assert np.isclose(res["avg_hock_angle_right"], 90.0, atol=1.0)
    # The hock angles difference is 90 degrees (> 20), which triggers asymmetry alert
    assert res["kestin_gait_score"] >= 2  # abnormal gait score


def test_lateral_sway_and_ref_size():
    analyzer = GaitAnalyzer(history_len=20)
    base_time = datetime.utcnow()

    # Generate walking with substantial lateral sway (zig-zagging on X axis while moving on Y axis)
    for i in range(15):
        kps = [[0.0, 0.0, 1.0]] * 11
        # Neck moves forward in Y, but swings heavily in X
        neck_x = 100.0 + (15.0 if i % 2 == 0 else -15.0)
        neck_y = 100.0 + i * 10.0
        kps[3] = [neck_x, neck_y, 0.9] # Neck
        kps[6] = [100.0, neck_y, 0.9]  # Hip moving straight
        
        # Legs extensions (ref size ~ 20)
        kps[7] = [90.0, neck_y + 10.0, 0.9]
        kps[9] = [90.0, neck_y + 20.0, 0.9]
        kps[8] = [110.0, neck_y + 10.0, 0.9]
        kps[10] = [110.0, neck_y + 20.0, 0.9]
        
        res = analyzer.update_track(
            track_id=30, 
            keypoints=kps, 
            timestamp=base_time + timedelta(seconds=i * 0.1)
        )
        
    assert res["status"] == "ANALYZED"
    assert res["lateral_sway_px"] > 10.0
    assert res["sway_ratio"] > 0.4
    assert res["kestin_gait_score"] >= 2  # due to high sway ratio


def test_lameness_detector_coco_and_unilateral():
    from unittest.mock import patch
    with patch("ultralytics.YOLO") as mock_yolo:
        detector = LamenessDetector(model_path="dummy.pt")
        
    # Generate 17 keypoint mock history (COCO)
    # Left leg: healthy (angle ~140). Right leg: lame (angle ~50).
    kp = np.zeros((17, 3))
    # Fill left leg (indices 11, 13, 15) and right leg (indices 12, 14, 16) with values > 0
    kp[11] = [0.1, 0.1, 0.9]
    kp[13] = [0.1, 0.2, 0.9]
    kp[15] = [0.1, 0.3, 0.9]
    
    kp[12] = [0.2, 0.1, 0.9]
    kp[14] = [0.2, 0.2, 0.9]
    kp[16] = [0.2, 0.3, 0.9]
    
    detector.track_history[1] = [kp] * 20
    
    # We mock calculate_hock_angle to return:
    # Frame 0: Esquerda=140, Direita=50
    # Frame 1: Esquerda=140, Direita=51...
    # Since it iterates over all frames and legs, calculate_hock_angle will be called
    # 20 * 2 = 40 times.
    mock_angles = []
    for i in range(20):
        mock_angles.append(140.0) # Esquerda
        mock_angles.append(50.0 + (i % 2)) # Direita
        
    with patch.object(detector, "calculate_hock_angle", side_effect=mock_angles):
        is_lame, conf, details = detector.analyze_gait(track_id=1)
        
    assert is_lame is True
    # The right leg average angle will be 50.5 (< 60.0), triggering lameness
    assert "Esquerda" in details["legs_detail"]
    assert "Direita" in details["legs_detail"]
    assert details["legs_detail"]["Direita"]["is_lame"] is True
    assert details["legs_detail"]["Esquerda"]["is_lame"] is False
    assert details["legs_detail"]["asymmetry_diff_deg"] == pytest.approx(89.5, abs=1.0)
