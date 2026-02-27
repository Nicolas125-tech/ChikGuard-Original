
![Texto Alternativo]("C:\Users\cris_\Downloads\screencapture-localhost-5173-2026-02-26-22_16_46 (1).png")

# ChikGuard

Sistema de monitoramento para criação de frangos usando visão computacional. Este documento fornece as instruções necessárias para configurar e executar os ambientes de backend, frontend e mobile.

## Funcionalidades (Exemplo)

- Monitoramento de comportamento das aves.
- Contagem de aves em tempo real.
- Detecção de anomalias (ex: aves paradas por muito tempo).

## Pré-requisitos

- Python 3.8+
- Node.js 18+
- npm ou yarn
- Expo CLI
- OpenCV
- Cloudflare Tunnel (`cloudflared`)

## Instalação

### Backend

1. Navegue até o diretório do backend:
```bash
cd backend
```

2. Crie um ambiente virtual (opcional mas recomendado):
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```
4. Instale as dependências:

```bash
pip install flask-bcrypt flask-sqlalchemy flask-jwt-extended flask-cors ultralytics opencv-python numpy
```


5. Execute o servidor:
```bash
python app.py
```

O backend estará disponível em `http://localhost:5000`

### Cloudflare Tunnel

1. Instale o `cloudflared` (Windows):

```bash
winget install --id Cloudflare.cloudflared
```

2. Execute o tunnel para a API local:
```bash
cloudflared tunnel --url http://localhost:5000
```
3. Coloque o link HTTPS gerado (ex: `https://<hash>.trycloudflare.com`) na chave IP/URL de login.

### Frontend

1. Navegue até o diretório do frontend:
```bash
cd frontend
```

2. Instale as dependências:
```bash
npm install
```

3. Inicie o servidor de desenvolvimento:
```bash
npm run dev
```

O frontend estará disponível em `http://localhost:5173`

### Mobile

1. Navegue até o diretório mobile:
```bash
cd mobile
```

2. Instale as dependências:
```bash
npm install
```

3. Inicie o Expo:
```bash
npm start
```

4. Escaneie o QR code com o app Expo Go no seu dispositivo móvel.

## Estrutura do Projeto

```
ChikGuard/
├── backend/          # API Flask para processamento de vídeo
├── frontend/         # Aplicação web React + Vite
└── mobile/           # Aplicação mobile React Native + Expo
```
