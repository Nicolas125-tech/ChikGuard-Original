# Configuração do Ambiente de Visão Computacional (Windows)

Este guia cobre a configuração necessária para rodar o pipeline otimizado do ChikGuard (SAHI + YOLOv9-Seg + ByteTrack + CLAHE) em ambientes Windows, seja para desenvolvimento local ou execução em hardware Windows IoT.

## 1. Pré-requisitos do Sistema

Para ambientes Windows, você precisará das seguintes ferramentas básicas:

1. **Python 3.9 a 3.11:** Instale a versão mais recente dentro deste range via [python.org](https://www.python.org/downloads/windows/) (Marque a opção "Add Python to PATH").
2. **Visual Studio C++ Build Tools:** Requerido para compilar algumas dependências do OpenCV e de Machine Learning. Baixe o instalador do Visual Studio e instale a carga de trabalho "Desenvolvimento para desktop com C++".
3. *(Opcional, mas recomendado)* **CUDA Toolkit e cuDNN:** Se sua máquina possuir uma placa de vídeo NVIDIA, instale o CUDA Toolkit e o cuDNN compatíveis com sua versão do PyTorch para acelerar a inferência.

## 2. Dependências Python

O ambiente virtual é altamente recomendado. Abra o PowerShell ou o Prompt de Comando e execute:

```cmd
python -m virtualenv venv
.\venv\Scripts\activate

# Instalar os requisitos principais
pip install -r backend\requirements.txt

# Instalar os requisitos de Visão Computacional Avançada
pip install sahi ultralytics lapx numpy opencv-python
```
*Nota:* No Windows, se o `lapx` falhar ao compilar, certifique-se de que o C++ Build Tools está corretamente instalado. O `lapx` é obrigatório para o ByteTrack.

## 3. Preparando os Modelos de IA (Exportação para Windows)

### Exportando para OpenVINO (CPUs Intel)

Se você não tiver uma GPU NVIDIA dedicada, o OpenVINO tira proveito dos processadores Intel para acelerar drasticamente a predição.

```cmd
yolo export model=yolov9-seg.pt format=openvino half=True int8=True
```
*Isso irá gerar uma pasta com arquivos `.xml` e `.bin` otimizados.*

### Exportando para TensorRT (GPUs NVIDIA)

Se você tiver CUDA configurado no Windows:

```cmd
yolo export model=yolov9-seg.pt format=engine half=True workspace=4
```

## 4. Testando o Pipeline no Windows

Para testar o pipeline com uma webcam conectada diretamente ao Windows:

```cmd
# Executar usando o modelo YOLO base (ou substitua pelo modelo exportado) com a câmera principal (0)
python backend\src\vision\sahi_yolo_integration.py --model yolov9-seg.pt --video 0

# Executar desativando o SAHI (baseline de comparação)
python backend\src\vision\sahi_yolo_integration.py --model yolov9-seg.pt --video 0 --no-sahi
```

## Dica: Uso de WSL2 e Câmeras USB

Se você preferir rodar o código dentro do WSL2 (Ubuntu no Windows) em vez do Windows nativo, lembre-se de que o WSL2 **não** acessa nativamente webcams USB. Você precisará instalar a ferramenta `usbipd-win` no lado do Windows:

1. No PowerShell do Windows como Administrador:
   ```cmd
   winget install --interactive --exact dorssel.usbipd-win
   usbipd list
   usbipd bind --busid <BUS-ID-DA-CAMERA>
   usbipd attach --wsl --busid <BUS-ID-DA-CAMERA>
   ```
2. Após isso, siga o guia `VISION_EDGE_SETUP.md` dentro do seu ambiente Linux/WSL2.
