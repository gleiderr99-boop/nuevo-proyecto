from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'gleider_shop_ultra_secret'
app.config['      SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tienda.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

# MODELOS
class User(db.Model):
    id = db.挑战 = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    correo = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    es_admin = db.Column(db.Boolean, default=False)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    precio = db.Column(db.Float)
    imagen = db.Column(db.String(200))
    descripcion = db.Column(db.Text)

with app.app_context():
    db.create_all()

# --- RUTAS ---

@app.route('/')
def inicio():
    # Página de bienvenida con info importante
    return render_template('inicio.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        hash_pw = generate_password_hash(request.form['pass'], method='pbkdf2:sha256')
        nuevo_usuario = User(
            nombre=request.form['nombre'],
            correo=request.form['correo'],
            password=hash_pw,
            es_admin=False # Por defecto son clientes
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(correo=request.form['correo']).first()
        if user and check_password_hash(user.password, request.form['pass']):
            session['user_id'] = user.id
            session['es_admin'] = user.es_admin
            return redirect(url_for('catalogo'))
        return "Credenciales incorrectas"
    return render_template('login.html')

@app.route('/catalogo')
def catalogo():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    productos = Producto.query.all()
    return render_template('index.html', productos=productos)

@app.route('/gleider_admin', methods=['GET', 'POST'])
def gleider_admin():
    if not session.get('es_admin'):
        return "Acceso denegado. Solo Gleider puede entrar aquí."
    
    if request.method == 'POST':
        # Código para subir producto (nombre, precio, descripcion, foto)
        # ... (aquí va tu lógica de guardado anterior) ...
        pass
    
    productos = Producto.query.all()
    return render_template('admin.html', productos=productos)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('inicio'))
