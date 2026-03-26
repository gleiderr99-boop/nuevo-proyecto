import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
# Versión 6 para forzar limpieza en Render
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sabanalarga_ultra_v6.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'clave_maestra_sabanalarga_2026'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    correo = db.Column(db.String(100), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    password = db.Column(db.String(200), nullable=False)
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

@app.route('/')
def inicio():
    productos = Producto.query.order_by(Producto.id.desc()).all()
    return render_template('index.html', productos=productos)

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        correo = request.form['correo'].lower().strip()
        if User.query.filter_by(correo=correo).first(): 
            return "Error: Este correo ya está en uso."
        
        # Método de hash actualizado para evitar errores de creación
        hash_pass = generate_password_hash(request.form['pass'], method='scrypt')
        nuevo_usuario = User(
            nombre=request.form['nombre'], 
            correo=correo, 
            telefono=request.form.get('telefono'),
            password=hash_pass
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = User.query.filter_by(correo=request.form['correo'].lower().strip()).first()
        if u and check_password_hash(u.password, request.form['pass']):
            session.update({'user_id': u.id, 'user_name': u.nombre})
            return redirect(url_for('inicio'))
    return render_template('login.html')

@app.route('/perfil/<int:user_id>')
def perfil(user_id):
    usuario = User.query.get_or_404(user_id)
    return render_template('perfil.html', usuario=usuario, productos=usuario.productos)

@app.route('/comentar/<int:p_id>', methods=['POST'])
def comentar(p_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    nuevo = Comentario(contenido=request.form.get('comentario'), user_id=session['user_id'], producto_id=p_id)
    db.session.add(nuevo); db.session.commit()
    return redirect(request.referrer)

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('inicio'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
