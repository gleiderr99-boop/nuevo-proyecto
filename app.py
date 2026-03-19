from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Configuración
app.secret_key = 'mi_llave_secreta_pro' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

# Modelo de la Base de Datos
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.String(20), nullable=False)
    imagen = db.Column(db.String(200), nullable=False)

# Crear base de datos
with app.app_context():
    db.create_all()

# --- 1. RUTA DE INICIO: AHORA ES EL LOGIN ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Usuario: admin | Clave: 1234
        if request.form['user'] == 'Gleider' and request.form['pass'] == 'gleider1':
            session['gleider'] = True
            return redirect(url_for('gleider'))
        else:
            return "Error: Usuario o contraseña incorrectos. <a href='/'>Volver</a>"
    return render_template('login.html')

# --- 2. RUTA DEL CATÁLOGO (LO QUE VEN LOS CLIENTES) ---
@app.route('/catalogo')
def index():
    productos = Producto.query.all()
    return render_template('index.html', productos=productos)

# --- 3. PANEL DE ADMINISTRACIÓN ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = request.form['precio']
        foto = request.files['foto']
        
        if foto:
            nombre_archivo = foto.filename
            # Guardamos la foto en static/uploads
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo))
            
            nuevo_p = Producto(nombre=nombre, precio=precio, imagen=nombre_archivo)
            db.session.add(nuevo_p)
            db.session.commit()
            return redirect(url_for('gleider'))
            
    productos = Producto.query.all()
    return render_template('gleider.html', productos=productos)

# --- 4. CERRAR SESIÓN ---
@app.route('/logout')
def logout():
    session.pop('gleider', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
