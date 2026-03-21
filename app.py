import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

# CAMBIO DE NOMBRE DE BD PARA DESBLOQUEAR RENDER
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sabanalarga_v3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'llave_maestra_99'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# MODELOS
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
    imagen = db.Column(db.String(200), nullable=True)
    video = db.Column(db.String(200), nullable=True)
    descripcion = db.Column(db.Text)
    categoria = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comentarios = db.relationship('Comentario', backref='producto_rel', lazy=True, cascade="all, delete-orphan")

class Comentario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    contenido = db.Column(db.Text, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'))
    autor = db.relationship('User', backref='comentarios_realizados')

with app.app_context():
    db.create_all()

# RUTAS
@app.route('/')
def inicio():
    try:
        q = request.args.get('q')
        productos = Producto.query.filter(Producto.nombre.contains(q)).all() if q else Producto.query.all()
        return render_template('index.html', productos=productos)
    except:
        return "Error en Inicio. Por favor, recarga la página."

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        correo = request.form['correo'].lower().strip()
        if User.query.filter_by(correo=correo).first(): return "Correo ya registrado"
        nuevo = User(nombre=request.form['nombre'], correo=correo, 
                     telefono=request.form.get('telefono', 'Cliente'),
                     password=generate_password_hash(request.form['pass'], method='pbkdf2:sha256'),
                     es_admin=(correo == 'gleiderr99@gmail.com'))
        db.session.add(nuevo); db.session.commit()
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(correo=request.form['correo'].lower().strip()).first()
        if u and check_password_hash(u.password, request.form['pass']):
            session.update({'user_id': u.id, 'user_name': u.nombre, 'es_admin': u.es_admin})
            return redirect(url_for('gleider_admin'))
    return render_template('login.html')

@app.route('/gleider_admin', methods=['GET', 'POST'])
def gleider_admin():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        f, v = request.files.get('foto'), request.files.get('video')
        fn_f = secure_filename(f.filename) if f and f.filename != '' else None
        fn_v = secure_filename(v.filename) if v and v.filename != '' else None
        if fn_f: f.save(os.path.join(app.config['UPLOAD_FOLDER'], fn_f))
        if fn_v: v.save(os.path.join(app.config['UPLOAD_FOLDER'], fn_v))
        nuevo = Producto(nombre=request.form.get('nombre'), precio=float(request.form.get('precio', 0)),
                         descripcion=request.form.get('descripcion'), categoria=request.form.get('categoria'),
                         imagen=fn_f, video=fn_v, user_id=user.id)
        db.session.add(nuevo); db.session.commit()
        return redirect(url_for('gleider_admin'))
    productos = Producto.query.filter_by(user_id=user.id).all()
    return render_template('admin.html', user=user, productos=productos)

@app.route('/perfil/<int:user_id>')
def perfil(user_id):
    try:
        usuario = User.query.get_or_404(user_id)
        productos = Producto.query.filter_by(user_id=user_id).all()
        return render_template('perfil.html', usuario=usuario, productos=productos)
    except Exception as e:
        return f"Error en Perfil: {str(e)}"

@app.route('/comentar/<int:p_id>', methods=['POST'])
def comentar(p_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    nuevo = Comentario(contenido=request.form.get('comentario'), 
                       user_id=session['user_id'], producto_id=p_id)
    db.session.add(nuevo); db.session.commit()
    return redirect(request.referrer)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('inicio'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
