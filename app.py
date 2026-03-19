from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_gleider' # Cambia esto por algo difícil
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tienda.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

# --- MODELOS DE BASE DE DATOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    correo = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    es_admin = db.Column(db.Boolean, default=False)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    precio = db.Column(db.Float)
    imagen = db.Column(db.String(200))
    descripcion = db.Column(db.Text)

# Crear las tablas
with app.app_context():
    db.create_all()

# --- RUTAS ---

@app.route('/')
def inicio():
    # Página principal de bienvenida
    return render_template('inicio.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        # Encriptamos la clave por seguridad
        pw_hash = generate_password_hash(request.form['pass'], method='pbkdf2:sha256')
        nuevo_usuario = User(
            nombre=request.form['nombre'],
            correo=request.form['correo'],
            password=pw_hash,
            es_admin=False
        )
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            return "El correo ya está registrado. <a href='/registro'>Intenta otro</a>"
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        clave = request.form['pass']
        user = User.query.filter_by(correo=correo).first()
        
        if user and check_password_hash(user.password, clave):
            session['user_id'] = user.id
            session['user_name'] = user.nombre
            session['es_admin'] = user.es_admin
            
            if user.es_admin:
                return redirect(url_for('gleider_admin'))
            return redirect(url_for('catalogo'))
        
        return "Correo o clave incorrectos. <a href='/login'>Volver</a>"
    return render_template('login.html')

@app.route('/catalogo')
def catalogo():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    productos = Producto.query.all()
    return render_template('index.html', productos=productos)

@app.route('/gleider_admin', methods=['GET', 'POST'])
def gleider_admin():
    # Seguridad: Solo entra si es admin
    if not session.get('es_admin'):
        return "Acceso denegado. <a href='/'>Ir al inicio</a>"
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = request.form['precio']
        desc = request.form['descripcion']
        file = request.files['foto']
        
        if file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            nuevo_p = Producto(nombre=nombre, precio=precio, imagen=filename, descripcion=desc)
            db.session.add(nuevo_p)
            db.session.commit()
            return redirect(url_for('gleider_admin'))

    productos = Producto.query.all()
    return render_template('admin.html', productos=productos)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('inicio'))

if __name__ == '__main__':
    app.run(debug=True)
