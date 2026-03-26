import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Constantes para Anonimizacao (LGPD / GDPR)
BLUR_KERNEL_SIZE = (55, 55) # Kernel forte para ofuscar tracos faciais
BLUR_SIGMA_X = 30           # Desvio padrao gaussiano alto para desfocar

def anonymize_human_detections(frame: np.ndarray, detections: list) -> np.ndarray:
    """
    LGPD / Privacy by Design (ChikGuard Edge):
    Aplica um desfoque forte (GaussianBlur) sobre as bounding boxes
    de pessoas detetadas no frame. Este processo deve ocorrer ANTES
    do frame ser guardado no disco do Mini PC ou streamed/enviado para a Cloud.

    Args:
        frame (np.ndarray): A imagem original (BGR) capturada pela camera.
        detections (list): Lista de deteccoes YOLOv8.
                           Ex: [{'class': 0, 'confidence': 0.85, 'box': [x1, y1, x2, y2]}]

    Returns:
        np.ndarray: O frame modificado, agora anonimizado (com as caras/corpos borrados).
    """
    if frame is None:
        return frame

    # Copia o frame para garantir que nao estamos alterando uma referencia
    # original em transito num buffer de memoria partilhada (Zero Trust).
    anonymized_frame = frame.copy()

    # Altura e largura para garantir recortes dentro da imagem (evita OutOfBounds)
    h_frame, w_frame = anonymized_frame.shape[:2]

    # Itera sobre todas as deteccoes fornecidas pelo YOLOv8 (ou similar)
    # A classe '0' no dataset COCO padrao do YOLO e a classe "person".
    for det in detections:
        # Se detetarmos a classe '0' (Pessoa/Humano), entra em modo anonimizacao
        if det.get("class") == 0:
            box = det.get("box", [])
            if not box or len(box) != 4:
                continue

            # Converte coordenadas para inteiros
            # (YOLO retorna floats, e cv2 necessita de pixels int)
            x1, y1, x2, y2 = map(int, box)

            # Clamp das coordenadas para dentro das bordas da imagem
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = min(w_frame, x2)
            y2 = min(h_frame, y2)

            # Verifica se a bounding box e valida apos o clamping
            if x2 <= x1 or y2 <= y1:
                logger.warning(f"Bounding box invalida descartada: {box}")
                continue

            # Extrair a Regiao de Interesse (ROI) referente a pessoa detetada
            roi = anonymized_frame[y1:y2, x1:x2]

            # DICA DE ARQUITETURA DE ML (Active Learning):
            # O YOLOv8 geralmente marca a bounding box de todo o corpo da pessoa.
            # Se for exigido preservar o resto do corpo (ex: ver o uniforme do
            # funcionario da granja), recomendase aplicar aqui um `Haar Cascade`
            # secundario apenas dentro desta ROI (roi) para procurar caras/olhos
            # (cv2.CascadeClassifier('haarcascade_frontalface_default.xml'))
            # e so aplicar o desfoque nessa sub-regiao facial, mantendo o corpo visivel.
            #
            # Como a exigencia atual e desfoque rigoroso LGPD (Zero Trust total visual),
            # vamos desfocar toda a bounding box da pessoa detetada.

            # Aplicar um Gaussian Blur forte na area isolada
            blurred_roi = cv2.GaussianBlur(roi, BLUR_KERNEL_SIZE, BLUR_SIGMA_X)

            # Opcional mas recomendado: Para um efeito pixelado ou de bloco ("Minecraft"),
            # ou para tornar a recuperacao da cara inviavel mesmo com IA de deblurring,
            # podemos adicionar um downscale seguido de um upscale antes do blur.
            # pequenos_pixels = cv2.resize(roi, (8, 8), interpolation=cv2.INTER_LINEAR)
            # blurred_roi = cv2.resize(pequenos_pixels, (x2-x1, y2-y1), interpolation=cv2.INTER_NEAREST)

            # Recolar a Regiao de Interesse ofuscada de volta na imagem original
            anonymized_frame[y1:y2, x1:x2] = blurred_roi
            logger.debug(f"Pessoa (Classe 0) anonimizada nas coordenadas: [{x1},{y1},{x2},{y2}]")

    return anonymized_frame
