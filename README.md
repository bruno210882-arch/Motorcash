# MotorCash

Aplicativo SaaS em Flask para motoristas de aplicativo controlarem ganhos, gastos, metas e lucro real.

## Recursos
- Cadastro e login
- Dashboard com lucro do dia, da semana e do mês
- Ganho por hora, ganho por km, lucro por hora e lucro por km
- Lançamento de ganhos e gastos
- Metas e reservas mensais
- PWA instalável no celular
- Estrutura de planos Free, Pro e Premium
- Banco SQLite local e PostgreSQL no Render

## Como rodar localmente
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
python app.py
```

Depois abra:
- http://127.0.0.1:5000/admin/seed
- http://127.0.0.1:5000

## Deploy no Render
1. Suba os arquivos para um repositório GitHub.
2. Crie um Web Service no Render.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Adicione as variáveis:
   - `SECRET_KEY`
   - `DATABASE_URL`

## Próximos passos comerciais
- Integrar Stripe, Mercado Pago ou Asaas para cobrança recorrente
- Implementar período de teste gratuito
- Criar exportação PDF e painel administrativo de assinantes
- Adicionar onboarding guiado e notificações push


## Atualização: Jornada automática

Esta versão inclui a tela **Iniciar/Finalizar dia**. O motorista informa o KM inicial no começo do expediente e o KM final ao encerrar. O sistema registra os horários automaticamente e calcula KM rodados e horas trabalhadas no dashboard.

Se você já testou uma versão anterior com SQLite local, apague `instance/motorcash.db` e acesse `/init-db` novamente para criar a nova tabela `daily_shift`.
