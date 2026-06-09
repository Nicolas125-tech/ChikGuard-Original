import pytest
import sys
import os
import unittest.mock as mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

# The app logic often instantiates background threads or starts processing
# We want to import just the function and avoid global execution blocks.
# Mocking cv2 prevents video loading and pipeline starting side-effects in most cases.
sys.modules["cv2"] = mock.MagicMock()
os.environ["ADMIN_PASSWORD"] = "dummy_password"

from app import _box_center_area


def test_box_center_area_basic():
    """Test standard box coordinates."""
    cx, cy, area = _box_center_area([10, 10, 20, 20])
    assert cx == 15
    assert cy == 15
    assert area == 100


def test_box_center_area_zero_area():
    """Test when x1=x2 and y1=y2, area should be at least 1."""
    cx, cy, area = _box_center_area([10, 10, 10, 10])
    assert cx == 10
    assert cy == 10
    assert area == 1


def test_box_center_area_floats():
    """Test with float inputs to ensure they are parsed as ints correctly."""
    cx, cy, area = _box_center_area([10.5, 10.1, 20.9, 20.8])
    # Parsed to int: [10, 10, 20, 20]
    assert cx == 15
    assert cy == 15
    assert area == 100


def test_box_center_area_negative_coords():
    """Test with negative coordinates (e.g. from edge cases in models)."""
    cx, cy, area = _box_center_area([-20, -20, -10, -10])
    assert cx == -15
    assert cy == -15
    assert area == 100


def test_box_center_area_non_square():
    """Test with non-square rectangle."""
    cx, cy, area = _box_center_area([0, 0, 100, 50])
    assert cx == 50
    assert cy == 25
    assert area == 5000
