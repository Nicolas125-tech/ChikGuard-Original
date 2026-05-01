#!/bin/bash

# ChikGuard Edge Inference - Model Export Pipeline
# Converts YOLO PyTorch models (.pt) to optimized formats (ONNX, NCNN, TensorRT) for Edge Hardware (Raspberry Pi, Mini PCs).

set -e

echo "=========================================="
echo " ChikGuard Model Export Pipeline Started  "
echo "=========================================="

# Default paths
MODEL_PATH=${1:-"yolov8n.pt"}
IMG_SIZE=${2:-640}

if [ ! -f "$MODEL_PATH" ]; then
    echo "Error: Model file $MODEL_PATH not found!"
    exit 1
fi

echo "Installing required export dependencies..."
pip install ultralytics onnx onnxruntime onnxsim
# ncnn requires additional setup depending on OS, but ultralytics attempts to handle it

echo "------------------------------------------"
echo " Exporting to ONNX (High compatibility)   "
echo "------------------------------------------"
# ONNX is great for general CPU/GPU acceleration (OpenVINO, DirectML, etc.)
yolo export model=$MODEL_PATH format=onnx imgsz=$IMG_SIZE simplify=True half=False

echo "------------------------------------------"
echo " Exporting to NCNN (Mobile / Raspberry Pi)"
echo "------------------------------------------"
# NCNN is highly optimized for ARM CPUs (like Raspberry Pi)
yolo export model=$MODEL_PATH format=ncnn imgsz=$IMG_SIZE half=True

echo "------------------------------------------"
echo " Exporting to TensorRT (NVIDIA Jetson)    "
echo "------------------------------------------"
# Note: TensorRT export requires running ON NVIDIA hardware with TensorRT installed
# We will wrap this in a try-catch equivalent in bash or just warn the user.
echo "Note: TensorRT export requires NVIDIA hardware and TensorRT libraries."
echo "If this fails, ignore it unless you are on a Jetson device."
yolo export model=$MODEL_PATH format=engine imgsz=$IMG_SIZE half=True || echo "TensorRT export skipped (likely not on NVIDIA hardware)."

echo "=========================================="
echo " Export Pipeline Completed Successfully!  "
echo "=========================================="
echo "Generated formats:"
echo " - .onnx (For generic Edge PCs / OpenVINO)"
echo " - _ncnn_model/ (For Raspberry Pi / ARM Edge)"
echo " - .engine (For NVIDIA Jetson - if successful)"
