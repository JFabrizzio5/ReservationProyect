from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import qrcode
import os
import secrets
from PIL import Image
from pyzbar.pyzbar import decode
import pandas as pd  # Asegúrate de tener pandas instalado
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

class Formulario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    telefono_particular = db.Column(db.String(20), nullable=False)
    telefono_celular = db.Column(db.String(20), nullable=False)
    correo = db.Column(db.String(100), nullable=False)
    generacion = db.Column(db.String(20), nullable=False)
    boleta = db.Column(db.String(20), nullable=False)
    carrera = db.Column(db.String(100), nullable=False)
    egresado_ipn = db.Column(db.String(20), nullable=False)
    actualmente_labora = db.Column(db.String(20), nullable=False)
    comprobante_pago = db.Column(db.String(255), nullable=False)  # Link del PDF
    id_evento = db.Column(db.Integer, db.ForeignKey('evento.id'))


# Crear la base de datos
with app.app_context():
    db.create_all()

# Función para generar el QR
def generar_qr(clave_unica):
    qr = qrcode.make(f'Clave unica: {clave_unica}')  
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
        clave_unica = secrets.token_hex(10)  
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
    print(f"Clave única recibida: {clave_unica}")  
    boleto = Boleto.query.filter_by(clave_unica=clave_unica).first()
    
    if not boleto:
        return jsonify({'message': 'Código no válido o ya utilizado. Clave proporcionada: {}'.format(clave_unica)}), 400
    
    if not boleto.activo:
        return jsonify({'message': 'Código ya usado'}), 400

    boleto.activo = False  
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
            
            clave_unica = decoded_objects[0].data.decode('utf-8').strip()  
            print(f"Clave única decodificada: {clave_unica}")  

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

@app.route('/formulario/<int:evento_id>', methods=['GET', 'POST'])
def formulario(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    
    if request.method == 'POST':
        # Verificar si el correo ya está registrado
        correo = request.form['correo']
        if Formulario.query.filter_by(correo=correo).first():
            return jsonify({'message': 'El correo ya está registrado'}), 400

        nuevo_formulario = Formulario(
            nombre=request.form['nombre'],
            telefono_particular=request.form['telefono_particular'],
            telefono_celular=request.form['telefono_celular'],
            correo=correo,
            generacion=request.form['generacion'],
            boleta=request.form['boleta'],
            carrera=request.form['carrera'],
            egresado_ipn=request.form['egresado_ipn'],
            actualmente_labora=request.form['actualmente_labora'],
            comprobante_pago=request.form['comprobante_pago'],
            id_evento=evento_id
        )
        db.session.add(nuevo_formulario)
        db.session.commit()
        return redirect(url_for('formulario', evento_id=evento_id))

    return render_template('formulario.html', evento=evento)

@app.route('/importar_excel', methods=['GET', 'POST'])
def importar_excel():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'message': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400

        # Leer el archivo Excel
        df = pd.read_excel(file, header=0)

        # Imprimir el DataFrame en la consola del servidor
        print(df)  # Ver el contenido del Excel

        # Validar que tenga las columnas necesarias
        if not {'nombre', 'correo'}.issubset(df.columns):
            return jsonify({'message': 'El archivo debe contener las columnas "nombre" y "correo"'}), 400

        evento = Evento.query.filter_by(nombre='Importaciones Excel').first()
        if not evento:
            evento = Evento(nombre='Importaciones Excel', fecha='2024-01-01')
            db.session.add(evento)
            db.session.commit()

        columna_nombre = 'nombre'
        columna_correo = 'correo'
        columna_boletos = 'numero de boletos' if 'numero de boletos' in df.columns else None

        usuarios_creados = 0
        boletos_creados = 0

        for index, row in df.iterrows():
            nombre = row[columna_nombre]
            correo = row[columna_correo]

            # Imprimir para depurar
            print(f"Procesando fila {index}: {nombre}, {correo}")

            # Verificar si el usuario ya existe
            usuario = Usuario.query.filter_by(correo=correo).first()
            if not usuario:
                # Crear usuario si no existe
                usuario = Usuario(nombre=nombre, correo=correo)
                db.session.add(usuario)
                db.session.commit()
                usuarios_creados += 1
                print(f"Usuario creado: {nombre} - {correo}")
            else:
                print(f"Usuario ya existente: {correo}")

            # Crear boletos solo si la columna 'numero de boletos' existe y no está vacía
            if columna_boletos and not pd.isna(row[columna_boletos]):
                num_boletos = int(row[columna_boletos])
                for _ in range(num_boletos):
                    clave_unica = secrets.token_hex(10)
                    nuevo_boleto = Boleto(id_usuario=usuario.id, id_evento=evento.id, clave_unica=clave_unica)
                    db.session.add(nuevo_boleto)
                    boletos_creados += 1
                print(f"Boletos creados para {correo}: {num_boletos} boletos")

        db.session.commit()

        # Generar el mensaje para sweetalert
        if usuarios_creados > 0 and boletos_creados > 0:
            mensaje = 'Usuarios y boletos creados con éxito.'
        elif usuarios_creados > 0:
            mensaje = 'Solo se crearon usuarios.'
        elif boletos_creados > 0:
            mensaje = 'Solo se crearon boletos para usuarios existentes.'
        else:
            mensaje = 'No se crearon ni usuarios ni boletos.'

        # Devolver el mensaje en formato JSON para SweetAlert
        return jsonify({'message': mensaje}), 200

    return render_template('excel.html')

@app.route('/DatosFormularios', methods=['GET'])
def datos_formularios():
    formularios = Formulario.query.all()
    return render_template('datos_formularios.html', formularios=formularios)

if __name__ == '__main__':
    if not os.path.exists('static/qrcodes'):
        os.makedirs('static/qrcodes')
    app.run(host='0.0.0.0', port=5000)
