# Configuração do Ambiente de Visão Computacional (Edge Linux)

Este guia cobre a configuração necessária para rodar o pipeline otimizado do ChikGuard (SAHI + YOLOv9-Seg + ByteTrack + CLAHE) em hardware Edge (Mini PCs, Jetson, NUCs rodando Linux).

## 1. Dependências do Sistema

Certifique-se de que o sistema possui as bibliotecas do OpenCV instaladas a nível de SO (se estiver rodando sem Docker):

```bash
sudo apt-get update
sudo apt-get install -y libgl1-mesa-glx libglib2.0-0
```

## 2. Dependências Python

O novo pipeline requer pacotes específicos para inferência fatiada e tracking ágil:

```bash
pip install -r backend/requirements.txt
pip install sahi ultralytics lapx numpy opencv-python
```
*Aviso:* O pacote `lapx` é obrigatório para que a engine de regressão linear do `BYTETracker` funcione corretamente no back-end do pacote `ultralytics`.

## 3. Preparando os Modelos de IA (Exportação para Edge)

Para evitar que a CPU "derreta" durante a inferência fatiada, não utilize modelos `.pt` puros em produção. Exporte-os para TensorRT (NVIDIA) ou OpenVINO (Intel CPU).

### Exportando para OpenVINO (Recomendado para Mini PCs Intel NUC/Celeron)

```bash
yolo export model=yolov9-seg.pt format=openvino half=True int8=True
```
*Isso irá gerar uma pasta com arquivos `.xml` e `.bin` otimizados e quantizados, acelerando drasticamente a predição na CPU.*

### Exportando para TensorRT (Recomendado para NVIDIA Jetson)

```bash
yolo export model=yolov9-seg.pt format=engine half=True workspace=4
```

## 4. Testando o Pipeline

Para verificar se o CLAHE, SAHI e o ByteTrack estão operando juntos, execute o script de integração:

```bash
# Executar usando o modelo otimizado e uma webcam USB
python3 backend/src/vision/sahi_yolo_integration.py --model yolov9-seg_openvino_model/ --video 0

# Executar desativando o SAHI (para comparar a perda de detecções ao fundo do galpão)
python3 backend/src/vision/sahi_yolo_integration.py --model yolov9-seg.pt --video 0 --no-sahi
```
