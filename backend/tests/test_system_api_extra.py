import sys
import importlib
if "cv2" in sys.modules and type(sys.modules["cv2"]).__name__ == "MagicMock":
    del sys.modules["cv2"]
import cv2
import pytest
from src.api.system_api_extra import _validate_rule_data

def test_validate_rule_data_valid():
    data = {
        "name": "Test Rule",
        "condition_variable": "temperature",
        "condition_operator": ">",
        "condition_value": "30",
        "action_device": "fan",
        "action_state": "on"
    }
    assert _validate_rule_data(data) is True

def test_validate_rule_data_missing_fields():
    data = {
        "name": "Test Rule"
    }
    assert _validate_rule_data(data) is True

def test_validate_rule_data_invalid_length():
    data = {
        "name": "A" * 101,
        "condition_variable": "temperature",
        "condition_operator": ">",
        "condition_value": "30",
        "action_device": "fan",
        "action_state": "on"
    }
    assert _validate_rule_data(data) is False

def test_validate_rule_data_another_invalid_length():
    data = {
        "name": "Test Rule",
        "condition_variable": "A" * 101,
        "condition_operator": ">",
        "condition_value": "30",
        "action_device": "fan",
        "action_state": "on"
    }
    assert _validate_rule_data(data) is False

def test_validate_rule_data_other_types():
    data = {
        "name": "Test Rule",
        "condition_variable": "temperature",
        "condition_operator": ">",
        "condition_value": 30,
        "action_device": "fan",
        "action_state": "on"
    }
    assert _validate_rule_data(data) is True

def test_validate_rule_data_empty():
    data = {}
    assert _validate_rule_data(data) is True
