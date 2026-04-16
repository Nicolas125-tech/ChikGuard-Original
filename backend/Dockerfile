FROM python:3.12-slim-bookworm

WORKDIR /app

# Instala dependências do sistema necessárias para OpenCV, OpenVINO, ONNX
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsndfile1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt psutil onnxruntime openvino

COPY . .

ENV PYTHONPATH=/app

EXPOSE 5000

CMD ["python", "app.py"]
