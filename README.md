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

- Python 3.12 (ou superior)
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
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

3. Instale dependencias:

```bash
pip install -r requirements.txt
```

4. Configure o ambiente:

```bash
# Windows
copy .env.example .env

# Linux/macOS
cp .env.example .env
```

**Nota de Seguranca:** O backend enforce uma politica estrita de inicializacao para a conta do administrador. Certifique-se que variaveis sensiveis como `ADMIN_PASSWORD` estao preenchidas no seu `.env` antes da primeira inicializacao, ou ele podera falhar.

5. Rode a API (garantindo que o PYTHONPATH enxergue o pacote `src/`):

```bash
# Windows (PowerShell)
$env:PYTHONPATH="." ; python app.py

# Linux/macOS
PYTHONPATH=. python3 app.py
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

- `GET /api/summary` - Resumo em tempo real do sistema (CV + Sensores).
- `GET /api/system-info` - Status interno e recursos em execucao.
- `GET /api/sensors/live` - Leitura atual dos sensores (temperatura, umidade, amonia).
- `POST /api/auto-mode` - Alterar ou consultar automacoes da FSM.
- `POST /api/reports/esg` - Gera Relatorio de Conformidade ESG em PDF.
- `GET /api/accounts/me` - Retorna detalhes do usuario logado (sujeito a RBAC).
- `POST /api/webrtc/offer` - Handshake de transmissao de video ao vivo (aiortc).

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
