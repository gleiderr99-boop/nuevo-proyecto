from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os

app = Flask(__name__)
app.secret_key = 'sabanalarga_pro_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tienda.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

db = SQLAlchemy(app)

# --- MODELOS ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    correo = db.Column(db.String(100), unique=True, nullable=False)
    telefono = db.Column(db.String(20)) # Para el WhatsApp
    password = db.Column(db.String(200), nullable=False)
    es_admin = db.Column(db.Boolean, default=False)
    productos = db.relationship('Producto', backref='vendedor', lazy=True)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    precio = db.Column(db.Float)
    imagen = db.Column(db.String(200))
    descripcion = db.Column(db.Text)
    categoria = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comentarios = db.relationship('Comentario', backref='producto', lazy=True, cascade="all, delete-orphan")

class Comentario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    cliente = db.Column(db.String(100), default="Cliente interesado")
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)

with app.app_context():
    db.create_all()

# --- RUTAS ---

@app.route('/')
def inicio():
    productos = Producto.query.all()
    return render_template('index.html', productos=productos)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        correo = request.form['correo']
        # Si eres tú, te hace Admin automáticamente
        es_gleider = True if correo.lower() == 'gleiderr99@gmail.com' else False
        
        nuevo_u = User(
            nombre=request.form['nombre'],
            correo=correo,
            telefono=request.form['telefono'],
            password=generate_password_hash(request.form['pass'], method='pbkdf2:sha256'),
            es_admin=es_gleider
        )
        try:
            db.session.add(nuevo_u)
            db.session.commit()
            return redirect(url_for('login'))
        except:
            return "El correo ya existe. <a href='/login'>Inicia sesión</a>"
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(correo=request.form['correo']).first()
        if user and check_password_hash(user.password, request.form['pass']):
            session['user_id'] = user.id
            session['user_name'] = user.nombre
            session['es_admin'] = user.es_admin
            return redirect(url_for('gleider_admin'))
        return "Error en datos. <a href='/login'>Reintentar</a>"
    return render_template('login.html')

@app.route('/gleider_admin', methods=['GET', 'POST'])
def gleider_admin():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST':
        file = request.files.get('foto')
        if file:
            filename = file.filename
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            nuevo = Producto(
                nombre=request.form.get('nombre'),
                precio=float(request.form.get('precio')),
                descripcion=request.form.get('descripcion'),
                categoria=request.form.get('categoria'),
                imagen=filename,
                user_id=user.id
            )
            db.session.add(nuevo)
            db.session.commit()
            return redirect(url_for('gleider_admin'))

    # Tú ves todo, los vendedores solo lo suyo
    if user.es_admin:
        productos = Producto.query.all()
        usuarios = User.query.all()
    else:
        productos = Producto.query.filter_by(user_id=user.id).all()
        usuarios = []
        
    return render_template('admin.html', productos=productos, usuarios=usuarios, user=user)

@app.route('/comentar/<int:p_id>', methods=['POST'])
def comentar(p_id):
    nuevo_c = Comentario(
        contenido=request.form.get('comentario'),
        cliente=request.form.get('nombre_cliente'),
        producto_id=p_id
    )
    db.session.add(nuevo_c)
    db.session.commit()
    return redirect(url_for('inicio'))

@app.route('/eliminar/<int:id>')
def eliminar_producto(id):
    p = Producto.query.get(id)
    if p and (session.get('es_admin') or p.user_id == session.get('user_id')):
        db.session.delete(p)
        db.session.commit()
    return redirect(url_for('gleider_admin'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('inicio'))

if __name__ == '__main__':
    app.run(debug=True)
