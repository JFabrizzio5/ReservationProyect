from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import qrcode
import os
import secrets
from PIL import Image
from pyzbar.pyzbar import decode
import pandas as pd  # Asegúrate de tener pandas instalado
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import zipfile
from flask import send_file
import pandas as pd
from sqlalchemy.exc import IntegrityError
import cv2
from flask import jsonify, request, send_file
import zipfile
import os

def preprocess_and_read_qr(image_path):
    # Cargar y procesar la imagen
    img = cv2.imread(image_path)

    # Convertir a escala de grises
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Ajustar brillo y contraste
    enhanced = cv2.convertScaleAbs(gray, alpha=1.5, beta=0)

    # Filtrar ruido
    filtered = cv2.GaussianBlur(enhanced, (5, 5), 0)

    # Detección de bordes
    edges = cv2.Canny(filtered, 100, 200)

    # Leer el código QR
    decoded_objects = decode(edges)
    for obj in decoded_objects:
        print("Detected QR Code:", obj.data.decode('utf-8'))
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


class BoletoDesactivado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    id_boleto = db.Column(db.Integer, db.ForeignKey('boleto.id'))
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
    usuario = db.relationship('Usuario')
    boleto = db.relationship('Boleto')

# Crear la base de datos
with app.app_context():
    db.create_all()

# Función para generar el QR
def generar_qr(clave_unica):
    with app.app_context():  # Necesario si estás generando fuera de una solicitud activa
        url_desactivacion = f'{request.host_url}desactivar_boleto/{clave_unica}'
        qr_content = f'Clave unica: {clave_unica}\nDesactivar: {url_desactivacion}'
        qr = qrcode.make(qr_content)
        qr_path = os.path.join('static/qrcodes', f'boleto_{clave_unica}.png')
        qr.save(qr_path)

# Rutas
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/buscar_usuarios', methods=['GET'])
def buscar_usuarios():
    query = request.args.get('query', '')
    usuarios = Usuario.query.filter(
        (Usuario.nombre.ilike(f'%{query}%')) | (Usuario.correo.ilike(f'%{query}%'))
    ).all()

    # Formato para devolver los resultados en JSON
    resultados = [{'nombre': usuario.nombre, 'correo': usuario.correo} for usuario in usuarios]

    return jsonify(resultados)

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

@app.route('/desactivar_boleto/<string:clave_unica>', methods=['POST','GET'])
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
            # Verifica que la imagen sea abierta correctamente
            imagen = Image.open(file.stream)
            imagen = imagen.convert('RGB')  # Asegúrate de que esté en RGB

            # Decodificación del QR
            decoded_objects = decode(imagen)

            if not decoded_objects:
                return jsonify({'message': 'No QR code found'}), 400
            
            qr_content = decoded_objects[0].data.decode('utf-8').strip()
            print(f"Contenido QR decodificado: {qr_content}")

            # Extraer la clave única desde el contenido del QR
            if '\n' in qr_content:
                clave_unica = qr_content.split('\n')[0].replace('Clave unica: ', '')
            else:
                clave_unica = qr_content

            print(f"Clave única decodificada: {clave_unica}")  

            return jsonify({'clave_unica': clave_unica}), 200

        except Exception as e:
            print(f"Error: {e}")  # Log del error para facilitar el diagnóstico
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
def generar_pdf(nombre_usuario, boletos_usuario, pdf_path):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib import utils
    import os

    # Verificar si el usuario tiene boletos
    if not boletos_usuario:
        print(f"El usuario {nombre_usuario} no tiene boletos.")
        return False  # Devuelve False si no hay boletos

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    for boleto in boletos_usuario:
        # Obtener el camino del QR
        qr_path = os.path.join('static/qrcodes', f'boleto_{boleto.clave_unica}.png')

        # Agregar el correo del propietario
        c.setFont("Helvetica", 12)
        c.drawString(100, height - 50, f"Correo del propietario: {boleto.usuario.correo}")

        # Agregar el QR en el centro
        if os.path.exists(qr_path):
            qr_image = utils.ImageReader(qr_path)
            qr_width, qr_height = qr_image.getSize()
            c.drawImage(qr_image, (width - qr_width) / 2, (height - qr_height) / 2 - 20)

        # Agregar ID del boleto y clave única en la parte inferior
        c.setFont("Helvetica", 12)
        y_position = 30
        c.drawString(100, y_position, f"ID del Boleto: {boleto.id}  |  Clave Única: {boleto.clave_unica}")

        # Agregar el nombre del evento en la parte inferior
        c.drawString(100, y_position - 15, f"Evento: {boleto.evento.nombre}")

        # Finalizar la página
        c.showPage()

    c.save()
    return True  # Devuelve True si el PDF se generó correctamente
