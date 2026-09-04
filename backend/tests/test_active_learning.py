import pytest
from unittest.mock import patch, MagicMock
import numpy as np
import os

from src.mlops.active_learning import ActiveLearningPipeline

@pytest.fixture(autouse=True)
def mock_cv2():
    with patch("src.mlops.active_learning.cv2") as mock:
        yield mock

@pytest.fixture(autouse=True)
def mock_os():
    with patch("src.mlops.active_learning.os") as mock:
        mock.path.join.side_effect = lambda *args: "/".join(args)
        yield mock

@pytest.fixture
def mock_time():
    with patch("src.mlops.active_learning.time") as mock:
        mock.time.return_value = 1000.0
        yield mock

def test_init_success(mock_os, mock_cv2):
    mock_os.path.exists.return_value = True
    mock_cv2.data.haarcascades = "path/to/cascades/"
    mock_classifier = MagicMock()
    mock_cv2.CascadeClassifier.return_value = mock_classifier

    pipeline = ActiveLearningPipeline(output_dir="test_dir", min_conf=0.2, max_conf=0.6)

    assert pipeline.output_dir == "test_dir"
    assert pipeline.min_conf == 0.2
    assert pipeline.max_conf == 0.6
    mock_os.makedirs.assert_called_once_with("test_dir", exist_ok=True)
    mock_cv2.CascadeClassifier.assert_called_once_with("path/to/cascades/haarcascade_frontalface_default.xml")
    assert pipeline.face_cascade == mock_classifier

def test_init_no_cascade_file(mock_os, mock_cv2):
    mock_os.path.exists.return_value = False

    pipeline = ActiveLearningPipeline()

    mock_cv2.CascadeClassifier.assert_not_called()
    assert pipeline.face_cascade is None

def test_init_cascade_error(mock_os, mock_cv2):
    mock_os.path.exists.return_value = True
    mock_cv2.CascadeClassifier.side_effect = Exception("Test error")

    pipeline = ActiveLearningPipeline()

    assert pipeline.face_cascade is None

@patch.object(ActiveLearningPipeline, '_save_uncertain_frame')
def test_process_detection_non_target(mock_save, mock_os, mock_cv2):
    pipeline = ActiveLearningPipeline()

    pipeline.process_detection(frame=None, detection={"confidence": 0.4, "box": [0,0,10,10]}, class_name="dog")

    mock_save.assert_not_called()

@patch.object(ActiveLearningPipeline, '_save_uncertain_frame')
def test_process_detection_outside_conf_range(mock_save, mock_os, mock_cv2):
    pipeline = ActiveLearningPipeline(min_conf=0.3, max_conf=0.45)

    # Below min_conf
    pipeline.process_detection(frame=None, detection={"confidence": 0.2, "box": [0,0,10,10]}, class_name="bird")
    mock_save.assert_not_called()

    # Above max_conf
    pipeline.process_detection(frame=None, detection={"confidence": 0.8, "box": [0,0,10,10]}, class_name="chicken")
    mock_save.assert_not_called()

@patch.object(ActiveLearningPipeline, '_save_uncertain_frame')
def test_process_detection_uncertain(mock_save, mock_os, mock_cv2):
    pipeline = ActiveLearningPipeline(min_conf=0.3, max_conf=0.45)
    frame = np.zeros((100, 100, 3), dtype=np.uint8)

    # Within conf
    pipeline.process_detection(frame=frame, detection={"confidence": 0.4, "box": [0,0,10,10]}, class_name="galinha")

    mock_save.assert_called_once()
    # Check if a copy was passed
    args, _ = mock_save.call_args
    assert args[0] is not frame
    assert np.array_equal(args[0], frame)

