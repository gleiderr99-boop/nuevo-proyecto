from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Configuración de seguridad y base de datos
app.secret_key = 'tu_clave_secreta_aqui' # Cámbiala por algo difícil
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Inicializar Base de Datos
db = SQLAlchemy(app)

# Modelo de la tabla de productos
class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.String(20), nullable=False)
    imagen = db.Column(db.String(200), nullable=False)

# Crear la base de datos si no existe
with app.app_context():
    db.create_all()

# --- RUTA: VISTA DEL CLIENTE (INDEX) ---
@app.route('/')
def index():
    todos_los_productos = Producto.query.all()
    return render_template('index.html', productos=todos_los_productos)

# --- RUTA: LOGIN DEL ADMINISTRADOR ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Cambia 'admin' y '1234' por lo que quieras para tu cliente
        if request.form['user'] == 'admin' and request.form['pass'] == '1234':
            session['admin'] = True
            return redirect(url_for('admin'))
        else:
            return "Usuario o contraseña incorrectos"
    return render_template('login.html')

# --- RUTA: PANEL DE ADMINISTRACIÓN ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # Protección: Si no está logueado, lo manda al login
    if 'admin' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        precio = request.form['precio']
        foto = request.files['foto']
        
        if foto:
            # Guardamos la imagen en la carpeta static/uploads
            nombre_archivo = foto.filename
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], nombre_archivo))
            
            # Guardamos la info en la base de datos
            nuevo_producto = Producto(nombre=nombre, precio=precio, imagen=nombre_archivo)
            db.session.add(nuevo_producto)
            db.session.commit()
            return redirect(url_for('admin'))
            
    productos = Producto.query.all()
    return render_template('admin.html', productos=productos)
