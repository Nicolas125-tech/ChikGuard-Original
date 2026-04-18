import cv2

import argparse
from vision_engine import VisionEngine
from tracking import Tracker


def main():
    parser = argparse.ArgumentParser(description="Teste de integração SAHI + YOLO + ByteTrack")
    parser.add_argument("--video", type=str, default="0", help="Caminho do video ou index da câmera (default 0)")
    parser.add_argument("--model", type=str, required=True, help="Caminho para o modelo YOLO (ex: yolov9c.pt)")
    parser.add_argument("--no-sahi", action="store_true", help="Desativa o SAHI para comparar o baseline")
    args = parser.parse_args()

    # Tenta usar int para index de câmera
    try:
        video_source = int(args.video)
    except ValueError:
        video_source = args.video

    print(f"Iniciando integração. Modelo: {args.model}")
    print(f"Fonte de vídeo: {video_source}")
    print(f"SAHI Ativado: {not args.no_sahi}")

    # Inicializa a Engine de Visão (com CLAHE e SAHI automáticos)
    engine = VisionEngine(
        model_path=args.model,
        camera_index=video_source,
        use_sahi=not args.no_sahi,
        slice_height=512,
        slice_width=512,
        confidence_threshold=0.25
    )

    # Inicializa o Tracker Ágil
    tracker = Tracker(use_bytetrack=True)

    cap = cv2.VideoCapture(video_source)
    if not cap.isOpened():
        print("Erro ao abrir vídeo/câmera.")
        return

    print("Processando... Pressione 'q' para sair.")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Fim do vídeo ou falha ao ler o frame.")
            break

        height, width = frame.shape[:2]

        # 1. Inferência com Visão Computacional (já aplica CLAHE e SAHI internamente)
        detections = engine.predict(frame)

        # 2. Tracking Ágil (ByteTrack associando os IDs)
        tracked_objects = tracker.update(detections, img_info=(height, width))

        # 3. Desenha na tela para validação visual
        for obj_id, data in tracked_objects.items():
            bbox = data.get('bbox')
            if bbox:
                x1, y1, x2, y2 = bbox

                # Desenha a caixa delimitadora
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Desenha o ID do Tracker
                label = f"ID: {obj_id}"
                cv2.putText(frame, label, (x1, max(10, y1 - 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                # Desenha o centroide
                cx, cy = data['centroid']
                cv2.circle(frame, (cx, cy), 4, (0, 0, 255), -1)

        # Informações de status na tela
        status_text = f"Modelo: {args.model} | SAHI: {'Sim' if not args.no_sahi else 'Nao'} | Dets: {len(detections)}"
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.imshow("ChikGuard - Pipeline Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
