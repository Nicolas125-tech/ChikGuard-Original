import cv2
import os
from ultralytics import YOLO
from pathlib import Path

def extract_critical_frames(video_path, model_path, output_dir, conf_threshold_critical=0.5, conf_threshold_min=0.1, skip_frames=5):
    """
    Extracts frames from a video where detection confidence is critical (between min and critical thresholds).
    This helps in identifying hard examples for fine-tuning.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Loading model from {model_path}...")
    model = YOLO(model_path)
    
    print(f"Opening video {video_path}...")
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error opening video stream or file: {video_path}")
        return

    frame_count = 0
    saved_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        
        # Process every Nth frame to speed up and avoid highly correlated frames
        if frame_count % skip_frames != 0:
            continue
            
        # Run inference
        results = model.predict(frame, verbose=False)
        
        is_critical = False
        
        # Analyze detections
        for result in results:
            boxes = result.boxes
            if boxes is not None and len(boxes) > 0:
                for conf in boxes.conf:
                    conf_val = float(conf)
                    # If we find a detection that is weak but not completely garbage
                    if conf_threshold_min < conf_val < conf_threshold_critical:
                        is_critical = True
                        break
            else:
                # If no detections at all, it might also be a critical frame (missed detection)
                # But to avoid saving too many empty frames, you could toggle this logic based on context
                pass
                
        if is_critical:
            out_filename = os.path.join(output_dir, f"critical_frame_{frame_count:06d}.jpg")
            cv2.imwrite(out_filename, frame)
            saved_count += 1
            if saved_count % 10 == 0:
                print(f"Saved {saved_count} critical frames so far...")
                
    cap.release()
    print(f"Extraction complete. Total critical frames saved: {saved_count}")

if __name__ == "__main__":
    # Example usage
    VIDEO_PATH = "video_granja.mp4"
    MODEL_PATH = "yolov8n.pt"  # Use your current best model
    OUTPUT_DIR = "data/critical_frames"
    
    if os.path.exists(VIDEO_PATH) and os.path.exists(MODEL_PATH):
        extract_critical_frames(VIDEO_PATH, MODEL_PATH, OUTPUT_DIR)
    else:
        print(f"Please ensure {VIDEO_PATH} and {MODEL_PATH} exist to run the extraction.")
