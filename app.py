import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'sabanalarga_market_ultra_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///tienda.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

# Asegurar que la carpeta de fotos exista
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# --- MODELOS ---

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

with app.app_context():
    db.create_all()

# --- RUTAS ---

@app.route('/')
def inicio():
    query = request.args.get('q')
    if query:
        productos = Producto.query.filter(Producto.nombre.contains(query)).all()
    else:
        productos = Producto.query.all()
    return render_template('index.html', productos=productos)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        correo = request.form['correo'].lower().strip()
        tipo = request.form.get('tipo_usuario')
        es_gleider = True if correo == 'gleiderr99@gmail.com' else False
        tel_final = request.form.get('telefono') if tipo == 'vendedor' else "Cliente"
        if User.query.filter_by(correo=correo).first():
            return "El correo ya existe. <a href='/login'>Inicia sesión</a>"
        nuevo_u = User(
            nombre=request.form['nombre'], correo=correo, telefono=tel_final,
            password=generate_password_hash(request.form['pass'], method='pbkdf2:sha256'),
            es_admin=es_gleider
        )
        db.session.add(nuevo_u)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(correo=request.form['correo'].lower().strip()).first()
        if user and check_password_hash(user.password, request.form['pass']):
            session['user_id'] = user.id
            session['user_name'] = user.nombre
            session['es_admin'] = user.es_admin
            return redirect(url_for('gleider_admin'))
        return "Correo o contraseña incorrectos."
    return render_template('login.html')

@app.route('/gleider_admin', methods=['GET', 'POST'])
def gleider_admin():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    
    # Lógica para subir productos (Solo vendedores)
    if request.method == 'POST' and user.telefono != "Cliente":
        file = request.files.get('foto')
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], filename))
            try:
                precio_val = float(request.form.get('precio', 0))
            except ValueError:
                precio_val = 0.0
            nuevo = Producto(
                nombre=request.form.get('nombre'), precio=precio_val,
                descripcion=request.form.get('descripcion'), categoria=request.form.get('categoria'),
                imagen=filename, user_id=user.id
            )
            db.session.add(nuevo)
            db.session.commit()
            return redirect(url_for('gleider_admin'))

    # Lógica de mensajes (Clientes ven con quién chatean, Vendedores ven lo recibido)
    if user.telefono == "Cliente":
        mensajes = Mensaje.query.filter((Mensaje.emisor_id == user.id) | (Mensaje.receptor_id == user.id)).order_by(Mensaje.fecha.desc()).all()
    else:
        mensajes = Mensaje.query.filter_by(receptor_id=user.id).order_by(Mensaje.fecha.desc()).all()

    chats_vistos = []
    mensajes_unicos = []
    for m in mensajes:
        otro_id = m.emisor_id if m.emisor_id != user.id else m.receptor_id
        if otro_id not in chats_vistos:
            mensajes_unicos.append(m)
            chats_vistos.append(otro_id)

    productos = Producto.query.filter_by(user_id=user.id).all()
    usuarios = User.query.all() if user.es_admin else []
    return render_template('admin.html', user=user, productos=productos, mensajes=mensajes_unicos, usuarios=usuarios)

@app.route('/perfil/<int:user_id>')
def perfil(user_id):
    # Buscamos al usuario o soltamos error 404 si no existe
    usuario = User.query.get_or_404(user_id)
    # Filtramos TODOS los productos que pertenecen a este ID de usuario
    productos_vendedor = Producto.query.filter_by(user_id=user_id).all()
    
    return render_template('perfil.html', usuario=usuario, productos=productos_vendedor)

@app.route('/chat/<int:user_b>')
def chat(user_b):
    if 'user_id' not in session: return redirect(url_for('login'))
    yo = session['user_id']
    Mensaje.query.filter_by(receptor_id=yo, emisor_id=user_b, leido=False).update({Mensaje.leido: True})
    db.session.commit()
    mensajes = Mensaje.query.filter(
        ((Mensaje.emisor_id == yo) & (Mensaje.receptor_id == user_b)) |
        ((Mensaje.emisor_id == user_b) & (Mensaje.receptor_id == yo))
    ).order_by(Mensaje.fecha.asc()).all()
    return render_template('chat.html', mensajes=mensajes, otro=User.query.get(user_b))

@app.route('/enviar_mensaje/<int:p_id>', methods=['POST'])
def enviar_mensaje(p_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    prod = Producto.query.get(p_id)
    emisor_id = session['user_id']
    receptor_id = request.form.get('receptor_id') if emisor_id == prod.user_id else prod.user_id
    if receptor_id:
        nuevo_m = Mensaje(contenido=request.form.get('mensaje'), emisor_id=emisor_id, receptor_id=int(receptor_id), producto_id=p_id)
        db.session.add(nuevo_m); db.session.commit()
        return redirect(url_for('chat', user_b=receptor_id))
    return redirect(url_for('inicio'))

@app.route('/eliminar/<int:id>')
def eliminar_producto(id):
    p = Producto.query.get(id)
    if p and (session.get('es_admin') or p.user_id == session.get('user_id')):
        db.session.delete(p); db.session.commit()
    return redirect(url_for('gleider_admin'))

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('inicio'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
