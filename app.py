from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'sabanalarga_market_ultra_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tienda.db'
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# Asegurar que la carpeta de fotos exista
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = SQLAlchemy(app)

# --- MODELOS DE BASE DE DATOS ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    correo = db.Column(db.String(100), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
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

class Mensaje(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    emisor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    receptor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'))
    leido = db.Column(db.Boolean, default=False)
    emisor = db.relationship('User', foreign_keys=[emisor_id])
    receptor = db.relationship('User', foreign_keys=[receptor_id])
    producto = db.relationship('Producto')

with app.app_context():
    db.create_all()

# --- RUTAS DE NAVEGACIÓN Y AUTENTICACIÓN ---

# Reemplaza la ruta de inicio y añade el modelo de mensajes leídos
@app.route('/')
def inicio():
    query = request.args.get('q') # Captura lo que la gente escribe en el buscador
    if query:
        # Busca productos que contengan esa palabra en el nombre
        productos = Producto.query.filter(Producto.nombre.contains(query)).all()
    else:
        productos = Producto.query.all()
    return render_template('index.html', productos=productos)

# Añade esto a tu clase Mensaje para las notificaciones
# class Mensaje(db.Model):
#    ... (lo que ya tenías)
#    leido = db.Column(db.Boolean, default=False)
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        correo = request.form['correo']
        tipo = request.form.get('tipo_usuario') # 'cliente' o 'vendedor'
        
        # El admin siempre es Gleider
        es_gleider = True if correo.lower() == 'gleiderr99@gmail.com' else False
        
        # Si es cliente, el teléfono será "Cliente", si es vendedor, lo que ponga en el input
        tel_final = request.form.get('telefono') if tipo == 'vendedor' else "Cliente"
        
        nuevo_u = User(
            nombre=request.form['nombre'],
            correo=correo,
            telefono=tel_final,
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
            
            # REGLA DE REDIRECCIÓN:
            # Si eres el Admin (Gleider) o eres un Vendedor (tienes teléfono), vas al Panel.
            if user.es_admin or (user.telefono and user.telefono != "Cliente"):
                return redirect(url_for('gleider_admin'))
            # Si eres solo un Cliente, vas directo a la Tienda a comprar.
            else:
                return redirect(url_for('inicio'))
                
        return "Datos incorrectos. <a href='/login'>Volver</a>"
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('inicio'))

# --- RUTAS DEL PANEL ADMINISTRATIVO ---

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

    # Lógica para mostrar mensajes recibidos
    mensajes_recibidos = Mensaje.query.filter_by(receptor_id=user.id).order_by(Mensaje.fecha.desc()).all()

    if user.es_admin:
        productos = Producto.query.all()
        usuarios = User.query.all()
    else:
        productos = Producto.query.filter_by(user_id=user.id).all()
        usuarios = []
        
    return render_template('admin.html', productos=productos, usuarios=usuarios, user=user, mensajes=mensajes_recibidos)

@app.route('/eliminar/<int:id>')
def eliminar_producto(id):
    p = Producto.query.get(id)
    if p and (session.get('es_admin') or p.user_id == session.get('user_id')):
        db.session.delete(p)
        db.session.commit()
    return redirect(url_for('gleider_admin'))

# --- RUTAS DEL SISTEMA DE CHAT ---

@app.route('/enviar_mensaje/<int:p_id>', methods=['POST'])
def enviar_mensaje(p_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    
    prod = Producto.query.get(p_id)
    contenido = request.form.get('mensaje')
    emisor_id = session['user_id']
    
    # LÓGICA INTELIGENTE DE RECEPTOR:
    # Si el que escribe NO es el dueño, el mensaje va para el dueño (Vendedor).
    if emisor_id != prod.user_id:
        receptor_id = prod.user_id
    else:
        # Si el que escribe ES el dueño, necesitamos saber a qué cliente le responde.
        # Para simplificar, lo sacamos de la URL del chat donde está parado.
        receptor_id = request.form.get('receptor_id') 

    if contenido and receptor_id:
        nuevo_m = Mensaje(
            contenido=contenido,
            emisor_id=emisor_id,
            receptor_id=int(receptor_id),
            producto_id=p_id
        )
        db.session.add(nuevo_m)
        db.session.commit()
        return redirect(url_for('chat', user_b=receptor_id))
    
    return redirect(url_for('inicio'))

@app.route('/chat/<int:user_b>')
def chat(user_b):
    if 'user_id' not in session: return redirect(url_for('login'))
    user_a = session['user_id']
    
    mensajes = Mensaje.query.filter(
        ((Mensaje.emisor_id == user_a) & (Mensaje.receptor_id == user_b)) |
        ((Mensaje.emisor_id == user_b) & (Mensaje.receptor_id == user_a))
    ).order_by(Mensaje.fecha.asc()).all()
    
    otro_usuario = User.query.get(user_b)
    return render_template('chat.html', mensajes=mensajes, otro=otro_usuario)

if __name__ == '__main__':
    app.run(debug=True)
