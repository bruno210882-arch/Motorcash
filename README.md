# MotorCash - Versão Play Store

Aplicativo SaaS em Flask/PWA/TWA para motoristas de aplicativo controlarem ganhos, gastos, jornada, metas e lucro real.

## Planos comerciais
- Essencial: R$ 9,90/mês
- Profissional: R$ 19,90/mês
- Premium: R$ 29,90/mês

Não existe versão grátis nesta edição.

## Recursos
- Cadastro e login
- Escolha de plano no cadastro
- Dashboard com lucro do dia, semana e mês
- Jornada automática: KM inicial + hora inicial automática; KM final + hora final automática
- Ganho por hora, ganho por km, lucro por hora e lucro por km
- Lançamento de ganhos e gastos
- Metas e reservas mensais
- Páginas obrigatórias para Play Store: privacidade, termos e exclusão de conta
- PWA instalável com manifest e ícones PNG 192/512
- Preparado para empacotar como TWA/Android via Bubblewrap

## Rodar local
```bash
pip install -r requirements.txt
python app.py
```
Acesse:
- http://127.0.0.1:5000/admin/seed
- http://127.0.0.1:5000

## Deploy no Render
Build command:
```bash
pip install -r requirements.txt
```
Start command:
```bash
gunicorn app:app
```
Variáveis:
- SECRET_KEY
- DATABASE_URL

## Play Store
Veja a pasta `playstore/` com descrição, checklist, política de privacidade e instruções para Bubblewrap.

## Importante
A cobrança real ainda precisa ser conectada ao Mercado Pago, Stripe ou Asaas. O seletor de plano está pronto no app, mas a ativação automática por pagamento depende do token e webhook da sua conta de pagamentos.
