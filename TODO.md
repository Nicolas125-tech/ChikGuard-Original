# ChikGuard - Plano de Atualização

## 1. Backend - Corrigir Dependencies
- [x] Adicionar flask-bcrypt ao requirements.txt
- [x] Adicionar flask-jwt-extended ao requirements.txt  
- [x] Adicionar flask-sqlalchemy ao requirements.txt

## 2. Backend - Adicionar Endpoints de Controle
- [x] Criar endpoint POST /api/ventilacao (ligar/desligar)
- [x] Criar endpoint POST /api/aquecedor (ligar/desligar)
- [x] Criar endpoint GET /api/estado-dispositivos

## 3. Frontend - Adicionar Gráfico de Histórico
- [x] Instalar recharts para gráficos
- [x] Criar componente de gráfico de temperaturas
- [x] Integrar com endpoint /api/history

## 4. Frontend - Conectar Controles
- [x] Conectar botões de ventilação/aquecedor aos novos endpoints

## 5. Mobile - Atualizações (se necessário)
- [x] Verificar se precisa de atualizações (Não precisa, já possui as funcionalidades)