@app.route('/importar_excel', methods=['GET', 'POST'])
def importar_excel():
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({'message': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400

        try:
            # Leer el archivo Excel
            df = pd.read_excel(file, header=0)

            usuarios_creados = 0
            boletos_creados = 0
            zip_buffer = BytesIO()
            zip_file = None  # Inicializa zip_file aquí

            for index, row in df.iterrows():
                nombre = row.get('nombre', None)
                correo = row.get('correo', None)
                num_boletos = row.get('numero de boletos', None)
                evento_nombre = row.get('evento', None)

                # Validar datos
                if pd.isna(nombre) or pd.isna(correo):
                    print(f"Error: Falta información en la fila {index + 1}. Se omite esta fila.")
                    continue

                # Lógica para solo nombre y correo
                if (pd.isna(num_boletos) or num_boletos == '') and (evento_nombre is None or pd.isna(evento_nombre)):
                    usuario_existente = Usuario.query.filter_by(correo=correo).first()
                    if not usuario_existente:
                        nuevo_usuario = Usuario(nombre=nombre, correo=correo)
                        db.session.add(nuevo_usuario)
                        db.session.commit()
                        usuarios_creados += 1
                    continue  # No procesar boletos si solo se está agregando usuario

                # Validar número de boletos
                try:
                    num_boletos = int(num_boletos) if not pd.isna(num_boletos) else 0
                    if num_boletos <= 0:
                        print(f"Error: El número de boletos en la fila {index + 1} no es válido. Se omite esta fila.")
                        continue
                except (ValueError, TypeError):
                    print(f"Error: El número de boletos en la fila {index + 1} no es un número válido. Se omite esta fila.")
                    continue

                usuario = Usuario.query.filter_by(correo=correo).first()
                if not usuario:
                    usuario = Usuario(nombre=nombre, correo=correo)
                    db.session.add(usuario)
                    db.session.commit()
                    usuarios_creados += 1

                evento_nombre_normalizado = evento_nombre.strip().lower() if isinstance(evento_nombre, str) else None
                evento_existente = Evento.query.filter(Evento.nombre.ilike(evento_nombre_normalizado)).first() if evento_nombre_normalizado else None

                if not evento_existente:
                    if pd.isna(evento_nombre) or evento_nombre.strip() == '':
                        evento_existente = Evento.query.filter(Evento.nombre.ilike('evento batiz')).first()
                        if not evento_existente:
                            evento_existente = Evento(nombre='Evento Batiz', fecha='2024-01-01')
                            db.session.add(evento_existente)
                            db.session.commit()
                    else:
                        evento = Evento(nombre=evento_nombre, fecha='2024-01-01')
                        db.session.add(evento)
                        db.session.commit()
                        evento_existente = evento

                # Inicializar zip_file solo si hay boletos a procesar
                if num_boletos > 0:
                    if zip_file is None:
                        zip_file = zipfile.ZipFile(zip_buffer, 'w')  # Solo inicializa el ZIP si se van a agregar boletos

                    # Crear boletos
                    for _ in range(num_boletos):
                        clave_unica = secrets.token_hex(10)
                        nuevo_boleto = Boleto(id_usuario=usuario.id, id_evento=evento_existente.id, clave_unica=clave_unica)
                        db.session.add(nuevo_boleto)
                        boletos_creados += 1
                        generar_qr(clave_unica)

                    # Generar PDF para el usuario solo si hay boletos
                    boletos_usuario = Boleto.query.filter_by(id_usuario=usuario.id).all()
                    if boletos_usuario:
                        pdf_path = f"static/pdfs/{nombre.replace(' ', '_')}_boletos.pdf"
                        generar_pdf(nombre, boletos_usuario, pdf_path)
                        pdf_filename = f"{usuario.nombre.replace(' ', '_')}_boletos.pdf"
                        zip_file.write(pdf_path, arcname=os.path.join(correo, pdf_filename))

            db.session.commit()

            # Cerrar el ZIP solo si se han creado boletos
            if zip_file:
                zip_file.close()
                zip_buffer.seek(0)
                return send_file(zip_buffer, as_attachment=True, download_name='boletos_importacion.zip', mimetype='application/zip')

            # Si no se crea el ZIP, retornar la cantidad de usuarios creados
            return jsonify({
                'message': 'Usuarios agregados',
                'usuarios_creados': usuarios_creados
            }), 200

        except Exception as e:
            return jsonify({'message': f'Error interno: {str(e)}'}), 500

    return render_template('excel.html')

@app.route('/DatosFormularios', methods=['GET'])
def datos_formularios():
    formularios = Formulario.query.all()
    return render_template('datos_formularios.html', formularios=formularios)

@app.route('/generar_pdf/<int:usuario_id>', methods=['GET'])
def generar_pdf_usuario(usuario_id):
    usuario = Usuario.query.get_or_404(usuario_id)
    boletos_usuario = Boleto.query.filter_by(id_usuario=usuario_id).all()

    if not boletos_usuario:
        return jsonify({'message': 'El usuario no tiene boletos'}), 400

    pdf_path = f"static/pdfs/{usuario.nombre.replace(' ', '_')}_boletos.pdf"
    generar_pdf(usuario.nombre, boletos_usuario, pdf_path)

    return jsonify({'pdf_url': '/' + pdf_path})

def generar_zip_con_pdfs(usuario):
    from zipfile import ZipFile
    import os

    zip_path = f"static/zips/{usuario.correo}_boletos.zip"

    # Generar el ZIP
    with ZipFile(zip_path, 'w') as zip_file:
        nombre = usuario.nombre
        correo = usuario.correo
        boletos_usuario = Boleto.query.filter_by(id_usuario=usuario.id).all()

        # Generar PDF para el usuario solo si tiene boletos
        if boletos_usuario:
            pdf_path = f"static/pdfs/{nombre.replace(' ', '_')}_boletos.pdf"
            pdf_generado = generar_pdf(nombre, boletos_usuario, pdf_path)

            if pdf_generado:
                pdf_filename = f"{usuario.nombre.replace(' ', '_')}_boletos.pdf"
                zip_file.write(pdf_path, arcname=os.path.join(correo, pdf_filename))
            else:
                print(f"No se generó el PDF para {nombre} porque no tiene boletos.")
        else:
            print(f"El usuario {nombre} no tiene boletos para generar.")

@app.route('/generar_pdfs', methods=['POST'])
def generar_pdfs():
    data = request.json
    usuario_ids = data.get('usuarios', [])
    
    if not usuario_ids:
        return jsonify({"message": "No se seleccionaron usuarios."}), 400

    pdf_files = []
    for usuario_id in usuario_ids:
        # Generar el PDF para cada usuario (simulado aquí)
        pdf_filename = f"usuario_{usuario_id}.pdf"
        pdf_path = f"/ruta/a/pdfs/{pdf_filename}"
        # Agregarlo a la lista de archivos a comprimir
        pdf_files.append(pdf_path)

    # Crear un archivo ZIP
    zip_filename = "/ruta/a/pdfs/usuarios_seleccionados.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for pdf_file in pdf_files:
            zipf.write(pdf_file, os.path.basename(pdf_file))

    # Retornar la URL para descargar el archivo ZIP
    return jsonify({"zip_url": zip_filename})
    # Ejemplo en Python Flask
@app.route('/eliminar_usuario/<int:usuario_id>', methods=['DELETE'])
def eliminar_usuario(usuario_id):
    # Buscar el usuario
    usuario = Usuario.query.get_or_404(usuario_id)
    
    # Obtener todos los boletos activos del usuario
    boletos_activos = Boleto.query.filter_by(id_usuario=usuario_id, activo=True).all()
    
    # Eliminar los boletos activos
    for boleto in boletos_activos:
        db.session.delete(boleto)
    
    # Eliminar el usuario
    db.session.delete(usuario)
    db.session.commit()

    return jsonify({'message': 'Usuario y boletos eliminados correctamente'})


def eliminar_boletos(usuario_id):
    # Lógica para eliminar los boletos del usuario
    boletos.query.filter_by(usuario_id=usuario_id).delete()
    db.session.commit()

@app.route('/asistencia', methods=['GET'])
def asistencia():
    eventos = Evento.query.all()  # Obtener todos los eventos para mostrarlos en el select
    return render_template('Asistencia.html', eventos=eventos)
# Asegúrate de tener este modelo en tu archivo
@app.route('/actualizar_estado_boleto/<int:boleto_id>', methods=['POST'])
def actualizar_estado_boleto(boleto_id):
    boleto = Boleto.query.get(boleto_id)
    if not boleto:
        return jsonify({'message': 'Boleto no encontrado'}), 404
    
    # Lógica para cambiar el estado del boleto (por ejemplo, toggle activo/inactivo)
    boleto.activo = not boleto.activo  # Cambiar el estado
    db.session.commit()

    return jsonify({'message': 'Estado actualizado', 'nuevo_estado': boleto.activo})

@app.route('/eliminar_boleto/<int:boleto_id>', methods=['DELETE'])
def eliminar_boleto(boleto_id):
    boleto = Boleto.query.get(boleto_id)
    
    if not boleto:
        return jsonify({'message': 'Boleto no encontrado'}), 404

    db.session.delete(boleto)
    db.session.commit()
    return jsonify({'message': 'Boleto eliminado correctamente'}), 200
# Actualiza la tabla con los boletos desactivados
@app.route('/asistencia/boletos/<int:evento_id>', methods=['GET'])
def get_boletos_desactivados(evento_id):
    boletos = Boleto.query.filter_by(id_evento=evento_id, activo=False).all()
    resultado = [{'nombre': b.usuario.nombre, 'correo': b.usuario.correo} for b in boletos]
    return jsonify(resultado)

if __name__ == '__main__':
    if not os.path.exists('static/qrcodes'):
        os.makedirs('static/qrcodes')
    app.run(host='0.0.0.0', port=5000)
    