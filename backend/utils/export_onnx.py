import sys
import argparse
from ultralytics import YOLO

def main():
    parser = argparse.ArgumentParser(description="Export YOLO model to ONNX for acceleration.")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Path to the YOLO model to export (default: yolov8n.pt)")
    parser.add_argument("--format", type=str, default="onnx", help="Export format (default: onnx)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image size for inference (default: 640)")
    parser.add_argument("--dynamic", action="store_true", help="Use dynamic axes for ONNX export")

    args = parser.parse_args()

    print(f"Loading model: {args.model}")
    try:
        model = YOLO(args.model)
    except Exception as e:
        print(f"Error loading model: {e}")
        sys.exit(1)

    print(f"Exporting model to {args.format} format with imgsz={args.imgsz}...")
    try:
        exported_path = model.export(format=args.format, imgsz=args.imgsz, dynamic=args.dynamic)
        print(f"Successfully exported model to: {exported_path}")
    except Exception as e:
        print(f"Error exporting model: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
