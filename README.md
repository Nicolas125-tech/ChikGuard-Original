# ChikGuard

Sistema de monitoramento para criação de frangos usando visão computacional.

## Pré-requisitos

- Python 3.8+
- Node.js 18+
- npm ou yarn
- Expo CLI
- OpenCV

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
pip install flask-bcrypt flask-sqlalchemy flask-jwt-extended
```

5. Configure servidor Ngrok:

```bash
ngrok config add-authtoken 1a2b3c4d5e6f7g8h9i0_token_falso_aqui
```
5.1 
```bash
ngrok http 5000
```

6. Execute o servidor:
```bash
python app.py
```

O backend estará disponível em `http://localhost:5000`

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
