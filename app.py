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
    video = db.Column(db.String(200)) 
    descripcion = db.Column(db.Text)
    categoria = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comentarios = db.relationship('Comentario', backref='producto', lazy=True, cascade="all, delete-orphan")

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

class Comentario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'))
    autor = db.relationship('User', backref='sus_comentarios')

with app.app_context():
    db.create_all()

# --- RUTAS ---
@app.route('/')
def inicio():
    query = request.args.get('q')
    productos = Producto.query.filter(Producto.nombre.contains(query)).all() if query else Producto.query.all()
    return render_template('index.html', productos=productos)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        correo = request.form['correo'].lower().strip()
        tipo = request.form.get('tipo_usuario')
        es_gleider = (correo == 'gleiderr99@gmail.com')
        tel_final = request.form.get('telefono') if tipo == 'vendedor' else "Cliente"
        if User.query.filter_by(correo=correo).first():
            return "Correo ya existe."
        nuevo_u = User(nombre=request.form['nombre'], correo=correo, telefono=tel_final,
                     password=generate_password_hash(request.form['pass'], method='pbkdf2:sha256'), es_admin=es_gleider)
        db.session.add(nuevo_u); db.session.commit()
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(correo=request.form['correo'].lower().strip()).first()
        if user and check_password_hash(user.password, request.form['pass']):
            session['user_id'], session['user_name'], session['es_admin'] = user.id, user.nombre, user.es_admin
            return redirect(url_for('gleider_admin'))
    return render_template('login.html')

@app.route('/gleider_admin', methods=['GET', 'POST'])
def gleider_admin():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    
    if request.method == 'POST' and user.telefono != "Cliente":
        foto = request.files.get('foto')
        video = request.files.get('video')
        f_foto, f_video = "", ""
        if foto:
            f_foto = secure_filename(foto.filename)
            foto.save(os.path.join(app.config['UPLOAD_FOLDER'], f_foto))
        if video:
            f_video = secure_filename(video.filename)
            video.save(os.path.join(app.config['UPLOAD_FOLDER'], f_video))

        nuevo = Producto(nombre=request.form.get('nombre'), precio=float(request.form.get('precio', 0)),
                        descripcion=request.form.get('descripcion'), categoria=request.form.get('categoria'),
                        imagen=f_foto, video=f_video, user_id=user.id)
        db.session.add(nuevo); db.session.commit()
        return redirect(url_for('gleider_admin'))

    mensajes = Mensaje.query.filter((Mensaje.emisor_id==user.id)|(Mensaje.receptor_id==user.id)).order_by(Mensaje.fecha.desc()).all()
    chats_vistos, mensajes_unicos = [], []
    for m in mensajes:
        otro_id = m.emisor_id if m.emisor_id != user.id else m.receptor_id
        if otro_id not in chats_vistos:
            mensajes_unicos.append(m); chats_vistos.append(otro_id)

    productos = Producto.query.filter_by(user_id=user.id).all()
    return render_template('admin.html', user=user, productos=productos, mensajes=mensajes_unicos)

@app.route('/perfil/<int:user_id>')
def perfil(user_id):
    usuario = User.query.get_or_404(user_id)
    productos = Producto.query.filter_by(user_id=user_id).all()
    return render_template('perfil.html', usuario=usuario, productos=productos)

@app.route('/comentar/<int:p_id>', methods=['POST'])
def comentar(p_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    nuevo = Comentario(contenido=request.form.get('comentario'), user_id=session['user_id'], producto_id=p_id)
    db.session.add(nuevo); db.session.commit()
    return redirect(request.referrer)

@app.route('/chat/<int:user_b>')
def chat(user_b):
    if 'user_id' not in session: return redirect(url_for('login'))
    yo = session['user_id']
    mensajes = Mensaje.query.filter(((Mensaje.emisor_id==yo)&(Mensaje.receptor_id==user_b))|((Mensaje.emisor_id==user_b)&(Mensaje.receptor_id==yo))).all()
    return render_template('chat.html', mensajes=mensajes, otro=User.query.get(user_b))

@app.route('/enviar_mensaje/<int:p_id>', methods=['POST'])
def enviar_mensaje(p_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    prod = Producto.query.get(p_id)
    emisor_id = session['user_id']
    receptor_id = request.form.get('receptor_id') if emisor_id == prod.user_id else prod.user_id
    nuevo_m = Mensaje(contenido=request.form.get('mensaje'), emisor_id=emisor_id, receptor_id=int(receptor_id), producto_id=p_id)
    db.session.add(nuevo_m); db.session.commit()
    return redirect(url_for('chat', user_b=receptor_id))

@app.route('/eliminar/<int:id>')
def eliminar_producto(id):
    p = Producto.query.get(id); db.session.delete(p); db.session.commit()
    return redirect(url_for('gleider_admin'))

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('inicio'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
