from ultralytics import YOLO

def export_model():
    print("Loading YOLOv8n-seg model... (this may download the weights)")
    model = YOLO("yolov8n-seg.pt")
    
    print("Exporting model to ONNX format with float16 precision for FPS optimization...")
    path = model.export(format="onnx", half=True)
    
    print(f"Export successful! ONNX model saved at: {path}")

if __name__ == "__main__":
    export_model()
