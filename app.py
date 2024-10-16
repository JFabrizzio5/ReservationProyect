from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import qrcode
import os
import secrets
from PIL import Image
from pyzbar.pyzbar import decode
import requests

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Definición de modelos
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    boletos = db.relationship('Boleto', backref='usuario', lazy=True)

class Evento(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    fecha = db.Column(db.String(100), nullable=False)
    boletos = db.relationship('Boleto', backref='evento', lazy=True)

class Boleto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    id_evento = db.Column(db.Integer, db.ForeignKey('evento.id'))
    activo = db.Column(db.Boolean, default=True)
    clave_unica = db.Column(db.String(20), unique=True, nullable=False)

# Crear la base de datos
with app.app_context():
    db.create_all()

# Función para generar el QR
def generar_qr(clave_unica):
    qr = qrcode.make(f'Clave unica: {clave_unica}')  # Asegúrate de que el texto sea claro
    qr_path = os.path.join('static/qrcodes', f'boleto_{clave_unica}.png')
    qr.save(qr_path)

# Rutas
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/eventos', methods=['GET', 'POST'])
def eventos():
    if request.method == 'POST':
        nombre = request.form['nombre']
        fecha = request.form['fecha']
        nuevo_evento = Evento(nombre=nombre, fecha=fecha)
        db.session.add(nuevo_evento)
        db.session.commit()
        return redirect(url_for('eventos'))
    
    eventos = Evento.query.all()
    return render_template('eventos.html', eventos=eventos)

@app.route('/boletos', methods=['GET', 'POST'])
def boletos():
    if request.method == 'POST':
        id_usuario = request.form['id_usuario']
        id_evento = request.form['id_evento']
        clave_unica = secrets.token_hex(10)  # Generar una clave aleatoria
        nuevo_boleto = Boleto(id_usuario=id_usuario, id_evento=id_evento, clave_unica=clave_unica)
        db.session.add(nuevo_boleto)
        db.session.commit()

        # Generar el código QR
        generar_qr(clave_unica)

        return redirect(url_for('boletos'))
    
    boletos = Boleto.query.all()
    usuarios = Usuario.query.all()
    eventos = Evento.query.all()
    return render_template('boletos.html', boletos=boletos, usuarios=usuarios, eventos=eventos)

@app.route('/desactivar_boleto/<string:clave_unica>', methods=['POST'])
def desactivar_boleto(clave_unica):
    print(f"Clave única recibida: {clave_unica}")  # Para depuración
    boleto = Boleto.query.filter_by(clave_unica=clave_unica).first()
    
    if not boleto:
        return jsonify({'message': 'Código no válido o ya utilizado. Clave proporcionada: {}'.format(clave_unica)}), 400
    
    if not boleto.activo:
        return jsonify({'message': 'Código ya usado'}), 400

    boleto.activo = False  # Desactivar el boleto
    db.session.commit()
    return jsonify({'message': 'Código correcto, boleto desactivado'})


@app.route('/subir-imagen', methods=['GET', 'POST'])
def subir_imagen():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'message': 'No file part'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400
        
        # Procesar la imagen
        try:
            imagen = Image.open(file.stream)
            decoded_objects = decode(imagen)

            if not decoded_objects:
                return jsonify({'message': 'No QR code found'}), 400
            
            # Suponiendo que solo hay un QR en la imagen
            clave_unica = decoded_objects[0].data.decode('utf-8').strip()  # Obtener solo el valor
            print(f"Clave única decodificada: {clave_unica}")  # Para depuración

            # Retornar la clave única como JSON
            return jsonify({'clave_unica': clave_unica}), 200

        except Exception as e:
            return jsonify({'message': f'Error procesando la imagen: {str(e)}'}), 500

    return render_template('subir_imagen.html')


@app.route('/usuarios', methods=['GET', 'POST'])
def usuarios():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        nuevo_usuario = Usuario(nombre=nombre, correo=correo)
        db.session.add(nuevo_usuario)
        db.session.commit()
        return redirect(url_for('usuarios'))

    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)

if __name__ == '__main__':
    if not os.path.exists('static/qrcodes'):
        os.makedirs('static/qrcodes')
    app.run(host='0.0.0.0', port=5000)
