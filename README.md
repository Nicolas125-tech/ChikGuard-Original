# ChikGuard

Sistema de monitoramento para criacao de frangos com visao computacional.

## Funcionalidades

- Monitoramento de comportamento das aves.
- Contagem de aves em tempo real.
- Deteccao de anomalias.
- API para frontend web e app mobile.

## Arquitetura Atual

```text
ChikGuard/
|- backend/
|  |- app.py (Entrypoint principal)
|  |- plugins/
|  |  |- face_recognition/
|  |  |- weapon_detection/
|  |  |- fire_detection/
|  |- src/
|  |  |- api/
|  |  |  |- auth.py (Rotas de Contas e Permissoes)
|  |  |  |- devices.py (Rotas de Atuadores e Automacao)
|  |  |  |- reports_api.py (Rotas de Relatorios PDF)
|  |  |  |- routes.py (Rotas de WebRTC)
|  |  |  |- sensors_api.py (Rotas de Sensores e Anomalias)
|  |  |- core/
|  |  |  |- config.py
|  |  |  |- logger.py
|  |  |- plugins/
|  |     |- manager.py
|  |     |- base.py
|  |  |- reports/
|  |     |- generator.py (Geracao de PDF com ReportLab)
|  |  |- alerts/
|  |     |- providers.py
|  |- tests/
|- frontend/
|- mobile/
```

## Pre-requisitos

- Python 3.11+
- Node.js 18+
- npm ou yarn
- Docker e Docker Compose (opcional, recomendado)

## Backend (execucao local)

1. Entre na pasta:

```bash
cd backend
```

2. Crie e ative um ambiente virtual:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Instale dependencias:

```bash
pip install -r requirements.txt
```

4. Configure ambiente:

```bash
copy .env.example .env
```

5. Rode a API:

```bash
python app.py
```

API padrao: `http://localhost:5000`

## Docker (padronizado)

Na raiz do projeto:

```bash
docker-compose up --build
```

Servico backend exposto em `http://localhost:5000`.

## Testes

Na raiz do projeto:

```bash
python -m pytest backend/tests -q
```

## Endpoints importantes

- `GET /api/health`
- `GET /api/runtime-status`
- `GET /api/plugins`
- `POST /api/plugins/reload`
- `POST /api/login`
- `GET /api/status`
- `GET /api/history`
- `GET /api/video`

## Sistema de plugins

Cada plugin fica em `backend/plugins/<nome>/plugin.py` e expoe uma funcao `register()`.

Exemplo minimo:

```python
from src.plugins.base import PluginBase, PluginInfo

class MyPlugin(PluginBase):
    info = PluginInfo(name="my_plugin", version="0.1.0", description="example")

def register():
    return MyPlugin()
```

## Frontend e Mobile

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Mobile

```bash
cd mobile
npm install
npm start
```
