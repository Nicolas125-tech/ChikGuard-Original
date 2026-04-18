# Configuração do Ambiente Industrial (ChikGuard Vision v3)

Este guia detalha o processo de configuração de um Mini PC Linux para rodar o pipeline de visão de alta performance com SAHI, YOLO e ByteTrack.

## 1. Dependências do Sistema (Ubuntu/Debian)

Primeiro, instale as dependências de sistema para processamento de vídeo e aceleração:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv libgl1-mesa-glx libglib2.0-0
# Dependências para OpenCV e Compilação
sudo apt install -y libsm6 libxext6 libxrender-dev
```

## 2. Preparação do Ambiente Python

Crie um ambiente virtual dedicado para evitar conflitos de bibliotecas:

```bash
cd ChikGuard-Original/backend
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

## 3. Instalação das Bibliotecas de Visão

Instale os pacotes principais, incluindo o suporte a fatiamento (SAHI):

```bash
pip install ultralytics sahi onnxruntime-gpu  # onnxruntime-gpu para aceleração NVIDIA
# Caso use OpenVINO (Intel):
# pip install openvino-dev
```

## 4. Otimização para Edge (Hardware Local)

Para atingir FPS de nível industrial em Mini PCs, você deve exportar os pesos `.pt` para formatos otimizados:

### A. Para NVIDIA (TensorRT)
```bash
# Dentro do ambiente python
python -c "from ultralytics import YOLO; model = YOLO('yolov8n-seg.pt'); model.export(format='engine', device=0, half=True)"
```

### B. Para Intel (OpenVINO)
```bash
python -c "from ultralytics import YOLO; model = YOLO('yolov8n-seg.pt'); model.export(format='openvino', half=True)"
```

## 5. Execução do Pipeline

A classe `VisionEngine` configurada em `src/core/vision_engine.py` irá automaticamente detectar os arquivos `.engine` ou `.xml` se os caminhos forem atualizados no `.env`.

> [!TIP]
> **Use SAHI com moderação em Edge**: Em dispositivos muito limitados, prefira o `use_sahi=False` no construtor da `VisionEngine` e aumente o parâmetro `imgsz` para 1280 para manter o detalhe dos pintinhos sem o overhead do fatiamento massivo.

> [!IMPORTANT]
> **Permissões de Câmera**: Certifique-se de que o usuário tem grupos `video` e `render`:
> `sudo usermod -aG video,render $USER`
