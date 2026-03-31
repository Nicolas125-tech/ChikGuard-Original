# Configuração do Supabase OAuth na Vercel

Se você está recebendo erros ao fazer login com o Google, siga os passos abaixo para resolver o problema de redirecionamento.

## 1. No painel do Google Cloud Console
- Vá para "APIs e Serviços" -> "Credenciais".
- Edite o seu "ID do cliente OAuth 2.0" (Aplicativo da Web).
- Na seção **URIs de redirecionamento autorizados**, adicione a URL do seu Supabase com `/auth/v1/callback` no final.
  - Exemplo: `https://seu-projeto.supabase.co/auth/v1/callback`

## 2. No painel do Supabase
- Acesse `Authentication` -> `URL Configuration`.
- Defina o **Site URL** como: `https://chik-guard-original.vercel.app`
- Adicione as **Redirect URLs**:
  - `https://chik-guard-original.vercel.app`
  - `http://localhost:5173` (para funcionar quando rodar local)

## 3. Na Vercel
- Acesse o seu projeto na Vercel e vá em `Settings` -> `Environment Variables`.
- Certifique-se de que definiu as 3 variáveis:
  - `VITE_SUPABASE_URL` (Sua URL do Supabase)
  - `VITE_SUPABASE_ANON_KEY` (Sua chave pública anon do Supabase)
  - `VITE_SITE_URL=https://chik-guard-original.vercel.app` (Para forçar o redirecionamento para o Vercel)
- Após alterar as variáveis, você precisará fazer um novo **Deploy** para aplicá-las (ou redeploy do último commit).
