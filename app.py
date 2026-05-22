from __future__ import annotations

import os
from collections import defaultdict
from datetime import date, datetime, timedelta
from functools import wraps

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, inspect, text
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db = SQLAlchemy()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "motorcash_super_secret_change_me")
    db_url = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'motorcash.db')}")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    vehicle_type = db.Column(db.String(50), default="Carro")
    main_platform = db.Column(db.String(50), default="Uber")
    plan = db.Column(db.String(20), default="basic")
    plan_expires_at = db.Column(db.DateTime)
    city = db.Column(db.String(80))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    goal = db.relationship("Goal", backref="user", uselist=False, cascade="all, delete-orphan")
    entries = db.relationship("IncomeEntry", backref="user", cascade="all, delete-orphan")
    expenses = db.relationship("ExpenseEntry", backref="user", cascade="all, delete-orphan")
    shifts = db.relationship("DailyShift", backref="user", cascade="all, delete-orphan")
    companies = db.relationship("Company", backref="user", cascade="all, delete-orphan")
    maintenance_items = db.relationship("MaintenanceItem", backref="user", cascade="all, delete-orphan")

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    @property
    def plan_is_active(self) -> bool:
        return self.plan_expires_at is None or self.plan_expires_at >= datetime.utcnow()

    @property
    def is_pro(self) -> bool:
        return self.plan in {"pro", "premium"} and self.plan_is_active

    @property
    def is_premium(self) -> bool:
        return self.plan == "premium" and self.plan_is_active


class Goal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, unique=True)
    daily_goal = db.Column(db.Float, default=300.0)
    weekly_goal = db.Column(db.Float, default=1800.0)
    monthly_goal = db.Column(db.Float, default=7200.0)
    fuel_consumption_km_l = db.Column(db.Float, default=10.0)
    fixed_cost_monthly = db.Column(db.Float, default=0.0)
    maintenance_reserve_monthly = db.Column(db.Float, default=0.0)
    tax_reserve_pct = db.Column(db.Float, default=0.0)


class Voucher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(50), unique=True, nullable=False, index=True)
    plan = db.Column(db.String(20), default="premium")
    days = db.Column(db.Integer, default=180)
    usado = db.Column(db.Boolean, default=False)
    usado_por_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    usado_em = db.Column(db.DateTime)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)