def test_save_uncertain_frame_with_faces(mock_os, mock_cv2, mock_time):
    pipeline = ActiveLearningPipeline()
    pipeline.output_dir = "test_dir"
    pipeline.face_cascade = MagicMock()

    # Setup face detection mock to return one face
    pipeline.face_cascade.detectMultiScale.return_value = [[10, 10, 20, 20]]

    # Frame and detection setup
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    detection = {"box": [50, 50, 100, 100]}

    # IMPORTANT: The issue is mock_cv2.GaussianBlur needs to return an array of correct shape
    # The face roi in the code is frame[10:30, 10:30] which has shape (20, 20, 3)
    mock_cv2.GaussianBlur.return_value = np.ones((20, 20, 3), dtype=np.uint8)

    pipeline._save_uncertain_frame(frame, detection, conf=0.42)

    # Verify face blurring logic
    mock_cv2.cvtColor.assert_called_once()
    pipeline.face_cascade.detectMultiScale.assert_called_once()
    mock_cv2.GaussianBlur.assert_called_once()

    # Verify saving logic
    expected_filename = "uncertain_1000000_conf_0.42.jpg"
    expected_filepath = f"test_dir/{expected_filename}"
    mock_cv2.imwrite.assert_called_once()
    args, kwargs = mock_cv2.imwrite.call_args
    assert args[0] == expected_filepath
    # Crop should be pad 100 from 50,50 -> 0,0 and 100,100 -> 200,200 (max frame dimensions)
    assert args[1].shape[:2] == (200, 200)

def test_save_uncertain_frame_no_faces(mock_os, mock_cv2, mock_time):
    pipeline = ActiveLearningPipeline()
    pipeline.output_dir = "test_dir"
    pipeline.face_cascade = None

    frame = np.zeros((500, 500, 3), dtype=np.uint8)
    # Box well inside
    detection = {"box": [200, 200, 300, 300]}

    pipeline._save_uncertain_frame(frame, detection, conf=0.35)

    # Blur logic skipped
    mock_cv2.cvtColor.assert_not_called()
    mock_cv2.GaussianBlur.assert_not_called()

    mock_cv2.imwrite.assert_called_once()
    args, kwargs = mock_cv2.imwrite.call_args

    # Check crop dimensions: pad=100 -> cy1=100, cx1=100, cy2=400, cx2=400 -> shape=(300,300)
    assert args[1].shape[:2] == (300, 300)
    expected_filename = "uncertain_1000000_conf_0.35.jpg"
    assert args[0] == f"test_dir/{expected_filename}"

def test_save_uncertain_frame_error(mock_os, mock_cv2):
    pipeline = ActiveLearningPipeline()
    pipeline.face_cascade = None

    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    detection = {"box": [0,0,10,10]}

    mock_cv2.imwrite.side_effect = Exception("Write error")

    # Should handle gracefully and log
    pipeline._save_uncertain_frame(frame, detection, conf=0.35)

def test_sync_to_cloud_no_files(mock_os, mock_cv2):
    pipeline = ActiveLearningPipeline()
    pipeline.output_dir = "test_dir"

    mock_os.listdir.return_value = ["file.txt", "video.mp4"]

    pipeline.sync_to_cloud()

    mock_os.remove.assert_not_called()

def test_sync_to_cloud_success(mock_os, mock_cv2):
    pipeline = ActiveLearningPipeline()
    pipeline.output_dir = "test_dir"

    mock_os.listdir.return_value = ["img1.jpg", "doc.pdf", "img2.jpg"]

    pipeline.sync_to_cloud()

    assert mock_os.remove.call_count == 2
    mock_os.remove.assert_any_call("test_dir/img1.jpg")
    mock_os.remove.assert_any_call("test_dir/img2.jpg")

def test_sync_to_cloud_error(mock_os, mock_cv2):
    pipeline = ActiveLearningPipeline()
    pipeline.output_dir = "test_dir"

    mock_os.listdir.return_value = ["img1.jpg"]
    mock_os.remove.side_effect = Exception("Delete error")

    # Should handle gracefully
    pipeline.sync_to_cloud()
    mock_os.remove.assert_called_once()
