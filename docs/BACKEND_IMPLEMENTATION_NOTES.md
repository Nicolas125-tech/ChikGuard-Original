# Implementation Plan: ChikGuard Enterprise CV Pipeline (Project Spy-Level)

Este documento detalha o desenho da nova arquitetura State-of-the-Art (SOTA) para o motor de visão computacional do ChikGuard. O objetivo é substituir processamentos legados por algoritmos preditivos de nível militar, otimizados para Edge Computing e baixa latência.

## Arquitetura e Tecnologias (Visão Geral do Arquiteto)

Para alcançar os requisitos exigidos, o sistema será modularizado:
1. **Inference Core**: Substituição dos tensores brutos por modelos otimizados (YOLOv10 ou RT-DETR), empacotados usando **ONNX Runtime (otimizado via TensorRT)** para extração máxima de frames por segundo (FPS) no edge hardware.
2. **Tracker Avançado**: Integração profunda com **ByteTrack** (via `supervision`) mantendo alta persistência temporal sobre os IDs das aves, superando oclusões severas.
3. **Módulo Comportamental (Inteligência Cinetica)**: Análise contínua das variações vetoriais, gerando **Heatmaps Cinetizados** e disparando heurísticas de detecção de anomalias (como imobilidade crônica).
4. **Streaming de Baixa Latência**: Substituição do MJPEG cru (M-JPEG over HTTP) por um servidor de streaming **WebRTC** (ou, alternativamente, **HLS** in-memory) gerenciado pelo ecossistema Flask.

---

> [!IMPORTANT]
> **User Review Required**
> Como estamos alterando o paradigma crítico de streaming de vídeo nativo (bytes crus) para WebRTC / HLS no Flask, precisarei da sua escolha:
> 
> 1. **WebRTC (`aiortc`)**: Menor latência (~200ms), "Tempo Real" absoluto, mas exige refatoração no front-end para negociar conexões (SDP, ICE candidatos).
> 2. **HLS In-Memory**: Latência ligeiramente maior (~2-5s), mas compatibilidade universal (o React precisará apenas de uma tag de vídeo ou player HLS padrão, como HLS.js), além de ser perfeitamente atendido e balanceado pelo Flask.
>
> Recomendação Policial/Militar: HLS com fragmentos curtos via RAM se for focado em dashboards complexos, WebRTC se focarmos em resposta instantânea em guarita de monitoramento.

---

## Estrutura Modular Proposta

O código não ficará misturado. A arquitetura de pastas desenhada:
```
backend/src/cv_master/
├── __init__.py
├── inference_sota.py      # (Motor TensorRT/ONNX + YOLOv10/RT-DETR + SAHI)
├── tracker_spy.py         # (Motor ByteTrack de retenção de memória multialvo)
├── behavior_engine.py     # (Heatmaps Contínuos + Vetor Identitário de imobilidade)
└── stream_gateway.py      # (Integração de WebRTC/HLS com o Flask)
```

### 1. Motor de Inferência `inference_sota.py`
Carregamento delegado para ONNX Runtime (com `providers=['TensorrtExecutionProvider', 'CUDAExecutionProvider']`).
Garante que o modelo trabalhe acoplado à GPU. Lógica baseada nas mais novas SDKs Python.

### 2. Tracker Nível Espião `tracker_spy.py`
Será utilizado `sv.ByteTrack` nativo com buffers ajustados agressivamente para lidar com o ambiente orgânico (onde as aves se movem de forma caótica e sobreposta). As chaves de rastreamento são as identificações. Manteremos um dict local para registrar posições anteriores, velocidade do movimento do bounding box e a última vez em que o frame apresentou a caixa delimitadora (`lost_track_buffer` elevado).

### 3. Engine Comportamental `behavior_engine.py`
- **Heatmaps**: Usa o `supervision.HeatMapAnnotator()`, acumulando frames em um buffer decay (esmaecimento) contínuo, mostrando pontos de sobre-lotação quentes na tela.
- **Detecção de Anomalias (Óbitos/Aves Doentes)**: Uma task roda de forma assíncrona calculando a variação euclidiana entre t(0) e t(N) para cada detecção. Identificadores (IDs) que oscilam um $\Delta\text{d} < 5$ pixels por > 300 segundos geram evento CRÍTICO.

### 4. Streaming Gateway `stream_gateway.py` (Rotas Flask)
A rota Flask integrará a captura transformada das anotações em um buffer de saída estruturado.
- Se decidido WebRTC: Rota negocia a API `/offer` onde o Python instancia um `VideoTrack` que gera frames.
- Se HLS: Rota serve o `.m3u8` gerado dinamicamente onde cada bloco (`.ts`) é compilado do resultado da Inferência.

## Verification Plan
1. **Ambiente Isolado**: Escrever e rodar um script de teste simulado `test_sota_pipeline.py` lendo `video_granja.mp4` e medindo o throughput absoluto contra o antigo `vision_pipeline.py`.
2. **Verificações de Track**: Assistir a um segmento de 30s de vídeo anotado validando se o "Flickering" que estava no `vision_pipeline.py` original sumiu.
3. **Anomalia Lógica**: Adicionar virtualmente pontuação de inatividade em uma ave específica e observar se o Trigger de Alarme aciona.
