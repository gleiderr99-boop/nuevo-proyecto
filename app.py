from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'clave_secreta_gleider' 
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
    categoria = db.Column(db.String(50), default='General')

with app.app_context():
    db.create_all()

# --- RUTAS ---

@app.route('/')
def inicio():
    return render_template('inicio.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        correo_ingresado = request.form['correo']
        pw_hash = generate_password_hash(request.form['pass'], method='pbkdf2:sha256')
        
        soy_el_jefe = False
        if correo_ingresado.lower() == 'gleiderr99@gmail.com': 
            soy_el_jefe = True
        
        nuevo_usuario = User(
            nombre=request.form['nombre'],
            correo=correo_ingresado,
            password=pw_hash,
            es_admin=soy_el_jefe 
        )
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            return "Error: Este correo ya existe. <a href='/login'>Inicia sesión</a>"
            
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
    productos = Producto.query.all()
    return render_template('index.html', productos=productos)

@app.route('/gleider_admin', methods=['GET', 'POST'])
def gleider_admin():
    if not session.get('es_admin'):
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # 1. Recogemos los datos primero
        nombre = request.form.get('nombre')
        precio = request.form.get('precio')
        desc = request.form.get('descripcion')
        categoria = request.form.get('categoria')
        file = request.files.get('foto')
        
        # 2. Verificamos y guardamos
        if nombre and precio and file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            nuevo_p = Producto(
                nombre=nombre, 
                precio=float(precio), 
                imagen=filename, 
                descripcion=desc, 
                categoria=categoria
            )
            db.session.add(nuevo_p)
            db.session.commit()
            return redirect(url_for('gleider_admin'))

    productos = Producto.query.all()
    usuarios = User.query.all() 
    return render_template('admin.html', productos=productos, usuarios=usuarios)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('inicio'))
    
@app.route('/eliminar_producto/<int:id>')
def eliminar_producto(id):
    if not session.get('es_admin'):
        return redirect(url_for('login'))
    
    producto = Producto.query.get(id)
    if producto:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], producto.imagen))
        except:
            pass 
            
        db.session.delete(producto)
        db.session.commit()
    
    return redirect(url_for('gleider_admin'))

if __name__ == '__main__':
    app.run(debug=True)