class Company(db.Model):
    """Empresa/plataforma em que o motorista trabalha.

    user_id nulo = empresa padrão global disponível para todos.
    user_id preenchido = empresa personalizada do motorista.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True, index=True)
    name = db.Column(db.String(80), nullable=False)
    logo_url = db.Column(db.String(255), default="")
    category = db.Column(db.String(40), default="Aplicativo")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class MaintenanceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(180), default="")
    due_km = db.Column(db.Float)
    due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default="aberto")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class IncomeEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company.id"), nullable=True, index=True)
    company = db.relationship("Company")
    platform = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(150), default="")
    amount = db.Column(db.Float, nullable=False)
    km = db.Column(db.Float, default=0.0)
    hours = db.Column(db.Float, default=0.0)
    entry_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ExpenseEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(150), default="")
    amount = db.Column(db.Float, nullable=False)
    entry_date = db.Column(db.Date, nullable=False, default=date.today)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class DailyShift(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    shift_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    start_km = db.Column(db.Float, nullable=False)
    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_km = db.Column(db.Float)
    end_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def is_open(self) -> bool:
        return self.end_time is None

    @property
    def km_total(self) -> float:
        if self.end_km is None:
            return 0.0
        return max(float(self.end_km) - float(self.start_km), 0.0)

    @property
    def hours_total(self) -> float:
        if self.end_time is None or self.start_time is None:
            return 0.0
        seconds = (self.end_time - self.start_time).total_seconds()
        return max(seconds / 3600, 0.0)


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    body = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


PLATFORMS = ["Uber", "99", "inDrive", "Particular", "Entrega", "Outro"]

DEFAULT_COMPANIES = [
    {"name": "Uber", "category": "Aplicativo", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/c/cc/Uber_logo_2018.png"},
    {"name": "99", "category": "Aplicativo", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/8/8f/99app_logo.png"},
    {"name": "inDrive", "category": "Aplicativo", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/9/9f/InDrive_Logo.png"},
    {"name": "Particular", "category": "Particular", "logo_url": ""},
    {"name": "Entrega", "category": "Entrega", "logo_url": ""},
]

EXPENSE_CATEGORIES = [
    "Combustível",
    "Manutenção",
    "Seguro",
    "Aluguel/Parcela",
    "Pedágio",
    "Alimentação",
    "Lavagem",
    "Outros",
]
PLANS = {
    "basic": {
        "name": "Essencial",
        "price": "R$ 9,90/mês",
        "features": [
            "Dashboard financeiro diário",
            "Jornada automática com KM e horas",
            "Ganhos e gastos ilimitados",
            "Resumo de lucro real",
        ],
    },
    "pro": {
        "name": "Profissional",
        "price": "R$ 19,90/mês",
        "features": [
            "Tudo do Essencial",
            "Metas diária, semanal e mensal",
            "Indicadores por KM e por hora",
            "Reserva de manutenção",
            "Relatórios avançados",
        ],
    },
    "premium": {
        "name": "Premium",
        "price": "R$ 29,90/mês",
        "features": [
            "Tudo do Profissional",
            "Insights inteligentes",
            "Voucher de teste premium por 6 meses",
            "Reserva de imposto configurável",
            "Prioridade no suporte",
        ],
    },
}



def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    os.makedirs(os.path.join(BASE_DIR, "instance"), exist_ok=True)
    db.init_app(app)

    @app.context_processor
    def inject_globals():
        current_user = get_current_user()
        return {
            "current_user": current_user,
            "plans": PLANS,
            "today": date.today(),
            "year": date.today().year,
        }

    @app.route("/manifest.json")
    def manifest():
        return send_from_directory(os.path.join(BASE_DIR, "static"), "manifest.json", mimetype="application/manifest+json")

    @app.route("/service-worker.js")
    def service_worker():
        return send_from_directory(os.path.join(BASE_DIR, "static"), "service-worker.js", mimetype="application/javascript")

    @app.route("/admin/criar-vouchers")
    def criar_vouchers():
        ensure_schema()
        codigos = ["MOTORVIP1", "MOTORVIP2", "MOTORVIP3"]
        criados = []
        existentes = []
        for codigo in codigos:
            if Voucher.query.filter_by(codigo=codigo).first():
                existentes.append(codigo)
                continue
            db.session.add(Voucher(codigo=codigo, plan="premium", days=180))
            criados.append(codigo)
        db.session.commit()
        return (
            "Vouchers premium de 6 meses configurados.<br>"
            f"Criados agora: {', '.join(criados) if criados else 'nenhum'}<br>"
            f"Já existiam: {', '.join(existentes) if existentes else 'nenhum'}<br>"
            "Códigos: MOTORVIP1, MOTORVIP2, MOTORVIP3"
        )

    @app.route("/")
    def index():
        if not is_logged_in():
            return redirect(url_for("landing"))
        return redirect(url_for("dashboard"))

    @app.route("/landing")
    def landing():
        announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.created_at.desc()).limit(3).all()
        return render_template("landing.html", announcements=announcements)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            selected_plan = request.form.get("plan", "basic")
            selected_plan = selected_plan if selected_plan in PLANS else "basic"

            if not email or not password or not request.form.get("name"):
                flash("Preencha nome, e-mail e senha.", "danger")
                return redirect(url_for("register"))
            if User.query.filter_by(email=email).first():
                flash("Esse e-mail já está cadastrado.", "warning")
                return redirect(url_for("register"))

            voucher_codigo = request.form.get("voucher", "").strip().upper()
            voucher = None
            if voucher_codigo:
                voucher = Voucher.query.filter_by(codigo=voucher_codigo, usado=False).first()
                if not voucher:
                    flash("Voucher inválido ou já utilizado.", "danger")
                    return redirect(url_for("register"))
                selected_plan = voucher.plan or "premium"

            user = User(
                name=request.form.get("name", "").strip(),
                email=email,
                phone=request.form.get("phone", "").strip(),
                city=request.form.get("city", "").strip(),
                vehicle_type=request.form.get("vehicle_type", "Carro"),
                main_platform=request.form.get("main_platform", "Uber"),
                plan=selected_plan,
            )

            if voucher:
                user.plan_expires_at = datetime.utcnow() + timedelta(days=voucher.days or 180)

            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            if voucher:
                voucher.usado = True
                voucher.usado_por_id = user.id
                voucher.usado_em = datetime.utcnow()

            goal = Goal(
                user_id=user.id,
                daily_goal=parse_float(request.form.get("daily_goal"), 300),
                weekly_goal=parse_float(request.form.get("weekly_goal"), 1800),
                monthly_goal=parse_float(request.form.get("monthly_goal"), 7200),
                fuel_consumption_km_l=parse_float(request.form.get("fuel_consumption_km_l"), 10),
                fixed_cost_monthly=parse_float(request.form.get("fixed_cost_monthly"), 0),
                maintenance_reserve_monthly=parse_float(request.form.get("maintenance_reserve_monthly"), 0),
                tax_reserve_pct=parse_float(request.form.get("tax_reserve_pct"), 0),
            )
            db.session.add(goal)
            db.session.commit()

            if voucher:
                flash("Cadastro realizado com voucher Premium válido por 6 meses. Faça login para continuar.", "success")
            else:
                flash("Cadastro realizado com sucesso. Finalize o pagamento do plano escolhido para liberar o acesso.", "success")
            return redirect(url_for("login"))
        return render_template("register.html", platforms=PLATFORMS)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            user = User.query.filter_by(email=email, is_active=True).first()
            if not user or not user.check_password(password):
                flash("E-mail ou senha inválidos.", "danger")
                return redirect(url_for("login"))
            session["user_id"] = user.id
            flash("Bem-vindo ao MotorCash.", "success")
            return redirect(url_for("dashboard"))
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Sessão encerrada.", "info")
        return redirect(url_for("landing"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        user = get_current_user()
        metrics = get_metrics(user)
        announcements = Announcement.query.filter_by(is_active=True).order_by(Announcement.created_at.desc()).limit(3).all()
        return render_template("dashboard.html", metrics=metrics, announcements=announcements)

    @app.route("/jornada", methods=["GET", "POST"])
    @login_required
    def shift_day():
        user = get_current_user()
        today_shift = get_today_shift(user.id)
        if request.method == "POST":
            action = request.form.get("action")
            if action == "start":
                if today_shift and today_shift.is_open:
                    flash("Você já iniciou o dia. Finalize antes de iniciar outro.", "warning")
                    return redirect(url_for("shift_day"))
                start_km = parse_float(request.form.get("start_km"), 0)
                if start_km <= 0:
                    flash("Informe a quilometragem inicial para começar o dia.", "danger")
                    return redirect(url_for("shift_day"))
                shift = DailyShift(user_id=user.id, shift_date=date.today(), start_km=start_km, start_time=datetime.utcnow())
                db.session.add(shift)
                db.session.commit()
                flash("Dia iniciado. A hora inicial foi registrada automaticamente.", "success")
                return redirect(url_for("dashboard"))
            if action == "finish":
                if not today_shift or not today_shift.is_open:
                    flash("Nenhum dia aberto para finalizar.", "warning")
                    return redirect(url_for("shift_day"))
                end_km = parse_float(request.form.get("end_km"), 0)
                if end_km < today_shift.start_km:
                    flash("O KM final não pode ser menor que o KM inicial.", "danger")
                    return redirect(url_for("shift_day"))
                today_shift.end_km = end_km
                today_shift.end_time = datetime.utcnow()
                db.session.commit()
                flash("Dia finalizado. KM rodado e horas trabalhadas foram calculados automaticamente.", "success")
                return redirect(url_for("dashboard"))
        history = DailyShift.query.filter_by(user_id=user.id).order_by(DailyShift.shift_date.desc(), DailyShift.id.desc()).limit(30).all()
        return render_template("jornada.html", shift=today_shift, history=history)

    @app.route("/ganhos", methods=["GET", "POST"])
    @login_required
    def incomes():
        user = get_current_user()
        companies = get_available_companies(user.id)
        if request.method == "POST":
            company_id = request.form.get("company_id", type=int)
            company = get_company_for_user(company_id, user.id) if company_id else None
            platform = company.name if company else request.form.get("platform", "Outro")
            entry = IncomeEntry(
                user_id=user.id,
                company_id=company.id if company else None,
                platform=platform,
                description=request.form.get("description", "").strip(),
                amount=parse_float(request.form.get("amount"), 0),
                km=parse_float(request.form.get("km"), 0),
                hours=parse_float(request.form.get("hours"), 0),
                entry_date=parse_date(request.form.get("entry_date")) or date.today(),
            )
            db.session.add(entry)
            db.session.commit()
            flash("Ganho lançado com sucesso.", "success")
            return redirect(url_for("incomes"))

        entries = IncomeEntry.query.filter_by(user_id=user.id).order_by(IncomeEntry.entry_date.desc(), IncomeEntry.id.desc()).all()
        return render_template("ganhos.html", entries=entries, platforms=PLATFORMS, companies=companies)


    @app.route("/empresas", methods=["GET", "POST"])
    @login_required
    def companies_page():
        user = get_current_user()
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            if not name:
                flash("Informe o nome da empresa/plataforma.", "danger")
                return redirect(url_for("companies_page"))
            company = Company(
                user_id=user.id,
                name=name,
                category=request.form.get("category", "Aplicativo").strip() or "Aplicativo",
                logo_url=request.form.get("logo_url", "").strip(),
                is_active=True,
            )
            db.session.add(company)
            db.session.commit()
            flash("Empresa adicionada com sucesso.", "success")
            return redirect(url_for("companies_page"))
        companies = get_available_companies(user.id, include_inactive=True)
        return render_template("empresas.html", companies=companies)

    @app.route("/empresas/<int:company_id>/toggle", methods=["POST"])
    @login_required
    def toggle_company(company_id: int):
        user = get_current_user()
        company = Company.query.filter_by(id=company_id, user_id=user.id).first_or_404()
        company.is_active = not company.is_active
        db.session.commit()
        flash("Status da empresa atualizado.", "success")
        return redirect(url_for("companies_page"))

    @app.route("/manutencoes", methods=["GET", "POST"])
    @login_required
    def maintenance_page():
        user = get_current_user()
        if request.method == "POST":
            item = MaintenanceItem(
                user_id=user.id,
                title=request.form.get("title", "").strip() or "Manutenção",
                description=request.form.get("description", "").strip(),
                due_km=parse_float(request.form.get("due_km"), 0) or None,
                due_date=parse_date(request.form.get("due_date")),
                status="aberto",
            )
            db.session.add(item)
            db.session.commit()
            flash("Alerta de manutenção salvo.", "success")
            return redirect(url_for("maintenance_page"))
        items = MaintenanceItem.query.filter_by(user_id=user.id).order_by(MaintenanceItem.status, MaintenanceItem.due_date.asc().nullslast()).all()
        current_km = get_current_vehicle_km(user.id)
        return render_template("manutencoes.html", items=items, current_km=current_km)

    @app.route("/manutencoes/<int:item_id>/concluir", methods=["POST"])
    @login_required
    def finish_maintenance(item_id: int):
        user = get_current_user()
        item = MaintenanceItem.query.filter_by(id=item_id, user_id=user.id).first_or_404()
        item.status = "concluido"
        db.session.commit()
        flash("Manutenção marcada como concluída.", "success")
        return redirect(url_for("maintenance_page"))

    @app.route("/gastos", methods=["GET", "POST"])
    @login_required
    def expenses():
        user = get_current_user()
        if request.method == "POST":
            entry = ExpenseEntry(
                user_id=user.id,
                category=request.form.get("category", "Outros"),
                description=request.form.get("description", "").strip(),
                amount=parse_float(request.form.get("amount"), 0),
                entry_date=parse_date(request.form.get("entry_date")) or date.today(),
            )
            db.session.add(entry)
            db.session.commit()
            flash("Gasto lançado com sucesso.", "success")
            return redirect(url_for("expenses"))

        entries = ExpenseEntry.query.filter_by(user_id=user.id).order_by(ExpenseEntry.entry_date.desc(), ExpenseEntry.id.desc()).all()
        return render_template("gastos.html", entries=entries, categories=EXPENSE_CATEGORIES)

    @app.route("/metas", methods=["GET", "POST"])
    @login_required
    def goals():
        user = get_current_user()
        goal = user.goal or Goal(user_id=user.id)
        if request.method == "POST":
            goal.daily_goal = parse_float(request.form.get("daily_goal"), goal.daily_goal)
            goal.weekly_goal = parse_float(request.form.get("weekly_goal"), goal.weekly_goal)
            goal.monthly_goal = parse_float(request.form.get("monthly_goal"), goal.monthly_goal)
            goal.fuel_consumption_km_l = parse_float(request.form.get("fuel_consumption_km_l"), goal.fuel_consumption_km_l)
            goal.fixed_cost_monthly = parse_float(request.form.get("fixed_cost_monthly"), goal.fixed_cost_monthly)
            goal.maintenance_reserve_monthly = parse_float(request.form.get("maintenance_reserve_monthly"), goal.maintenance_reserve_monthly)
            if user.is_premium:
                goal.tax_reserve_pct = parse_float(request.form.get("tax_reserve_pct"), goal.tax_reserve_pct)
            db.session.add(goal)
            db.session.commit()
            flash("Metas atualizadas com sucesso.", "success")
            return redirect(url_for("goals"))
        metrics = get_metrics(user)
        return render_template("metas.html", goal=goal, metrics=metrics)

    @app.route("/relatorios")
    @login_required
    def reports():
        user = get_current_user()
        metrics = get_metrics(user)
        return render_template("relatorios.html", metrics=metrics)

    @app.route("/planos", methods=["GET", "POST"])
    @login_required
    def plans_page():
        user = get_current_user()
        if request.method == "POST":
            selected_plan = request.form.get("plan")
            if selected_plan in PLANS:
                user.plan = selected_plan
                db.session.commit()
                flash(f"Plano atualizado para {PLANS[selected_plan]['name']}. Integre sua cobrança real depois.", "success")
            return redirect(url_for("plans_page"))
        return render_template("planos.html")

    @app.route("/perfil", methods=["GET", "POST"])
    @login_required
    def profile():
        user = get_current_user()
        if request.method == "POST":
            user.name = request.form.get("name", user.name).strip()
            user.phone = request.form.get("phone", user.phone).strip()
            user.city = request.form.get("city", user.city).strip()
            user.vehicle_type = request.form.get("vehicle_type", user.vehicle_type).strip()
            user.main_platform = request.form.get("main_platform", user.main_platform).strip()
            db.session.commit()
            flash("Perfil atualizado.", "success")
            return redirect(url_for("profile"))
        return render_template("perfil.html", platforms=PLATFORMS)

    @app.route("/entry/delete/<string:kind>/<int:entry_id>", methods=["POST"])
    @login_required
    def delete_entry(kind: str, entry_id: int):
        user = get_current_user()
        model = IncomeEntry if kind == "income" else ExpenseEntry
        entry = model.query.filter_by(id=entry_id, user_id=user.id).first_or_404()
        db.session.delete(entry)
        db.session.commit()
        flash("Lançamento removido.", "info")
        return redirect(request.referrer or url_for("dashboard"))


    @app.route("/admin/migrar")
    def admin_migrar():
        ensure_schema()
        seed_default_companies()
        return "Migração executada com sucesso. Tabelas e colunas novas garantidas."

    @app.route("/admin/seed")
    def admin_seed():
        ensure_schema()
        seed_default_companies()
        if Announcement.query.count() == 0:
            db.session.add_all(
                [
                    Announcement(title="Sem plano grátis", body="O MotorCash agora trabalha apenas com planos pagos: Essencial, Profissional e Premium.", is_active=True),
                    Announcement(title="Venda consultiva", body="Ofereça o app como copiloto financeiro do motorista, não só como controle de gastos.", is_active=True),
                    Announcement(title="PWA pronto", body="Este projeto já pode ser instalado no celular como aplicativo.", is_active=True),
                ]
            )
            db.session.commit()
        return "Banco inicializado com sucesso."

    return app


def parse_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    value = value.replace("R$", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(value)
    except ValueError:
        return default


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def is_logged_in() -> bool:
    return bool(session.get("user_id"))


def get_current_user() -> User | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not is_logged_in():
            flash("Faça login para continuar.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapper


def get_metrics(user: User) -> dict:
    today = date.today()
    start_week = today - timedelta(days=today.weekday())
    start_month = today.replace(day=1)

    income_today = sum_amount(IncomeEntry, user.id, today, today)
    expense_today = sum_amount(ExpenseEntry, user.id, today, today)
    income_week = sum_amount(IncomeEntry, user.id, start_week, today)
    expense_week = sum_amount(ExpenseEntry, user.id, start_week, today)
    income_month = sum_amount(IncomeEntry, user.id, start_month, today)
    expense_month = sum_amount(ExpenseEntry, user.id, start_month, today)

    total_km_today = sum_shift_km(user.id, today, today)
    total_hours_today = sum_shift_hours(user.id, today, today)
    total_km_month = sum_shift_km(user.id, start_month, today)
    total_hours_month = sum_shift_hours(user.id, start_month, today)

    # Compatibilidade com lançamentos antigos: usa km/horas manuais apenas se ainda não houver jornada.
    if total_km_today == 0:
        total_km_today = sum_numeric(IncomeEntry, user.id, "km", today, today)
    if total_hours_today == 0:
        total_hours_today = sum_numeric(IncomeEntry, user.id, "hours", today, today)
    if total_km_month == 0:
        total_km_month = sum_numeric(IncomeEntry, user.id, "km", start_month, today)
    if total_hours_month == 0:
        total_hours_month = sum_numeric(IncomeEntry, user.id, "hours", start_month, today)

    today_shift = get_today_shift(user.id)

    profit_today = income_today - expense_today
    profit_week = income_week - expense_week
    profit_month = income_month - expense_month

    daily_goal = user.goal.daily_goal if user.goal else 300
    weekly_goal = user.goal.weekly_goal if user.goal else 1800
    monthly_goal = user.goal.monthly_goal if user.goal else 7200
    fixed_cost_monthly = user.goal.fixed_cost_monthly if user.goal else 0
    maintenance_reserve = user.goal.maintenance_reserve_monthly if user.goal else 0
    tax_reserve_pct = user.goal.tax_reserve_pct if user.goal else 0

    suggested_tax_reserve = (profit_month * tax_reserve_pct / 100) if user.is_premium else 0
    real_month_profit_after_reserves = profit_month - fixed_cost_monthly - maintenance_reserve - suggested_tax_reserve

    by_platform = defaultdict(float)
    for platform, amount in (
        db.session.query(IncomeEntry.platform, func.sum(IncomeEntry.amount))
        .filter(IncomeEntry.user_id == user.id, IncomeEntry.entry_date >= start_month, IncomeEntry.entry_date <= today)
        .group_by(IncomeEntry.platform)
        .all()
    ):
        by_platform[platform] = float(amount or 0)

    by_company = defaultdict(float)
    for company_name, amount in (
        db.session.query(func.coalesce(Company.name, IncomeEntry.platform), func.sum(IncomeEntry.amount))
        .outerjoin(Company, IncomeEntry.company_id == Company.id)
        .filter(IncomeEntry.user_id == user.id, IncomeEntry.entry_date >= start_month, IncomeEntry.entry_date <= today)
        .group_by(func.coalesce(Company.name, IncomeEntry.platform))
        .all()
    ):
        by_company[company_name or "Outros"] = float(amount or 0)

    by_category = defaultdict(float)
    for category, amount in (
        db.session.query(ExpenseEntry.category, func.sum(ExpenseEntry.amount))
        .filter(ExpenseEntry.user_id == user.id, ExpenseEntry.entry_date >= start_month, ExpenseEntry.entry_date <= today)
        .group_by(ExpenseEntry.category)
        .all()
    ):
        by_category[category] = float(amount or 0)

    daily_points = []
    for i in range(6, -1, -1):
        current_day = today - timedelta(days=i)
        inc = sum_amount(IncomeEntry, user.id, current_day, current_day)
        exp = sum_amount(ExpenseEntry, user.id, current_day, current_day)
        daily_points.append(
            {
                "label": current_day.strftime("%d/%m"),
                "income": round(inc, 2),
                "expense": round(exp, 2),
                "profit": round(inc - exp, 2),
            }
        )

    insights = []
    if profit_today <= 0 and (income_today > 0 or expense_today > 0):
        insights.append("Hoje o lucro ficou zerado ou negativo. Revise combustível, pedágio e despesas rápidas.")
    if total_hours_today > 0 and income_today > 0:
        income_per_hour = income_today / max(total_hours_today, 1)
        insights.append(f"Seu ganho bruto por hora hoje está em R$ {income_per_hour:.2f}.")
    if total_km_today > 0 and income_today > 0:
        income_per_km = income_today / max(total_km_today, 1)
        insights.append(f"Seu ganho bruto por km hoje está em R$ {income_per_km:.2f}.")
    if daily_goal > 0 and profit_today < daily_goal:
        insights.append(f"Faltam R$ {max(daily_goal - profit_today, 0):.2f} de lucro para bater sua meta diária.")
    if user.is_pro and maintenance_reserve > 0:
        insights.append(f"Reserve R$ {maintenance_reserve:.2f} por mês para manutenção e imprevistos.")
    if user.is_premium and suggested_tax_reserve > 0:
        insights.append(f"Separe R$ {suggested_tax_reserve:.2f} este mês para imposto conforme sua reserva configurada.")

    current_km = get_current_vehicle_km(user.id)
    maintenance_alerts = get_open_maintenance_alerts(user.id, current_km)
    for alert in maintenance_alerts[:3]:
        insights.append(alert)

    return {
        "income_today": round(income_today, 2),
        "expense_today": round(expense_today, 2),
        "profit_today": round(profit_today, 2),
        "income_week": round(income_week, 2),
        "expense_week": round(expense_week, 2),
        "profit_week": round(profit_week, 2),
        "income_month": round(income_month, 2),
        "expense_month": round(expense_month, 2),
        "profit_month": round(profit_month, 2),
        "real_month_profit_after_reserves": round(real_month_profit_after_reserves, 2),
        "daily_goal_progress": progress_pct(profit_today, daily_goal),
        "weekly_goal_progress": progress_pct(profit_week, weekly_goal),
        "monthly_goal_progress": progress_pct(profit_month, monthly_goal),
        "daily_goal": round(daily_goal, 2),
        "weekly_goal": round(weekly_goal, 2),
        "monthly_goal": round(monthly_goal, 2),
        "fuel_consumption_km_l": user.goal.fuel_consumption_km_l if user.goal else 10,
        "fixed_cost_monthly": round(fixed_cost_monthly, 2),
        "maintenance_reserve": round(maintenance_reserve, 2),
        "suggested_tax_reserve": round(suggested_tax_reserve, 2),
        "total_km_today": round(total_km_today, 2),
        "total_hours_today": round(total_hours_today, 2),
        "total_km_month": round(total_km_month, 2),
        "total_hours_month": round(total_hours_month, 2),
        "shift_is_open": bool(today_shift and today_shift.is_open),
        "shift_started_at": today_shift.start_time if today_shift else None,
        "shift_start_km": today_shift.start_km if today_shift else None,
        "shift_end_km": today_shift.end_km if today_shift else None,
        "income_per_km_today": round(income_today / max(total_km_today, 1), 2) if total_km_today > 0 else 0,
        "income_per_hour_today": round(income_today / max(total_hours_today, 1), 2) if total_hours_today > 0 else 0,
        "profit_per_km_today": round(profit_today / max(total_km_today, 1), 2) if total_km_today > 0 else 0,
        "profit_per_hour_today": round(profit_today / max(total_hours_today, 1), 2) if total_hours_today > 0 else 0,
        "by_platform": dict(by_platform),
        "by_company": dict(by_company),
        "by_category": dict(by_category),
        "maintenance_alerts": maintenance_alerts,
        "daily_points": daily_points,
        "insights": insights,
    }


def progress_pct(current: float, goal: float) -> int:
    if goal <= 0:
        return 0
    return max(0, min(int((current / goal) * 100), 100))


def sum_amount(model, user_id: int, start: date, end: date) -> float:
    amount_field = model.amount
    value = (
        db.session.query(func.sum(amount_field))
        .filter(model.user_id == user_id, model.entry_date >= start, model.entry_date <= end)
        .scalar()
    )
    return float(value or 0)


def sum_numeric(model, user_id: int, field_name: str, start: date, end: date) -> float:
    field = getattr(model, field_name)
    value = (
        db.session.query(func.sum(field))
        .filter(model.user_id == user_id, model.entry_date >= start, model.entry_date <= end)
        .scalar()
    )
    return float(value or 0)



def get_today_shift(user_id: int) -> DailyShift | None:
    return DailyShift.query.filter_by(user_id=user_id, shift_date=date.today()).order_by(DailyShift.id.desc()).first()


def sum_shift_km(user_id: int, start: date, end: date) -> float:
    shifts = DailyShift.query.filter(
        DailyShift.user_id == user_id,
        DailyShift.shift_date >= start,
        DailyShift.shift_date <= end,
        DailyShift.end_km.isnot(None),
    ).all()
    return sum(shift.km_total for shift in shifts)


def sum_shift_hours(user_id: int, start: date, end: date) -> float:
    shifts = DailyShift.query.filter(
        DailyShift.user_id == user_id,
        DailyShift.shift_date >= start,
        DailyShift.shift_date <= end,
        DailyShift.end_time.isnot(None),
    ).all()
    return sum(shift.hours_total for shift in shifts)


def seed_default_companies() -> None:
    for item in DEFAULT_COMPANIES:
        existing = Company.query.filter_by(user_id=None, name=item["name"]).first()
        if not existing:
            db.session.add(Company(user_id=None, name=item["name"], category=item["category"], logo_url=item["logo_url"], is_active=True))
    db.session.commit()


def get_available_companies(user_id: int, include_inactive: bool = False) -> list[Company]:
    query = Company.query.filter((Company.user_id.is_(None)) | (Company.user_id == user_id))
    if not include_inactive:
        query = query.filter(Company.is_active.is_(True))
    return query.order_by(Company.user_id.asc().nullsfirst(), Company.name.asc()).all()


def get_company_for_user(company_id: int | None, user_id: int) -> Company | None:
    if not company_id:
        return None
    return Company.query.filter(Company.id == company_id, ((Company.user_id.is_(None)) | (Company.user_id == user_id)), Company.is_active.is_(True)).first()


def get_current_vehicle_km(user_id: int) -> float:
    last_shift = DailyShift.query.filter(DailyShift.user_id == user_id, DailyShift.end_km.isnot(None)).order_by(DailyShift.end_time.desc()).first()
    return float(last_shift.end_km or 0) if last_shift else 0.0


def get_open_maintenance_alerts(user_id: int, current_km: float) -> list[str]:
    alerts: list[str] = []
    today = date.today()
    items = MaintenanceItem.query.filter_by(user_id=user_id, status="aberto").all()
    for item in items:
        if item.due_date and item.due_date <= today:
            alerts.append(f"Manutenção vencida: {item.title} estava prevista para {item.due_date.strftime('%d/%m/%Y')}.")
        elif item.due_date and (item.due_date - today).days <= 7:
            alerts.append(f"Manutenção próxima: {item.title} vence em {(item.due_date - today).days} dia(s).")
        if item.due_km and current_km and item.due_km <= current_km:
            alerts.append(f"Manutenção por KM vencida: {item.title} prevista para {item.due_km:.0f} km.")
        elif item.due_km and current_km and (item.due_km - current_km) <= 500:
            alerts.append(f"Manutenção próxima: faltam {max(item.due_km - current_km, 0):.0f} km para {item.title}.")
    return alerts


def ensure_schema() -> None:
    """Cria tabelas e adiciona colunas novas em bancos já existentes.

    Útil para Render/Supabase sem Alembic neste MVP.
    """
    db.create_all()
    inspector = inspect(db.engine)
    table_names = inspector.get_table_names()
    if "income_entry" in table_names:
        columns = {col["name"] for col in inspector.get_columns("income_entry")}
        if "company_id" not in columns:
            dialect = db.engine.dialect.name
            sql = "ALTER TABLE income_entry ADD COLUMN company_id INTEGER"
            db.session.execute(text(sql))
            db.session.commit()


app = create_app()

if __name__ == "__main__":
    with app.app_context():
        ensure_schema()
        seed_default_companies()
    app.run(debug=True)
