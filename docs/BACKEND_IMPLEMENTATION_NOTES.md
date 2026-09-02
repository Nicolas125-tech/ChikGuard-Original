# Implementation Plan: ChikGuard Enterprise CV Pipeline

Este documento detalha o desenho da arquitetura para o motor de visão computacional do ChikGuard. O objetivo é substituir processamentos legados por algoritmos otimizados para Edge Computing e baixa latência.

## Arquitetura e Tecnologias

Para alcançar os requisitos, o sistema será modularizado:
1. **Inference Core**: Substituição dos tensores brutos por modelos (YOLOv10 ou RT-DETR), empacotados usando **ONNX Runtime (otimizado via TensorRT)** para melhorar os frames por segundo (FPS) no edge hardware.
2. **Tracker**: Integração com **ByteTrack** (via `supervision`) mantendo a persistência temporal sobre os IDs das aves, lidando com oclusões.
3. **Módulo Comportamental**: Análise das variações vetoriais, gerando **Heatmaps** e executando detecção de anomalias (como imobilidade).
4. **Streaming de Baixa Latência**: Substituição do MJPEG (M-JPEG over HTTP) por um servidor de streaming **WebRTC** (ou, alternativamente, **HLS** in-memory) gerenciado pelo Flask.

---

> [!IMPORTANT]
> **User Review Required**
> Como estamos alterando o streaming de vídeo de bytes crus para WebRTC / HLS no Flask, precisarei da sua escolha:
> 
> 1. **WebRTC (`aiortc`)**: Menor latência (~200ms), mas exige refatoração no front-end para negociar conexões (SDP, ICE candidatos).
> 2. **HLS In-Memory**: Latência ligeiramente maior (~2-5s), mas com compatibilidade universal (o React precisará apenas de uma tag de vídeo ou player HLS padrão, como HLS.js).
>
> Recomendação: HLS com fragmentos curtos via RAM se for focado em dashboards complexos, WebRTC se focarmos em resposta imediata em guarita de monitoramento.

---

## Estrutura Modular Proposta

O código não ficará misturado. A arquitetura de pastas desenhada:
```
backend/src/cv_master/
├── __init__.py
├── inference.py           # (Motor TensorRT/ONNX + YOLOv10/RT-DETR + SAHI)
├── tracker.py             # (Motor ByteTrack de retenção de memória multialvo)
├── behavior_engine.py     # (Heatmaps + Vetor de imobilidade)
└── stream_gateway.py      # (Integração de WebRTC/HLS com o Flask)
```

### 1. Motor de Inferência `inference.py`
Carregamento delegado para ONNX Runtime (com `providers=['TensorrtExecutionProvider', 'CUDAExecutionProvider']`).
Garante que o modelo trabalhe com a GPU. Lógica baseada nas SDKs Python atuais.

### 2. Tracker `tracker.py`
Será utilizado `sv.ByteTrack` com buffers ajustados para lidar com o ambiente orgânico (onde as aves se movem de forma imprevisível e sobreposta). As chaves de rastreamento são as identificações. Manteremos um dict local para registrar posições anteriores, velocidade do movimento do bounding box e a última vez em que o frame apresentou a caixa delimitadora (`lost_track_buffer`).

### 3. Engine Comportamental `behavior_engine.py`
- **Heatmaps**: Usa o `supervision.HeatMapAnnotator()`, acumulando frames em um buffer decay contínuo, mostrando pontos de lotação na tela.
- **Detecção de Anomalias (Óbitos/Aves Doentes)**: Uma task roda de forma assíncrona calculando a variação euclidiana entre t(0) e t(N) para cada detecção. Identificadores (IDs) que oscilam um $\Delta\text{d} < 5$ pixels por > 300 segundos geram evento CRÍTICO.

### 4. Streaming Gateway `stream_gateway.py` (Rotas Flask)
A rota Flask integrará a captura transformada das anotações em um buffer de saída estruturado.
- Se decidido WebRTC: A rota negocia a API `/offer` onde o Python instancia um `VideoTrack` que gera frames.
- Se HLS: A rota serve o `.m3u8` gerado dinamicamente onde cada bloco (`.ts`) é compilado do resultado da Inferência.

## Verification Plan
1. **Ambiente Isolado**: Escrever e rodar um script de teste simulado `test_pipeline.py` lendo `video_granja.mp4` e medindo o throughput contra o antigo `vision_pipeline.py`.
2. **Verificações de Track**: Assistir a um segmento de 30s de vídeo anotado validando se o "Flickering" que estava no `vision_pipeline.py` original sumiu.
3. **Anomalia Lógica**: Adicionar virtualmente pontuação de inatividade em uma ave específica e observar se o Alarme aciona.
