# Configuração do Ambiente ChikGuard Vision v3 - Windows

Este guia detalha como configurar o pipeline de visão de alta performance em máquinas Windows 10/11, utilizando aceleração por GPU (NVIDIA) ou CPU (Intel).

## 1. Pré-requisitos de Sistema

### A. Python
- Instale o **Python 3.10 ou 3.11** via [python.org](https://www.python.org/).
- **IMPORTANTE:** Durante a instalação, marque a opção **"Add Python to PATH"**.

### B. Ferramentas de Compilação (Obrigatório para SAHI/ByteTrack)
- Instale o **Visual Studio Community** (2019 ou 2022).
- No instalador, selecione a carga de trabalho: **"Desenvolvimento para desktop com C++"**.
- Isso é necessário para compilar bibliotecas como `lap` e `cython-bbox`.

## 2. Configuração de GPU (NVIDIA - Opcional mas Recomendado)

Se você tiver uma placa NVIDIA, instale:
1. **CUDA Toolkit 11.8 ou 12.1**
2. **cuDNN v8.x** (compatível com a versão do CUDA escolhida)

## 3. Preparação do Ambiente

Abra o **PowerShell** ou **CMD** na pasta do projeto:

```powershell
cd backend
python -m venv venv .\venv\Scripts\activate
python -m pip install --upgrade pip
```

## 4. Instalação das Bibliotecas

```powershell
# Versão com suporte a CPU (Padrão)
pip install ultralytics sahi onnxruntime

# SE TIVER GPU NVIDIA:
# pip uninstall onnxruntime
# pip install onnxruntime-gpu
```

## 5. Exportação e Otimização (Edge)

Para obter o máximo de FPS no Windows, utilize o formato **ONNX** ou **OpenVINO**:

### A. Para Intel (OpenVINO - Excelente em CPUs modernas)
```powershell
python -c "from ultralytics import YOLO; model = YOLO('yolov8n-seg.pt'); model.export(format='openvino', half=True)"
```

### B. Para NVIDIA (TensorRT)
*Nota: Requer TensorRT instalado no Windows e configurado no PATH.*
```powershell
python -c "from ultralytics import YOLO; model = YOLO('yolov8n-seg.pt'); model.export(format='engine', device=0, half=True)"
```

## 6. Solução de Problemas Comuns no Windows

- **Erro de "Execution Policy" no PowerShell**: 
  Execute o comando: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`
- **DLLs Faltantes**: 
  Instale o [Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe).
- **Caminho Longo (Long Paths)**: 
  Se houver erro de instalação, habilite caminhos longos no Windows Registry ou via `git config --system core.longpaths true`.

> [!TIP]
> No Windows, o backend OpenCV pode ser melhor performado usando `cv2.CAP_DSHOW` ou `cv2.CAP_MSMF`. O código na `VisionEngine` já está preparado para essas nuances.
