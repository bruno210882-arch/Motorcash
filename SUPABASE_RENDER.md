# MotorCash + Supabase + Render

## 1. Criar banco no Supabase
1. Acesse Supabase e crie um novo projeto.
2. Defina uma senha forte para o banco.
3. Vá em **Project Settings > Database > Connection string**.
4. Copie a string **Direct connection** ou **Session pooler**.

Para Render, comece pela **Direct connection** quando disponível. Se houver problema de IPv6, use a opção **Session pooler** do Supabase.

Exemplo:

```text
postgresql://postgres:SUA_SENHA@db.xxxxxxxxxxxxx.supabase.co:5432/postgres
```

## 2. Configurar no Render
No Web Service do Render, configure:

```text
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
```

Em **Environment Variables**, adicione:

```text
SECRET_KEY=sua-chave-secreta-forte
DATABASE_URL=sua-url-do-supabase
```

## 3. Inicializar tabelas
Depois do deploy, acesse uma vez:

```text
https://SEU-APP.onrender.com/admin/seed
```

Depois acesse:

```text
https://SEU-APP.onrender.com
```

## 4. Observações importantes
- Não suba `motorcash.db` para o GitHub.
- Não suba `.env` para o GitHub.
- O arquivo `.env.example` é só modelo.
- Para Play Store, use a URL HTTPS do Render no Bubblewrap.
