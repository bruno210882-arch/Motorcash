from flask import Flask, render_template, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev'
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL","sqlite:///motorcash.db")
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    plano = db.Column(db.String(20), default="free")
    ativo = db.Column(db.Boolean, default=False)

@app.route("/")
def index():
    return redirect(url_for("landing"))

@app.route("/landing")
def landing():
    return render_template("landing.html")

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", lucro=210, km=1.85, hora=32)

@app.route("/planos")
def planos():
    return render_template("planos.html")

@app.route("/criar_pagamento/<plano>")
def criar_pagamento(plano):
    return f"Simulação pagamento plano {plano}"

@app.route("/admin/seed")
def seed():
    db.create_all()
    return "Banco criado"

if __name__ == "__main__":
    app.run(debug=True)

@app.route("/login", methods=["GET","POST"])
def login():
    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    return render_template("register.html")
